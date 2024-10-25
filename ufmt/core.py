# Copyright 2022 Amethyst Reese, Tim Hatch
# Licensed under the MIT license

import logging
import re
import sys
from dataclasses import replace
from functools import partial
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator, Match, Optional, Sequence
from warnings import warn

import black
import black.mode
import black.report
from moreorless import unified_diff
from trailrunner import Trailrunner
from usort import usort
from usort.config import CAT_FIRST_PARTY, CAT_STANDARD_LIBRARY

try:
    import ruff_api
except ImportError:  # pragma: nocover
    pass

from .config import load_config
from .types import (
    BlackConfig,
    BlackConfigFactory,
    Encoding,
    FileContent,
    Formatter,
    Processor,
    Result,
    SkipFormatting,
    Sorter,
    STDIN,
    UfmtConfig,
    UfmtConfigFactory,
    UsortConfig,
    UsortConfigFactory,
)
from .util import make_black_config, normalize_result, read_file, write_file

LOG = logging.getLogger(__name__)


def ufmt_bytes(
    path: Path,
    content: FileContent,
    *,
    encoding: Encoding = "utf-8",
    black_config: BlackConfig,
    usort_config: UsortConfig,
    ufmt_config: UfmtConfig = UfmtConfig(),
    pre_processor: Optional[Processor] = None,
    post_processor: Optional[Processor] = None,
) -> FileContent:
    """
    Format arbitrary bytes for the given path.

    Requires passing valid config objects for both black and µsort. If the given path
    represents a type stub (has a ``.pyi`` suffix), the black config object will be
    updated to set ``is_pyi = True``.

    This function will not catch any errors during formatting, except for "everything is
    fine" messages, like :exc:`black.NothingChanged`. All other errors must be handled
    by the code calling this function; see :func:`ufmt_file` for example error handling.

    Optionally takes a pre- or post-processor matching the :class:`Processor` protocol.
    If given, the pre-processor will be called with the original byte string content
    before it has been run through µsort or black. The return value of the pre-processor
    will be used in place of the original content when formatting.
    If given, the post processor will be called with the updated byte string content
    after it has been run through µsort and black. The return value of the post
    processor will replace the final return value of :func:`ufmt_bytes`.

    **Experimental:**
    The optional ``ufmt_config`` parameter allows passing alternative
    :class:`~ufmt.types.Formatter` and :class:`~ufmt.types.Sorter`
    values, to choose formatting and sorting implementations instead of black and µsort.
    This should be passed by alternate frontends, and be based on the project's
    configuration in ``pyproject.toml``. Optionally can be passed through from
    :func:`ufmt_file` or :func:`ufmt_paths` as ``ufmt_config_factory``.

    .. note::
        Content will be decoded before passing to black, and re-encoded to bytes
        again. Be sure to pass a known-valid unicode encoding for the content.

        Specifying the correct encoding is important! µfmt cannot do the right thing
        without the correct encoding if files contain PEP 263 coding lines, or byte
        values unrepresentable in UTF-8 (like ``\\ud800``).

        **When in doubt, use :func:`ufmt_file` or :func:`ufmt_paths`.**

        :func:`ufmt.util.read_file` can be used to both read bytes from disk, and make a
        best guess at file encodings. Otherwise, use :func:`tokenize.detect_encodings`.

    """
    if pre_processor is not None:
        content = pre_processor(path, content, encoding=encoding)

    # run configured sorter
    if ufmt_config.sorter == Sorter.usort:
        result = usort(content, usort_config, path)
        if result.error:
            raise result.error
        content = result.output
    elif ufmt_config.sorter == Sorter.ruff_api:
        ruff_isort_options = ruff_api.SortOptions(
            # match µsort configuration
            first_party_modules=[
                imp
                for imp, category in usort_config.known.items()
                if category == CAT_FIRST_PARTY
            ],
            standard_library_modules=[
                imp
                for imp, category in usort_config.known.items()
                if category == CAT_STANDARD_LIBRARY
            ],
            detect_same_package=usort_config.first_party_detection,
            # match µsort behavior for now
            case_sensitive=False,
            combine_as_imports=True,
            order_by_type=False,
        )
        content_str = ruff_api.isort_string(
            path.as_posix(),
            content.decode(encoding),
            options=ruff_isort_options,
            root=(
                ufmt_config.project_root.as_posix()
                if ufmt_config.project_root
                else None
            ),
        )
        content = content_str.encode(encoding)
    elif ufmt_config.sorter == Sorter.skip:
        pass
    else:
        raise ValueError(f"{ufmt_config.sorter!r} is not a supported sorter")

    if path.suffix == ".pyi":
        black_config = replace(black_config, is_pyi=True)

    # run configured formatter
    content_str = content.decode(encoding)
    if ufmt_config.formatter == Formatter.black:
        try:
            content_str = black.format_file_contents(
                content_str,
                fast=False,
                mode=black_config,
            )
        except black.report.NothingChanged:
            pass
    elif ufmt_config.formatter == Formatter.ruff_api:
        ruff_format_options = ruff_api.FormatOptions(
            target_version=str(
                black_config.target_versions.pop()
                if black_config.target_versions
                else {black.mode.TargetVersion.PY38}
            ),
            line_width=black_config.line_length,
            preview=black_config.preview,
        )
        content_str = ruff_api.format_string(
            path.as_posix(), content_str, options=ruff_format_options
        )
    else:
        raise ValueError(f"{ufmt_config.formatter!r} is not a supported formatter")
    content = content_str.encode(encoding)

    if post_processor is not None:
        content = post_processor(path, content, encoding=encoding)

    return content


