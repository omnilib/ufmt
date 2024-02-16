# Copyright 2022 Amethyst Reese, Tim Hatch
# Licensed under the MIT license

import os
import sqlite3
import time
import tokenize
import zlib
from contextlib import closing
from pathlib import Path
from typing import Optional, Tuple

from black import find_pyproject_toml, parse_pyproject_toml, TargetVersion

from .types import BlackConfig, Encoding, FileContent, Newline, SkipFormatting


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


class ResultCache:
    def __init__(
        self,
        cache_path: Optional[Path] = None,
        threshold: int = 7 * 86400,
    ) -> None:
        if cache_path is None:
            cache_path = Path.cwd() / ".ufmt_cache" / "cache.db"
            cache_path.parent.mkdir(exist_ok=True)
        self.cache_path = cache_path
        self.threshold = threshold

    def prepare(self) -> None:
        with closing(sqlite3.connect(self.cache_path)) as db:
            with db:
                db.execute(
                    """
                    create table if not exists clean (
                        `path` text,
                        `crc` integer,
                        `seen` integer,
                        unique(`path`, `crc`)
                    )"""
                )

    def cleanup(self) -> None:
        with closing(sqlite3.connect(self.cache_path)) as db:
            with db:
                db.execute(
                    """
                    delete from clean where rowid in (
                        select rowid from clean where `seen` < ?
                    )
                    """,
                    (int(time.time()) - self.threshold,),
                )

    def check(self, path: Path, content: FileContent) -> bool:
        path_str = path.as_posix()
        crc = zlib.adler32(content)
        with closing(sqlite3.connect(self.cache_path)) as db:
            with db:
                cursor = db.execute(
                    "select * from clean where `path` = ? and `crc` = ?",
                    (path_str, crc),
                )
                if cursor.fetchone():
                    db.execute(
                        "update clean set `seen` = ? where `path` = ? and `crc` = ?",
                        (int(time.time()), path_str, crc),
                    )
                    return True
        return False

    def mark(self, path: Path, content: FileContent) -> None:
        path_str = path.as_posix()
        crc = zlib.adler32(content)
        with closing(sqlite3.connect(self.cache_path)) as db:
            with db:
                db.execute(
                    "insert into clean (`path`, `crc`, `seen`) values (?, ?, ?) on conflict (`path`, `crc`) do update set `seen` = excluded.`seen`",
                    (path_str, crc, int(time.time())),
                )
