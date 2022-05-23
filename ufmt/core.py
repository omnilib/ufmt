# Copyright 2021 John Reese, Tim Hatch
# Licensed under the MIT license

import logging
from dataclasses import replace
from functools import partial
from pathlib import Path
from typing import List, Optional
from warnings import warn

from black import format_file_contents, NothingChanged
from moreorless.click import unified_diff
from trailrunner import Trailrunner
from usort import usort

from .config import ufmt_config
from .types import (
    BlackConfig,
    BlackConfigFactory,
    Encoding,
    FileContent,
    PostProcessor,
    Result,
    UsortConfig,
    UsortConfigFactory,
)
from .util import make_black_config, read_file, write_file

LOG = logging.getLogger(__name__)


def ufmt_bytes(
    path: Path,
    content: FileContent,
    *,
    encoding: Encoding = "utf-8",
    black_config: BlackConfig,
    usort_config: UsortConfig,
    post_processor: Optional[PostProcessor] = None,
) -> FileContent:
    """
    Format arbitrary bytes for the given path.

    Requires passing valid config objects for both black and µsort. If the given path
    represents a type stub (has a ``.pyi`` suffix), the black config object will be
    updated to set ``is_pyi = True``.

    Optionally takes a post processor matching the :class:`PostProcessor` protocol.
    If given, the post processor will be called with the updated byte string content
    after it has been run through µsort and black. The return value of the post
    processor will replace the final return value of :func:`ufmt_bytes`.

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
    result = usort(content, usort_config, path)

    if path.suffix == ".pyi":
        black_config = replace(black_config, is_pyi=True)

    try:
        content_str = result.output.decode(encoding)
        content_str = format_file_contents(content_str, fast=False, mode=black_config)
        content = content_str.encode(encoding)

    except NothingChanged:
        content = result.output

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
        black_config=black_config,
        usort_config=usort_config,
    )
    return data.decode(encoding)


def ufmt_file(
    path: Path,
    *,
    dry_run: bool = False,
    diff: bool = False,
    black_config_factory: Optional[BlackConfigFactory] = None,
    usort_config_factory: Optional[UsortConfigFactory] = None,
    post_processor: Optional[PostProcessor] = None,
) -> Result:
    """
    Format a single file on disk, and returns a :class:`Result`.

    Passing ``dry_run = True`` will only format the file in memory, without writing
    changes to disk. Passing ``diff = True`` will generate a unified diff of changes
    on the :class:`Result` object.

    Optionally takes ``black_config_factory`` or ``usort_config_factory`` to override
    the default configuration detection for each respective tool. Factory functions
    must take a :class:`pathlib.Path` object and return a valid :class:`BlackConfig`
    or :class:`UsortConfig` object respectively.

    Optionally takes a post processor matching the :class:`PostProcessor` protocol.
    If given, the post processor will be called with the updated byte string content
    after it has been run through µsort and black. The return value of the post
    processor will replace the final return value of :func:`ufmt_bytes`.
    """
    path = path.resolve()
    black_config = (black_config_factory or make_black_config)(path)
    usort_config = (usort_config_factory or UsortConfig.find)(path)

    LOG.debug(f"Checking {path}")

    src_contents, encoding, newline = read_file(path)
    dst_contents = ufmt_bytes(
        path,
        src_contents,
        encoding=encoding,
        black_config=black_config,
        usort_config=usort_config,
        post_processor=post_processor,
    )

    result = Result(path)

    if src_contents != dst_contents:
        result.changed = True

        if diff:
            result.diff = unified_diff(
                src_contents.decode(encoding),
                dst_contents.decode(encoding),
                path.as_posix(),
            )

        if not dry_run:
            LOG.debug(f"Formatted {path}")
            write_file(path, dst_contents, newline=newline)
            result.written = True

    return result


def ufmt_paths(
    paths: List[Path],
    *,
    dry_run: bool = False,
    diff: bool = False,
    black_config_factory: Optional[BlackConfigFactory] = None,
    usort_config_factory: Optional[UsortConfigFactory] = None,
    post_processor: Optional[PostProcessor] = None,
) -> List[Result]:
    """
    Format one or more paths, recursively, ignoring any files excluded by configuration.

    Uses trailrunner to first walk all paths, and then to run :func:`ufmt_file` on each
    matching file found. If more than one eligible file is discovered after walking the
    given paths, all files will be formatted using a process pool for improved
    performance and CPU utilization.

    Returns a list of :class:`Result` objects for each file formatted.

    See :func:`ufmt_file` for details on parameters, config factories,
    and post processors. All parameters are passed through to :func:`ufmt_file`.

    .. note::
        Factory and post processing functions must be pickleable when using
        :func:`ufmt_paths`.
    """
    all_paths: List[Path] = []
    runner = Trailrunner()
    for path in paths:
        config = ufmt_config(path)
        all_paths.extend(runner.walk(path, excludes=config.excludes))

    fn = partial(
        ufmt_file,
        dry_run=dry_run,
        diff=diff,
        black_config_factory=black_config_factory,
        usort_config_factory=usort_config_factory,
        post_processor=post_processor,
    )
    results = list(runner.run(all_paths, fn).values())

    return results