def ufmt_string(
    path: Path,
    content: str,
    usort_config: UsortConfig,
    black_config: Optional[BlackConfig] = None,
    encoding: Encoding = "utf-8",
) -> str:
    """
    Format an arbitrary string value for the given path.

    .. warning::
        Specifying the correct encoding is important! µfmt cannot do the right thing
        without the correct encoding if files contain byte values unrepresentable
        in UTF-8 (like ``\\ud800``) or PEP 263 coding lines.

        When in doubt, use :func:`ufmt_file`.

    .. deprecated:: 2.0
        Will be removed in µfmt version 3.0. Use :func:`ufmt_bytes` instead.
    """
    warn(
        "ufmt_string will be removed in version 3.0; use ufmt_bytes instead",
        DeprecationWarning,
        stacklevel=2,
    )

    black_config = black_config or BlackConfig()

    data = content.encode(encoding)
    data = ufmt_bytes(
        path,
        data,
        encoding=encoding,
        ufmt_config=load_config(path),
        black_config=black_config,
        usort_config=usort_config,
    )
    return data.decode(encoding)


def ufmt_file(
    path: Path,
    *,
    dry_run: bool = False,
    diff: bool = False,
    return_content: bool = False,
    ufmt_config_factory: Optional[UfmtConfigFactory] = None,
    black_config_factory: Optional[BlackConfigFactory] = None,
    usort_config_factory: Optional[UsortConfigFactory] = None,
    pre_processor: Optional[Processor] = None,
    post_processor: Optional[Processor] = None,
    root: Optional[Path] = None,
) -> Result:
    """
    Format a single file on disk, and returns a :class:`Result`.

    Passing ``dry_run = True`` will only format the file in memory, without writing
    changes to disk. Passing ``diff = True`` will generate a unified diff of changes
    on :attr:`Result.diff`. Passing ``return_content = True`` will also populate
    :attr:`Result.before` and :attr:`Result.after` with the bytes content of the file
    from before and after formatting, respectively.

    Any errors that occur during formatting will be caught, and those exceptions will
    be attached to the :attr:`Result.error` property of the result object. It is the
    responsibility of code calling this function to check for errors in results and
    handle or surface them appropriately.

    Optionally takes ``black_config_factory`` or ``usort_config_factory`` to override
    the default configuration detection for each respective tool. Factory functions
    must take a :class:`pathlib.Path` object and return a valid :class:`BlackConfig`
    or :class:`UsortConfig` object respectively.

    Optionally takes a pre- or post-processor matching the :class:`Processor` protocol.
    If given, the pre-processor will be called with the original byte string content
    before it has been run through µsort or black. The return value of the pre-processor
    will be used in place of the original content when formatting.
    If given, the post processor will be called with the updated byte string content
    after it has been run through µsort and black. The return value of the post
    processor will replace the final return value of :func:`ufmt_bytes`.

    Raising :exc:`ufmt.SkipFormatting` from a pre- or post-processor will result in
    "skipping" the file currently being formatted. The final contents will be unchanged,
    and the :attr:`Result.skipped` attribute will be set with the string message from
    the skip exception, or ``True`` if no message is given.
    """
    path = path.resolve()
    ufmt_config = (ufmt_config_factory or load_config)(path, root)
    black_config = (black_config_factory or make_black_config)(path)
    usort_config = (usort_config_factory or UsortConfig.find)(path)

    LOG.debug(f"Checking {path}")

    result = Result(path)

    try:
        src_contents, encoding, newline = read_file(path)
        dst_contents = ufmt_bytes(
            path,
            src_contents,
            encoding=encoding,
            ufmt_config=ufmt_config,
            black_config=black_config,
            usort_config=usort_config,
            pre_processor=pre_processor,
            post_processor=post_processor,
        )
    except SkipFormatting as e:
        dst_contents = src_contents
        result.skipped = str(e) or True
        return result

    except Exception as e:
        result.error = e
        return result

    if return_content or diff:
        src_result = normalize_result(src_contents, newline)
        dst_result = normalize_result(dst_contents, newline)

        if return_content:
            result.before = src_result
            result.after = dst_result

    if src_contents != dst_contents:
        result.changed = True

        if diff:
            result.diff = unified_diff(
                src_result.decode(encoding),
                dst_result.decode(encoding),
                path.as_posix(),
            )

        if not dry_run:
            LOG.debug(f"Formatted {path}")
            try:
                write_file(path, dst_contents, newline=newline)
                result.written = True
            except Exception as e:
                result.error = e

    return result


