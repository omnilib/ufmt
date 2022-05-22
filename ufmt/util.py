# Copyright 2021 John Reese, Tim Hatch
# Licensed under the MIT license

import tokenize
from pathlib import Path
from typing import Tuple

from black import find_pyproject_toml, parse_pyproject_toml, TargetVersion

from .types import BlackConfig, Encoding, FileContent


def make_black_config(path: Path) -> BlackConfig:
    """
    Generate a basic black config object for the given path.
    """
    config_file = find_pyproject_toml((str(path),))
    if not config_file:
        return BlackConfig()

    config = parse_pyproject_toml(config_file)

    # manually patch options that do not have a 1-to-1 match in Mode arguments
    config["target_versions"] = {
        TargetVersion[val.upper()] for val in config.pop("target_version", [])
    }
    config["string_normalization"] = not config.pop("skip_string_normalization", False)

    names = {
        field.name
        for field in BlackConfig.__dataclass_fields__.values()  # type: ignore[attr-defined]
    }
    config = {name: value for name, value in config.items() if name in names}

    return BlackConfig(**config)


def read_file(path: Path) -> Tuple[FileContent, Encoding]:
    with open(path, "rb") as buf:
        encoding, _ = tokenize.detect_encoding(buf.readline)
        buf.seek(0)
        content = buf.read()
        return content, encoding


def write_file(path: Path, content: FileContent) -> None:
    with open(path, "wb") as buf:
        buf.write(content)
