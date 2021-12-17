# Copyright 2021 John Reese, Tim Hatch
# Licensed under the MIT license

import logging
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import List, Optional

from black import (
    decode_bytes,
    find_pyproject_toml,
    format_file_contents,
    Mode,
    NothingChanged,
    parse_pyproject_toml,
    TargetVersion,
)
from moreorless.click import unified_diff
from trailrunner import Trailrunner
from usort.config import Config as UsortConfig
from usort.sorting import usort_string

from .config import ufmt_config

LOG = logging.getLogger(__name__)


@dataclass
class Result:
    path: Path
    changed: bool = False
    written: bool = False
    diff: Optional[str] = None


def ufmt_string(
    path: Path,
    content: str,
    usort_config: UsortConfig,
    black_config: Optional[Mode] = None,
) -> str:
    content = usort_string(content, usort_config, path)
    mode = black_config or Mode()

    if path.suffix == ".pyi":
        mode.is_pyi = True

    try:
        content = format_file_contents(content, fast=False, mode=mode)
    except NothingChanged:
        pass

    return content


def make_black_config(path: Path) -> Mode:
    config_file = find_pyproject_toml((str(path),))
    if not config_file:
        return Mode()

    config = parse_pyproject_toml(config_file)

    # manually patch options that do not have a 1-to-1 match in Mode arguments
    config["target_versions"] = {
        TargetVersion[val.upper()] for val in config.pop("target_version", [])
    }
    config["string_normalization"] = not config.pop("skip_string_normalization", False)

    names = {
        field.name
        for field in Mode.__dataclass_fields__.values()  # type: ignore[attr-defined]
    }
    config = {name: value for name, value in config.items() if name in names}

    return Mode(**config)


def ufmt_file(path: Path, dry_run: bool = False, diff: bool = False) -> Result:
    usort_config = UsortConfig.find(path)
    black_config = make_black_config(path)

    LOG.debug(f"Checking {path}")

    with open(path, "rb") as buf:
        src_contents, encoding, newline = decode_bytes(buf.read())

    dst_contents = ufmt_string(path, src_contents, usort_config, black_config)

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
    all_paths: List[Path] = []
    runner = Trailrunner()
    for path in paths:
        config = ufmt_config(path)
        all_paths.extend(runner.walk(path, excludes=config.excludes))

    fn = partial(ufmt_file, dry_run=dry_run, diff=diff)
    results = list(runner.run(all_paths, fn).values())

    return results
