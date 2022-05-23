# Copyright 2021 John Reese
# Licensed under the MIT license

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import call, Mock, patch

import trailrunner

import ufmt
from ufmt.types import BlackConfig, Encoding, UsortConfig

FAKE_CONFIG = """
[tool.ufmt]
excludes = [
    "foo/frob/",
    "__init__.py",
]
"""

POORLY_FORMATTED_CODE = """\
import click
from re import compile
import sys
import volatile



class Foo:
    var:  bool=123
    def method(foo,
               bar):
            '''Some docstring'''
            value = [str(some_really_long_var) for some_really_long_var in range(10) if some_really_long_var > 5]
            print(f'hello {value}!')
def func(arg:str="default")->bool:
        return arg  =="default" """  # noqa: E501

CORRECTLY_FORMATTED_CODE = '''\
import sys
from re import compile

import click
import volatile


class Foo:
    var: bool = 123

    def method(foo, bar):
        """Some docstring"""
        value = [
            str(some_really_long_var)
            for some_really_long_var in range(10)
            if some_really_long_var > 5
        ]
        print(f"hello {value}!")


def func(arg: str = "default") -> bool:
    return arg == "default"
'''

POORLY_FORMATTED_STUB = """\
import click
import os

def foo(a: int, b: str) -> bool:
    ...

class Bar:
    def hello(
        self,
    ) -> None:
        ...
"""

CORRECTLY_FORMATTED_STUB = """\
import os

import click

def foo(a: int, b: str) -> bool: ...

class Bar:
    def hello(
        self,
    ) -> None: ...
"""


