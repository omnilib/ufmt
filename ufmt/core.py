# Copyright 2021 John Reese, Tim Hatch
# Licensed under the MIT license

import logging
from pathlib import Path
from typing import List

from black import decode_bytes, format_file_contents, Mode, NothingChanged
from usort.config import Config
from usort.sorting import usort_string
from usort.util import walk

LOG = logging.getLogger(__name__)


def ufmt_string(path: Path, content: str, config: Config) -> str:
    content = usort_string(content, config, path)
    mode = Mode()  # TODO

    try:
        content = format_file_contents(content, fast=False, mode=mode)
    except NothingChanged:
        pass

    return content


def ufmt_file(path: Path, dry_run: bool = False) -> bool:
    changed = False
    config = Config.find(path)

    with open(path, "rb") as buf:
        src_contents, encoding, newline = decode_bytes(buf.read())

    dst_contents = ufmt_string(path, src_contents, config)

    if src_contents != dst_contents:
        changed = True

        if dry_run:
            LOG.info(f"Would format {path}")
        else:
            LOG.debug(f"Formatted {path}")
            with open(path, "w", encoding=encoding, newline=newline) as f:
                f.write(dst_contents)

    return changed


def ufmt_paths(paths: List[Path], dry_run: bool = False) -> bool:
    changed = False

    for path in paths:
        if path.is_dir():
            # TODO use black's version of walk?
            LOG.debug(f"Walking {path}")
            files = walk(path, "*.py")
        else:
            files = [path]

        for src in files:
            LOG.debug(f"Found {src}")
            changed |= ufmt_file(src, dry_run=dry_run)

    return changed
