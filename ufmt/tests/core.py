# Copyright 2021 John Reese
# Licensed under the MIT license

import io
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import call, Mock, patch

import trailrunner
from libcst import ParserSyntaxError

import ufmt
from ufmt.core import ufmt_stdin
from ufmt.types import BlackConfig, Encoding, Result, STDIN, UsortConfig

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

INVALID_SYNTAX = """\
print "hello world"
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

    def test_ufmt_bytes_pre_processor(self):
        def pre_processor(
            path: Path, content: bytes, *, encoding: Encoding = "utf-8"
        ) -> bytes:
            return content + b"print('hello')\n"

        black_config = BlackConfig()
        usort_config = UsortConfig()

        result = ufmt.ufmt_bytes(
            Path("foo.py"),
            CORRECTLY_FORMATTED_CODE.encode(),
            black_config=black_config,
            usort_config=usort_config,
            pre_processor=pre_processor,
        )

        self.assertEqual(
            CORRECTLY_FORMATTED_CODE.encode() + b'\n\nprint("hello")\n', result
        )

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

            with self.subTest("invalid syntax"):
                f.write_text(INVALID_SYNTAX)

                result = ufmt.ufmt_file(f)
                self.assertIsInstance(result.error, ParserSyntaxError)

            with self.subTest("file not found"):
                f.unlink()

                result = ufmt.ufmt_file(f)
                self.assertIsInstance(result.error, FileNotFoundError)

            with self.subTest("write failed"):
                with patch("ufmt.core.write_file") as write_mock:
                    write_mock.side_effect = PermissionError("fake permission error")

                    f.write_text(POORLY_FORMATTED_CODE)

                    result = ufmt.ufmt_file(f)
                    self.assertIsInstance(result.error, PermissionError)

    @patch("ufmt.core.sys.stdin")
    @patch("ufmt.core.sys.stdout")
    def test_ufmt_stdin(self, stdout_mock, stdin_mock):
        with self.subTest("check"):
            stdin_mock.buffer = stdin = io.BytesIO()
            stdout_mock.buffer = stdout = io.BytesIO()

            stdin.write(POORLY_FORMATTED_CODE.encode())
            stdin.seek(0)

            result = ufmt_stdin(STDIN, dry_run=True)
            expected = Result(path=STDIN, changed=True)
            self.assertEqual(expected, result)
            stdout.seek(0)
            self.assertEqual(b"", stdout.read())

        with self.subTest("diff"):
            stdin_mock.buffer = stdin = io.BytesIO()
            stdout_mock.buffer = stdout = io.BytesIO()

            stdin.write(POORLY_FORMATTED_CODE.encode())
            stdin.seek(0)

            result = ufmt_stdin(STDIN, dry_run=True, diff=True)
            self.assertTrue(result.diff)
            stdout.seek(0)
            self.assertEqual(b"", stdout.read())

        with self.subTest("format"):
            stdin_mock.buffer = stdin = io.BytesIO()
            stdout_mock.buffer = stdout = io.BytesIO()

            stdin.write(POORLY_FORMATTED_CODE.encode())
            stdin.seek(0)

            result = ufmt_stdin(STDIN)
            expected = Result(path=STDIN, changed=True, written=True)
            stdout.seek(0)
            self.assertEqual(CORRECTLY_FORMATTED_CODE.encode(), stdout.read())

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
                with self.subTest("no paths"):
                    results = list(ufmt.ufmt_paths([], dry_run=True))
                    self.assertEqual([], results)
                    file_wrapper.assert_not_called()

                with self.subTest("non-existent paths"):
                    results = list(
                        ufmt.ufmt_paths(
                            [(td / "fake.py"), (td / "another.py")], dry_run=True
                        )
                    )
                    self.assertEqual([], results)

                with self.subTest("mixed paths with stdin"):
                    with patch("ufmt.core.LOG") as log_mock:
                        results = list(ufmt.ufmt_paths([f1, STDIN, f3], dry_run=True))
                        self.assertEqual(2, len(results))
                        log_mock.warning.assert_called_once()

                with self.subTest("files"):
                    results = list(ufmt.ufmt_paths([f1, f3], dry_run=True))
                    self.assertEqual(2, len(results))
                    file_wrapper.assert_has_calls(
                        [
                            call(
                                f1,
                                dry_run=True,
                                diff=False,
                                return_content=False,
                                black_config_factory=None,
                                usort_config_factory=None,
                                pre_processor=None,
                                post_processor=None,
                            ),
                            call(
                                f3,
                                dry_run=True,
                                diff=False,
                                return_content=False,
                                black_config_factory=None,
                                usort_config_factory=None,
                                pre_processor=None,
                                post_processor=None,
                            ),
                        ],
                        any_order=True,
                    )
                    self.assertTrue(all(r.changed for r in results))
                    file_wrapper.reset_mock()

                with self.subTest("files with diff"):
                    results = list(ufmt.ufmt_paths([f1, f3], dry_run=True, diff=True))
                    self.assertEqual(2, len(results))
                    file_wrapper.assert_has_calls(
                        [
                            call(
                                f1,
                                dry_run=True,
                                diff=True,
                                return_content=False,
                                black_config_factory=None,
                                usort_config_factory=None,
                                pre_processor=None,
                                post_processor=None,
                            ),
                            call(
                                f3,
                                dry_run=True,
                                diff=True,
                                return_content=False,
                                black_config_factory=None,
                                usort_config_factory=None,
                                pre_processor=None,
                                post_processor=None,
                            ),
                        ],
                        any_order=True,
                    )
                    self.assertTrue(all(r.changed for r in results))
                    file_wrapper.reset_mock()

                with self.subTest("subdir"):
                    results = list(ufmt.ufmt_paths([sd]))
                    file_wrapper.assert_has_calls(
                        [
                            call(
                                f2,
                                dry_run=False,
                                diff=False,
                                return_content=False,
                                black_config_factory=None,
                                usort_config_factory=None,
                                pre_processor=None,
                                post_processor=None,
                            ),
                            call(
                                f3,
                                dry_run=False,
                                diff=False,
                                return_content=False,
                                black_config_factory=None,
                                usort_config_factory=None,
                                pre_processor=None,
                                post_processor=None,
                            ),
                        ],
                        any_order=True,
                    )
                    self.assertTrue(all(r.changed for r in results))
                    file_wrapper.reset_mock()

    @patch("ufmt.core.ufmt_stdin")
    def test_ufmt_paths_stdin(self, stdin_mock):
        stdin_mock.return_value = Result(path=STDIN, changed=True)

        with self.subTest("no name"):
            list(ufmt.ufmt_paths([STDIN], dry_run=True))
            stdin_mock.assert_called_with(
                Path("<stdin>"),
                dry_run=True,
                diff=False,
                return_content=False,
                black_config_factory=None,
                usort_config_factory=None,
                pre_processor=None,
                post_processor=None,
            )

        with self.subTest("path name"):
            list(ufmt.ufmt_paths([STDIN, Path("hello.py")], dry_run=True))
            stdin_mock.assert_called_with(
                Path("hello.py"),
                dry_run=True,
                diff=False,
                return_content=False,
                black_config_factory=None,
                usort_config_factory=None,
                pre_processor=None,
                post_processor=None,
            )

        with self.subTest("extra args"):
            with self.assertRaisesRegex(ValueError, "too many stdin paths"):
                list(
                    ufmt.ufmt_paths(
                        [STDIN, Path("hello.py"), Path("foo.py")], dry_run=True
                    )
                )

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
                list(ufmt.ufmt_paths([td]))
                file_wrapper.assert_has_calls(
                    [
                        call(
                            f2,
                            dry_run=False,
                            diff=False,
                            return_content=False,
                            black_config_factory=None,
                            usort_config_factory=None,
                            pre_processor=None,
                            post_processor=None,
                        ),
                    ],
                    any_order=True,
                )
                self.assertEqual(f1.read_text(), POORLY_FORMATTED_CODE)
                self.assertEqual(f2.read_text(), CORRECTLY_FORMATTED_CODE)
                self.assertEqual(f3.read_text(), POORLY_FORMATTED_CODE)

    def test_e2e_return_bytes(self):
        with TemporaryDirectory() as td:
            td = Path(td).resolve()
            foo = td / "foo.py"
            foo.write_text(POORLY_FORMATTED_CODE)

            results = list(ufmt.ufmt_paths([foo], return_content=True))
            expected = [
                ufmt.Result(
                    foo,
                    changed=True,
                    written=True,
                    diff=None,
                    error=None,
                    before=POORLY_FORMATTED_CODE.encode(),
                    after=CORRECTLY_FORMATTED_CODE.encode(),
                )
            ]
            self.assertEqual(expected, results)
