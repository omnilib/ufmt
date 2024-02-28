# Copyright 2022 Amethyst Reese, Tim Hatch
# Licensed under the MIT license

import os
import tokenize
from pathlib import Path
from typing import Tuple

from black.files import find_pyproject_toml, parse_pyproject_toml
from black.mode import TargetVersion

from .types import BlackConfig, Encoding, FileContent, Newline


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

    names = {field.name for field in BlackConfig.__dataclass_fields__.values()}
    config = {name: value for name, value in config.items() if name in names}

    return BlackConfig(**config)


def normalize_result(content: FileContent, newline: Newline) -> FileContent:
    """
    Convert bytes content with UNIX style line endings to the given style.

    No-op if ``newline`` is given as ``b"\\n"``.
    """
    if newline != b"\n":
        content = content.replace(b"\n", newline)
    return content


def read_file(path: Path) -> Tuple[FileContent, Encoding, Newline]:
    """
    Read a file from disk, detect encoding, and normalize newlines.

    Returns a tuple of file contents, file encoding, and original newline style.
    File contents are in bytes, with newlines normalized to UNIX style `"\\n"`.
    File encoding is detected either by PEP 263 coding line or encoding cookie.
    Newline is detected from the first line ending, and assumes that all lines in the
    file will have (or should have) consistent line endings.

    Intended for use with :func:`write_file`, where newlines get converted back to the
    original newline style before being written to disk.
    """
    with open(path, "rb") as buf:
        encoding, lines = tokenize.detect_encoding(buf.readline)
        newline = b"\r\n" if lines and lines[0].endswith(b"\r\n") else b"\n"

        buf.seek(0)
        content = buf.read()
        content = content.replace(newline, b"\n")
        return content, encoding, newline


def write_file(path: Path, content: FileContent, newline: Newline) -> None:
    """
    Write to a file on disk, normalizing to the given newline style.

    Expects given content in bytes, with UNIX style line endings. UNIX style newlines
    will be converted to the given newline style before writing bytes to disk.

    Intended for use with content and newline style from :func:`read_file`, so that
    newlines are correctly normalized back to their original style when writing to disk.
    """
    content = normalize_result(content, newline)
    with open(path, "wb") as buf:
        buf.write(content)


def enable_libcst_native() -> None:
    """
    Enable libcst native parser if available

    TODO: replace with usort.util.enable_libcst_native or similar
    """
    try:
        import libcst.native  # noqa: F401

        os.environ["LIBCST_PARSER_TYPE"] = "native"
    except ImportError:  # pragma: nocover
        pass