def ufmt_stdin(
    path: Path,
    *,
    dry_run: bool = False,
    diff: bool = False,
    return_content: bool = False,
    ufmt_config_factory: Optional[UfmtConfigFactory] = None,
    black_config_factory: Optional[BlackConfigFactory] = None,
    usort_config_factory: Optional[UsortConfigFactory] = None,
    pre_processor: Optional[Processor] = None,
    post_processor: Optional[Processor] = None,
) -> Result:
    """
    Wrapper around :func:`ufmt_file` for formatting content from STDIN.

    If given ``dry_run = False``, the resulting formatted content will be printed
    to STDOUT. Diff content and changed status will be returned as part of the
    :class:`Result` object as normal.

    Requires passing a path that represents the filesystem location matching the
    contents to be formatted. Reads bytes from STDIN until EOF, writes the content to
    a temporary location on disk, and formats that file on disk using :func:`ufmt_file`.
    The :class:`Result` object will be updated to match the location given by ``path``.

    See :func:`ufmt_file` for details on parameters, config factories,
    and post processors. All parameters are passed through to :func:`ufmt_file`.
    """
    ufmt_config = (ufmt_config_factory or load_config)(path, None)
    black_config = (black_config_factory or make_black_config)(path)
    usort_config = (usort_config_factory or UsortConfig.find)(path)

    with TemporaryDirectory() as td:
        tdp = Path(td).resolve()
        temp_path = tdp / path.name

        # read from stdin
        content = sys.stdin.buffer.read()
        temp_path.write_bytes(content)

        result = ufmt_file(
            temp_path,
            dry_run=dry_run,
            diff=diff,
            return_content=return_content,
            ufmt_config_factory=lambda _path, _root: ufmt_config,
            black_config_factory=lambda _path: black_config,
            usort_config_factory=lambda _path: usort_config,
            pre_processor=pre_processor,
            post_processor=post_processor,
        )
        result.path = path
        if result.diff and path != STDIN:
            real_path_str = path.as_posix()

            def replacement(match: Match[str]) -> str:
                return match.group(1) + real_path_str

            pattern = re.compile(r"^((?:---|\+\+\+)\s+).+$", re.M)
            result.diff = pattern.sub(replacement, result.diff)

        # write to stdout if not check/diff mode
        if not dry_run:
            content = temp_path.read_bytes()
            sys.stdout.buffer.write(content)
            sys.stdout.buffer.flush()

        return result


