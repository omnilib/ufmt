# Copyright 2022 Amethyst Reese, Tim Hatch
# Licensed under the MIT license

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast
from unittest import TestCase

import tomlkit
from black.mode import TargetVersion

import ufmt
from .core import FAKE_CONFIG, POORLY_FORMATTED_CODE

FAKE_CONTENT = b"""\
import foo

def bar():
    print("hello world")
"""


class UtilTest(TestCase):
    def test_black_config(self) -> None:
        doc = tomlkit.parse(FAKE_CONFIG)
        black = tomlkit.table()
        black["target_version"] = ["py36", "py37"]
        black["skip_string_normalization"] = True
        black["line_length"] = 87
        cast(tomlkit.container.Container, doc["tool"]).add("black", black)

        with TemporaryDirectory() as td:
            tdp = Path(td)

            pyproj = tdp / "pyproject.toml"
            pyproj.write_text(tomlkit.dumps(doc))

            f = tdp / "foo.py"
            f.write_text(POORLY_FORMATTED_CODE)

            result = ufmt.ufmt_file(f, dry_run=True)
            self.assertTrue(result.changed)

            mode = ufmt.util.make_black_config(tdp)

            with self.subTest("target_versions"):
                self.assertEqual(
                    mode.target_versions,
                    {TargetVersion[item.upper()] for item in ("py36", "py37")},
                )

            with self.subTest("string_normalization"):
                self.assertFalse(mode.string_normalization)

            with self.subTest("line_length"):
                self.assertEqual(mode.line_length, 87)

    def test_normalize_content(self) -> None:
        cases = (
            (b"hello world", None, (b"hello world", b"\n")),
            (b"hello\nworld\n", None, (b"hello\nworld\n", b"\n")),
            (b"hello\r\nworld\r\n", None, (b"hello\nworld\n", b"\r\n")),
            (b"hello world", b"\n", (b"hello world", b"\n")),
            (b"hello\nworld\n", b"\n", (b"hello\nworld\n", b"\n")),
            (b"hello\r\nworld\r\n", b"\n", (b"hello\r\nworld\r\n", b"\n")),
            (b"hello world", b"\r\n", (b"hello world", b"\r\n")),
            (b"hello\nworld\n", b"\r\n", (b"hello\nworld\n", b"\r\n")),
            (b"hello\r\nworld\r\n", b"\r\n", (b"hello\nworld\n", b"\r\n")),
        )
        for idx, (content, newline, expected) in enumerate(cases):
            with self.subTest(idx):
                self.assertEqual(
                    expected, ufmt.util.normalize_content(content, newline)
                )

    def test_normalize_result(self) -> None:
        cases = (
            (b"hello world", b"\n", b"hello world"),
            (b"hello\nworld\n", b"\n", b"hello\nworld\n"),
            (b"hello\r\nworld\r\n", b"\n", b"hello\r\nworld\r\n"),
            (b"hello world", b"\r\n", b"hello world"),
            (b"hello\nworld\n", b"\r\n", b"hello\r\nworld\r\n"),
        )
        for idx, (content, newline, expected) in enumerate(cases):
            with self.subTest(idx):
                self.assertEqual(expected, ufmt.util.normalize_result(content, newline))

    def test_read_file(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            foo = tdp / "foo.py"

            with self.subTest("unix newlines"):
                foo.write_bytes(FAKE_CONTENT)

                result = ufmt.util.read_file(foo)
                expected = (FAKE_CONTENT, "utf-8", b"\n")
                self.assertTupleEqual(expected, result)

            with self.subTest("windows newlines"):
                content = FAKE_CONTENT.replace(b"\n", b"\r\n")
                foo.write_bytes(content)

                result = ufmt.util.read_file(foo)
                expected = (FAKE_CONTENT, "utf-8", b"\r\n")
                self.assertTupleEqual(expected, result)

            with self.subTest("empty file"):
                foo.write_bytes(b"")

                result = ufmt.util.read_file(foo)
                expected = (b"", "utf-8", b"\n")
                self.assertTupleEqual(expected, result)
