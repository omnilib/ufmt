# Copyright 2021 John Reese, Tim Hatch
# Licensed under the MIT license

import logging
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import partial
from multiprocessing import get_context
from pathlib import Path
from typing import List, Optional, Set

from black import decode_bytes, format_file_contents, Mode, NothingChanged
from moreorless.click import unified_diff
from usort.config import Config
from usort.sorting import usort_string
from usort.util import walk

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

    for path in paths:
        if path.is_dir():
            # TODO use black's version of walk?
            LOG.debug(f"Walking {path}")
            files.update(walk(path, "*.py"))
        else:
            files.add(path)

    with EXECUTOR() as exe:
        fn = partial(ufmt_file, dry_run=dry_run, diff=diff)
        results = list(exe.map(fn, files))

    return results