def ufmt_paths(
    paths: Sequence[Path],
    *,
    dry_run: bool = False,
    diff: bool = False,
    return_content: bool = False,
    ufmt_config_factory: Optional[UfmtConfigFactory] = None,
    black_config_factory: Optional[BlackConfigFactory] = None,
    usort_config_factory: Optional[UsortConfigFactory] = None,
    pre_processor: Optional[Processor] = None,
    post_processor: Optional[Processor] = None,
    concurrency: Optional[int] = None,
    root: Optional[Path] = None,
) -> Generator[Result, None, None]:
    """
    Format one or more paths, recursively, ignoring any files excluded by configuration.

    Uses trailrunner to first walk all paths, and then to run :func:`ufmt_file` on each
    matching file found. If more than one eligible file is discovered after walking the
    given paths, all files will be formatted using a process pool for improved
    performance and CPU utilization.

    Returns a generator yielding :class:`Result` objects for each file formatted.
    Any errors that occur during formatting will be caught, and those exceptions will
    be attached to the :attr:`Result.error` property of the result object. It is the
    responsibility of code calling this function to check for errors in results and
    handle or surface them appropriately.

    If the first given path is STDIN (``Path("-")``), then content will be formatted
    from STDIN using :func:`ufmt_stdin`. Results will be printed to STDOUT.
    A second path argument may be given, which represents the original content's true
    path name, and will be used when printing status messages, diffs, or errors.
    Any further path names will result in a runtime error.

    See :func:`ufmt_file` for details on parameters, config factories,
    and post processors. All parameters are passed through to :func:`ufmt_file`.

    .. note::
        Factory and post processing functions must be pickleable when using
        :func:`ufmt_paths`.
    """
    if not paths:
        return

    # format stdin and short-circuit
    if paths[0] == STDIN:
        if len(paths) > 2:
            raise ValueError("too many stdin paths")
        elif len(paths) == 2:
            _, path = paths
        else:
            path = Path("stdin")
        yield ufmt_stdin(
            path,
            dry_run=dry_run,
            diff=diff,
            return_content=return_content,
            ufmt_config_factory=ufmt_config_factory,
            black_config_factory=black_config_factory,
            usort_config_factory=usort_config_factory,
            pre_processor=pre_processor,
            post_processor=post_processor,
        )
        return

    runner = (
        Trailrunner() if concurrency is None else Trailrunner(concurrency=concurrency)
    )

    def generate_paths() -> Generator[Path, None, None]:
        """
        yield paths to format, using trailrunner to walk directories and exclude paths
        """
        for path in paths:
            if path == STDIN:
                LOG.warning("Cannot mix stdin ('-') with normal paths, ignoring")
                continue
            config = (ufmt_config_factory or load_config)(path, root)
            yield from runner.walk(path, excludes=config.excludes)

    fn = partial(
        ufmt_file,
        dry_run=dry_run,
        diff=diff,
        return_content=return_content,
        ufmt_config_factory=ufmt_config_factory,
        black_config_factory=black_config_factory,
        usort_config_factory=usort_config_factory,
        pre_processor=pre_processor,
        post_processor=post_processor,
    )

    # we have a generator that yields paths to format, but for large lists of paths
    # or large directories, we want to start formatting files as soon as possible rather
    # than waiting to finish generating the entire set of paths. we also want to skip
    # using a process pool for the base case where we only need to format a single file.
    #
    # we do this here by manually pumping the generator twice, and either exit early
    # if the first pump yields nothing (no paths to format), or immediately format
    # the first item in the same process if the second pump yields nothing (only one
    # path to format). Otherwise, we fall through and pass the first and second items,
    # plus the entire rest of the generator, to trailrunner to format everything using
    # the process pool, yielding more paths from the generator on the main process
    # while the child processes start formatting paths.

    gen = generate_paths()

    try:
        first = next(gen)
    except StopIteration:  # no paths to format
        return

    try:
        second = next(gen)
    except StopIteration:  # only one path to format
        # skip multiprocessing for a single path
        yield fn(first)
        return

    # multiple paths to format
    combined = chain([first, second], gen)  # combine first, second, and the rest
    for _, result in runner.run_iter(combined, fn):
        yield result
