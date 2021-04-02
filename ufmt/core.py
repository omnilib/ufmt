# Copyright 2021 John Reese, Tim Hatch
# Licensed under the MIT license

import inspect
import logging
import re
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import partial
from multiprocessing import get_context
from pathlib import Path
from typing import List, Optional, Set

from black import (
    DEFAULT_INCLUDES,
    DEFAULT_EXCLUDES,
    Mode,
    NothingChanged,
    Report,
    decode_bytes,
    find_project_root,
    format_file_contents,
    gen_python_files,
    get_gitignore,
)
from moreorless.click import unified_diff
from usort.config import Config
from usort.sorting import usort_string

BLACK_HAS_EXTEND_EXCLUDE = (
    "extend_exclude" in inspect.signature(gen_python_files).parameters
)

LOG = logging.getLogger(__name__)

CONTEXT = get_context("spawn")
EXECUTOR = ProcessPoolExecutor


@dataclass
class Result:
    path: Path
    changed: bool = False
    written: bool = False
    diff: Optional[str] = None


def ufmt_string(path: Path, content: str, config: Config) -> str:
    content = usort_string(content, config, path)
    mode = Mode()  # TODO

    try:
        content = format_file_contents(content, fast=False, mode=mode)
    except NothingChanged:
        pass

    return content


def ufmt_file(path: Path, dry_run: bool = False, diff: bool = False) -> Result:
    config = Config.find(path)

    LOG.debug(f"Checking {path}")

    with open(path, "rb") as buf:
        src_contents, encoding, newline = decode_bytes(buf.read())

    dst_contents = ufmt_string(path, src_contents, config)

    result = Result(path)

    if src_contents != dst_contents:
        result.changed = True

        if diff:
            result.diff = unified_diff(src_contents, dst_contents, path.as_posix())

        if not dry_run:
            LOG.debug(f"Formatted {path}")
            with open(path, "w", encoding=encoding, newline=newline) as f:
                f.write(dst_contents)
            result.written = True

    return result


def ufmt_paths(
    paths: List[Path], dry_run: bool = False, diff: bool = False
) -> List[Result]:
    files: Set[Path] = set()

    # This relies an awful lot on black's internals, which appears on track to
    # change between 20.8b1 and 21.x.  If we're serious about path walking
    # (especially reading config, etc) we should probably vendor the parts we
    # care about.

    report = Report()  # write-only
    include = re.compile(DEFAULT_INCLUDES)
    exclude = re.compile(DEFAULT_EXCLUDES)

    root = find_project_root(str(x) for x in paths)
    gitignore = get_gitignore(root)

    for path in paths:
        if path.is_file():
            files.add(path)
        elif path.is_dir():
            kwargs = {
                "paths": path.iterdir(),
                "root": root,
                "include": include,
                "exclude": exclude,
                "force_exclude": None,
                "report": report,
                "gitignore": gitignore,
            }
            if BLACK_HAS_EXTEND_EXCLUDE:  # pragma: no cover
                # Grmbl, if they gave this a default of null there
                # wouldn't be such shenanigans.
                kwargs["extend_exclude"] = None

            files.update(gen_python_files(**kwargs))
        else:
            raise ValueError(f"Listed path {path} is not a file or directory")

    with EXECUTOR() as exe:
        fn = partial(ufmt_file, dry_run=dry_run, diff=diff)
        results = list(exe.map(fn, files))

    return results
