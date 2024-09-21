# Copyright 2022 Amethyst Reese
# Licensed under the MIT license

import io
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import ANY, call, Mock, patch

import black
import ruff_api
import trailrunner
import usort
from libcst import ParserSyntaxError

import ufmt
from ufmt.core import ufmt_stdin
from ufmt.types import (
    BlackConfig,
    Encoding,
    FileContent,
    Formatter,
    Result,
    SkipFormatting,
    Sorter,
    STDIN,
    UfmtConfig,
    UsortConfig,
)

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

    @patch("ufmt.core.black.format_file_contents", wraps=black.format_file_contents)
    @patch("ufmt.core.ruff_api.format_string", wraps=ruff_api.format_string)
    def test_ufmt_bytes(self, ruff_mock: Mock, black_mock: Mock) -> None:
        black_config = BlackConfig()
        usort_config = UsortConfig()

        with self.subTest("changed"):
            black_mock.reset_mock()
            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                POORLY_FORMATTED_CODE.encode(),
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE.encode(), result)
            black_mock.assert_called_once()
            ruff_mock.assert_not_called()

        with self.subTest("unchanged"):
            black_mock.reset_mock()
            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                CORRECTLY_FORMATTED_CODE.encode(),
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE.encode(), result)
            black_mock.assert_called_once()
            ruff_mock.assert_not_called()

        with self.subTest("type stub"):
            black_mock.reset_mock()
            result = ufmt.ufmt_bytes(
                Path("foo.pyi"),
                POORLY_FORMATTED_STUB.encode(),
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_STUB.encode(), result)
            black_mock.assert_called_once()
            ruff_mock.assert_not_called()

    @patch("ufmt.core.black.format_file_contents", wraps=black.format_file_contents)
    @patch("ufmt.core.ruff_api.format_string", wraps=ruff_api.format_string)
    def test_ufmt_bytes_alternate_formatter(
        self, ruff_mock: Mock, black_mock: Mock
    ) -> None:
        black_config = BlackConfig()
        usort_config = UsortConfig()

        with self.subTest("changed"):
            ruff_mock.reset_mock()
            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                POORLY_FORMATTED_CODE.encode(),
                ufmt_config=UfmtConfig(formatter=Formatter.ruff_api),
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE.encode(), result)
            ruff_mock.assert_called_once()
            black_mock.assert_not_called()

        with self.subTest("unchanged"):
            ruff_mock.reset_mock()
            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                CORRECTLY_FORMATTED_CODE.encode(),
                ufmt_config=UfmtConfig(formatter=Formatter.ruff_api),
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE.encode(), result)
            ruff_mock.assert_called_once()
            black_mock.assert_not_called()

        with self.subTest("type stub"):
            ruff_mock.reset_mock()
            result = ufmt.ufmt_bytes(
                Path("foo.pyi"),
                POORLY_FORMATTED_STUB.encode(),
                ufmt_config=UfmtConfig(formatter=Formatter.ruff_api),
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_STUB.encode(), result)
            ruff_mock.assert_called_once()
            black_mock.assert_not_called()

        with self.subTest("unsupported formatter"):
            with self.assertRaisesRegex(
                ValueError, "'garbage' is not a supported formatter"
            ):
                ufmt.ufmt_bytes(
                    Path("foo.pyi"),
                    POORLY_FORMATTED_STUB.encode(),
                    ufmt_config=UfmtConfig(formatter="garbage"),  # type:ignore
                    black_config=black_config,
                    usort_config=usort_config,
                )
            ruff_mock.assert_called_once()
            black_mock.assert_not_called()

    @patch("ufmt.core.usort", wraps=usort.usort)
    @patch("ufmt.core.ruff_api.isort_string", wraps=ruff_api.isort_string)
    def test_ufmt_bytes_alternate_sorter(
        self, ruff_mock: Mock, usort_mock: Mock
    ) -> None:
        black_config = BlackConfig()
        usort_config = UsortConfig()

        with self.subTest("default"):
            usort_mock.reset_mock()
            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                POORLY_FORMATTED_CODE.encode(),
                ufmt_config=UfmtConfig(),
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE.encode(), result)
            usort_mock.assert_called_once()

        with self.subTest("usort"):
            usort_mock.reset_mock()
            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                POORLY_FORMATTED_CODE.encode(),
                ufmt_config=UfmtConfig(),
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE.encode(), result)
            usort_mock.assert_called_with(
                POORLY_FORMATTED_CODE.encode(), usort_config, Path("foo.py")
            )
            ruff_mock.assert_not_called()

            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                CORRECTLY_FORMATTED_CODE.encode(),
                ufmt_config=UfmtConfig(sorter=Sorter.skip),
                black_config=black_config,
                usort_config=usort_config,
            )
            expected = CORRECTLY_FORMATTED_CODE
            self.assertEqual(expected.encode(), result)

        with self.subTest("ruff-api"):
            usort_mock.reset_mock()
            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                POORLY_FORMATTED_CODE.encode(),
                ufmt_config=UfmtConfig(sorter=Sorter.ruff_api),
                black_config=black_config,
                usort_config=usort_config,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE.encode(), result)
            usort_mock.assert_not_called()
            ruff_mock.assert_called_with(
                "foo.py", POORLY_FORMATTED_CODE, options=ANY, root=None
            )

            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                CORRECTLY_FORMATTED_CODE.encode(),
                ufmt_config=UfmtConfig(sorter=Sorter.skip),
                black_config=black_config,
                usort_config=usort_config,
            )
            expected = CORRECTLY_FORMATTED_CODE
            self.assertEqual(expected.encode(), result)

        with self.subTest("skip"):
            usort_mock.reset_mock()
            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                POORLY_FORMATTED_CODE.encode(),
                ufmt_config=UfmtConfig(sorter=Sorter.skip),
                black_config=black_config,
                usort_config=usort_config,
            )
            expected = POORLY_FORMATTED_CODE[:64] + CORRECTLY_FORMATTED_CODE[65:]
            self.assertEqual(expected.encode(), result)
            usort_mock.assert_not_called()

            result = ufmt.ufmt_bytes(
                Path("foo.py"),
                CORRECTLY_FORMATTED_CODE.encode(),
                ufmt_config=UfmtConfig(sorter=Sorter.skip),
                black_config=black_config,
                usort_config=usort_config,
            )
            expected = CORRECTLY_FORMATTED_CODE
            self.assertEqual(expected.encode(), result)

        with self.subTest("unsupported sorter"):
            with self.assertRaisesRegex(
                ValueError, "'garbage' is not a supported sorter"
            ):
                ufmt.ufmt_bytes(
                    Path("foo.py"),
                    POORLY_FORMATTED_CODE.encode(),
                    ufmt_config=UfmtConfig(sorter="garbage"),  # type:ignore
                    black_config=black_config,
                    usort_config=usort_config,
                )
            usort_mock.assert_not_called()

    def test_ufmt_bytes_pre_processor(self) -> None:
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

    def test_ufmt_bytes_post_processor(self) -> None:
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

    def test_ufmt_string(self) -> None:
        black_config = BlackConfig()
        usort_config = UsortConfig()

        warnings.simplefilter("ignore", DeprecationWarning)

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

        warnings.resetwarnings()

        with self.subTest("version check"):
            self.assertRegex(ufmt.__version__, r"^2\.", "remove ufmt_string in 3.0")

    def test_ufmt_file(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            f = tdp / "foo.py"
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

            with self.subTest("skipped file no reason"):

                def skip_no_reason(
                    path: Path, content: FileContent, *, encoding: Encoding = "utf-8"
                ) -> FileContent:
                    raise SkipFormatting

                f.write_text(POORLY_FORMATTED_CODE)

                result = ufmt.ufmt_file(f, pre_processor=skip_no_reason)
                self.assertTrue(result.skipped)
                self.assertIs(result.skipped, True)
                self.assertEqual(POORLY_FORMATTED_CODE, f.read_text())

            with self.subTest("skipped file no reason"):

                def skip_with_reason(
                    path: Path, content: FileContent, *, encoding: Encoding = "utf-8"
                ) -> FileContent:
                    raise SkipFormatting("because I said so")

                f.write_text(POORLY_FORMATTED_CODE)

                result = ufmt.ufmt_file(f, pre_processor=skip_with_reason)
                self.assertTrue(result.skipped)
                self.assertEqual(result.skipped, "because I said so")
                self.assertEqual(POORLY_FORMATTED_CODE, f.read_text())

    @patch("ufmt.core.sys.stdin")
    @patch("ufmt.core.sys.stdout")
    def test_ufmt_stdin(self, stdout_mock: Mock, stdin_mock: Mock) -> None:
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

        with self.subTest("diff with path"):
            stdin_mock.buffer = stdin = io.BytesIO()
            stdout_mock.buffer = stdout = io.BytesIO()

            stdin.write(POORLY_FORMATTED_CODE.encode())
            stdin.seek(0)

            path = Path("hello/world.py")
            result = ufmt_stdin(path, dry_run=True, diff=True)
            self.assertIsNotNone(result.diff)
            self.assertRegex(
                result.diff or "", r"--- hello.world\.py\n\+\+\+ hello.world\.py"
            )
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

    def test_ufmt_paths(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            f1 = tdp / "bar.py"
            sd = tdp / "foo"
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
                            [(tdp / "fake.py"), (tdp / "another.py")], dry_run=True
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
                                ufmt_config_factory=None,
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
                                ufmt_config_factory=None,
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
                                ufmt_config_factory=None,
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
                                ufmt_config_factory=None,
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
                                ufmt_config_factory=None,
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
                                ufmt_config_factory=None,
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
    def test_ufmt_paths_stdin(self, stdin_mock: Mock) -> None:
        stdin_mock.return_value = Result(path=STDIN, changed=True)

        with self.subTest("no name"):
            list(ufmt.ufmt_paths([STDIN], dry_run=True))
            stdin_mock.assert_called_with(
                Path("stdin"),
                dry_run=True,
                diff=False,
                return_content=False,
                ufmt_config_factory=None,
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
                ufmt_config_factory=None,
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

    @patch("ufmt.core.sys.stdin")
    @patch("ufmt.core.sys.stdout")
    def test_ufmt_paths_stdin_resolves(
        self, stdout_mock: Mock, stdin_mock: Mock
    ) -> None:
        stdin_mock.buffer = io.BytesIO(POORLY_FORMATTED_CODE.encode())
        stdout_mock.buffer = stdout = io.BytesIO()

        def fake_preprocessor(
            path: Path, content: FileContent, encoding: Encoding
        ) -> FileContent:
            # ensure the fake path resolves correctly (#94)
            path.resolve()
            return content

        result = list(ufmt.ufmt_paths([STDIN]))
        expected = [Result(Path("stdin"), changed=True, written=True)]
        stdout.seek(0)
        output = stdout.read()

        self.assertListEqual(expected, result)
        self.assertEqual(CORRECTLY_FORMATTED_CODE.encode(), output)

    def test_ufmt_paths_config(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            md = tdp / "foo"
            md.mkdir()
            f1 = md / "__init__.py"
            f2 = md / "foo.py"
            sd = md / "frob/"
            sd.mkdir()
            f3 = sd / "main.py"

            for f in f1, f2, f3:
                f.write_text(POORLY_FORMATTED_CODE)

            pyproj = tdp / "pyproject.toml"
            pyproj.write_text(FAKE_CONFIG)

            file_wrapper = Mock(name="ufmt_file", wraps=ufmt.ufmt_file)
            with patch("ufmt.core.ufmt_file", file_wrapper):
                list(ufmt.ufmt_paths([tdp]))
                file_wrapper.assert_has_calls(
                    [
                        call(
                            f2,
                            dry_run=False,
                            diff=False,
                            return_content=False,
                            ufmt_config_factory=None,
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

    def test_e2e_empty_files(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            foo = tdp / "foo.py"
            foo.write_text("")

            results = list(ufmt.ufmt_paths([foo], return_content=True))
            expected = [
                ufmt.Result(
                    foo,
                    changed=False,
                    error=None,
                    before=b"",
                    after=b"",
                )
            ]
            self.assertListEqual(expected, results)

    def test_e2e_return_bytes(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            foo = tdp / "foo.py"

            with self.subTest("unix newlines"):
                foo.write_bytes(POORLY_FORMATTED_CODE.encode())

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

            with self.subTest("crlf newlines"):
                before = POORLY_FORMATTED_CODE.replace("\n", "\r\n").encode()
                after = CORRECTLY_FORMATTED_CODE.replace("\n", "\r\n").encode()

                foo.write_bytes(before)

                results = list(ufmt.ufmt_paths([foo], return_content=True))
                expected = [
                    ufmt.Result(
                        foo,
                        changed=True,
                        written=True,
                        diff=None,
                        error=None,
                        before=before,
                        after=after,
                    )
                ]
                self.assertEqual(expected, results)