@patch.object(trailrunner.core.Trailrunner, "DEFAULT_EXECUTOR", ThreadPoolExecutor)
class CoreTest(TestCase):
    maxDiff = None

    def test_ufmt_bytes(self):
        black_config = BlackConfig()
        usort_config = UsortConfig()

        with self.subTest("changed"):
            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                POORLY_FORMATTED_CODE.encode(),
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE.encode(), result)

        with self.subTest("unchanged"):
            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                CORRECTLY_FORMATTED_CODE.encode(),
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE.encode(), result)

        with self.subTest("type stub"):
            result = ufmt.ufmt_bytes(
                Path("foo.pyi"),
                POORLY_FORMATTED_STUB.encode(),
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_STUB.encode(), result)

    def test_ufmt_bytes_post_processor(self):
        def post_processor(
            path: Path, content: bytes, *, encoding: Encoding = "utf-8"
        ) -> bytes:
            return content + b"\nprint('hello')\n"

        black_config = BlackConfig()
        usort_config = UsortConfig()

        result = ufmt.ufmt_bytes(
            Path("foo.py"),
            CORRECTLY_FORMATTED_CODE.encode(),
            black_config=black_config,
            usort_config=usort_config,
            post_processor=post_processor,
        )

        self.assertEqual(
            CORRECTLY_FORMATTED_CODE.encode() + b"\nprint('hello')\n", result
        )

    def test_ufmt_string(self):
        black_config = BlackConfig()
        usort_config = UsortConfig()

        with self.subTest("changed"):
            result = ufmt.ufmt_string(
                Path("foo.py"),
                POORLY_FORMATTED_CODE,
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE, result)

        with self.subTest("unchanged"):
            result = ufmt.ufmt_string(
                Path("foo.py"),
                CORRECTLY_FORMATTED_CODE,
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE, result)

        with self.subTest("type stub"):
            result = ufmt.ufmt_string(
                Path("foo.pyi"),
                POORLY_FORMATTED_STUB,
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_STUB, result)

    def test_ufmt_file(self):
        with TemporaryDirectory() as td:
            td = Path(td)
            f = td / "foo.py"
            f.write_text(POORLY_FORMATTED_CODE)

            with self.subTest("dry run"):
                result = ufmt.ufmt_file(f, dry_run=True)
                self.assertTrue(result.changed)
                self.assertIsNone(result.diff)
                self.assertEqual(POORLY_FORMATTED_CODE, f.read_text())

            with self.subTest("dry run with diff"):
                result = ufmt.ufmt_file(f, dry_run=True, diff=True)
                self.assertTrue(result.changed)
                self.assertIsNotNone(result.diff)
                self.assertEqual(POORLY_FORMATTED_CODE, f.read_text())

            with self.subTest("for reals"):
                result = ufmt.ufmt_file(f)
                self.assertTrue(result.changed)
                self.assertEqual(CORRECTLY_FORMATTED_CODE, f.read_text())

            with self.subTest("already formatted"):
                f.write_text(CORRECTLY_FORMATTED_CODE)

                result = ufmt.ufmt_file(f)
                self.assertFalse(result.changed)
                self.assertEqual(CORRECTLY_FORMATTED_CODE, f.read_text())

            with self.subTest("already formatted, unix newlines"):
                unix_content = CORRECTLY_FORMATTED_CODE.encode().replace(b"\r\n", b"\n")
                f.write_bytes(unix_content)

                result = ufmt.ufmt_file(f)
                self.assertFalse(result.changed)
                self.assertEqual(unix_content, f.read_bytes())

            with self.subTest("already formatted, windows newlines"):
                windows_content = CORRECTLY_FORMATTED_CODE.encode().replace(
                    b"\n", b"\r\n"
                )
                f.write_bytes(windows_content)

                result = ufmt.ufmt_file(f)
                self.assertFalse(result.changed)
                self.assertEqual(windows_content, f.read_bytes())

    def test_ufmt_paths(self):
        with TemporaryDirectory() as td:
            td = Path(td)
            f1 = td / "bar.py"
            sd = td / "foo"
            sd.mkdir()
            f2 = sd / "baz.py"
            f3 = sd / "frob.py"

            for f in f1, f2, f3:
                f.write_text(POORLY_FORMATTED_CODE)

            file_wrapper = Mock(name="ufmt_file", wraps=ufmt.ufmt_file)
            with patch("ufmt.core.ufmt_file", file_wrapper):
                with self.subTest("files"):
                    results = ufmt.ufmt_paths([f1, f3], dry_run=True)
                    self.assertEqual(2, len(results))
                    file_wrapper.assert_has_calls(
                        [
                            call(
                                f1,
                                dry_run=True,
                                diff=False,
                                black_config_factory=None,
                                usort_config_factory=None,
                                post_processor=None,
                            ),
                            call(
                                f3,
                                dry_run=True,
                                diff=False,
                                black_config_factory=None,
                                usort_config_factory=None,
                                post_processor=None,
                            ),
                        ],
                        any_order=True,
                    )
                    self.assertTrue(all(r.changed for r in results))
                    file_wrapper.reset_mock()

                with self.subTest("files with diff"):
                    results = ufmt.ufmt_paths([f1, f3], dry_run=True, diff=True)
                    self.assertEqual(2, len(results))
                    file_wrapper.assert_has_calls(
                        [
                            call(
                                f1,
                                dry_run=True,
                                diff=True,
                                black_config_factory=None,
                                usort_config_factory=None,
                                post_processor=None,
                            ),
                            call(
                                f3,
                                dry_run=True,
                                diff=True,
                                black_config_factory=None,
                                usort_config_factory=None,
                                post_processor=None,
                            ),
                        ],
                        any_order=True,
                    )
                    self.assertTrue(all(r.changed for r in results))
                    file_wrapper.reset_mock()

                with self.subTest("subdir"):
                    results = ufmt.ufmt_paths([sd])
                    file_wrapper.assert_has_calls(
                        [
                            call(
                                f2,
                                dry_run=False,
                                diff=False,
                                black_config_factory=None,
                                usort_config_factory=None,
                                post_processor=None,
                            ),
                            call(
                                f3,
                                dry_run=False,
                                diff=False,
                                black_config_factory=None,
                                usort_config_factory=None,
                                post_processor=None,
                            ),
                        ],
                        any_order=True,
                    )
                    self.assertTrue(all(r.changed for r in results))
                    file_wrapper.reset_mock()

    def test_ufmt_paths_config(self):
        with TemporaryDirectory() as td:
            td = Path(td).resolve()
            md = td / "foo"
            md.mkdir()
            f1 = md / "__init__.py"
            f2 = md / "foo.py"
            sd = md / "frob/"
            sd.mkdir()
            f3 = sd / "main.py"

            for f in f1, f2, f3:
                f.write_text(POORLY_FORMATTED_CODE)

            pyproj = td / "pyproject.toml"
            pyproj.write_text(FAKE_CONFIG)

            file_wrapper = Mock(name="ufmt_file", wraps=ufmt.ufmt_file)
            with patch("ufmt.core.ufmt_file", file_wrapper):
                ufmt.ufmt_paths([td])
                file_wrapper.assert_has_calls(
                    [
                        call(
                            f2,
                            dry_run=False,
                            diff=False,
                            black_config_factory=None,
                            usort_config_factory=None,
                            post_processor=None,
                        ),
                    ],
                    any_order=True,
                )
                self.assertEqual(f1.read_text(), POORLY_FORMATTED_CODE)
                self.assertEqual(f2.read_text(), CORRECTLY_FORMATTED_CODE)
                self.assertEqual(f3.read_text(), POORLY_FORMATTED_CODE)
