# Copyright 2021 John Reese
# Licensed under the MIT license

import os
import platform
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipIf, TestCase
from unittest.mock import call, patch

import trailrunner
from click.testing import CliRunner
from libcst import ParserSyntaxError

from ufmt.cli import echo_results, main
from ufmt.core import Result

from .core import CORRECTLY_FORMATTED_CODE, POORLY_FORMATTED_CODE


@patch.object(trailrunner.core.Trailrunner, "DEFAULT_EXECUTOR", ThreadPoolExecutor)
class CliTest(TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.td = TemporaryDirectory()
        td = Path(self.td.name)
        f1 = td / "bar.py"
        sd = td / "foo"
        sd.mkdir()
        f2 = sd / "baz.py"
        f3 = sd / "frob.py"

        for f in f1, f2, f3:
            f.write_text("\n")

        os.chdir(td)

    def tearDown(self):
        os.chdir(self.cwd)
        self.td.cleanup()

    @patch("ufmt.cli.echo_color_precomputed_diff")
    @patch("ufmt.cli.click.echo")
    def test_echo(self, echo_mock, mol_mock):
        f1 = Path("foo/bar.py")
        f2 = Path("fuzz/buzz.py")
        f3 = Path("make/rake.py")
        results = [
            Result(f1, changed=False),
            Result(f2, changed=True, written=False, diff="fakediff1"),
            Result(f3, changed=True, written=True, diff="fakediff2"),
        ]

        with self.subTest("no diff"):
            echo_results(results)
            echo_mock.assert_has_calls(
                [
                    call(f"Would format {f2}", err=True),
                    call(f"Formatted {f3}", err=True),
                ]
            )
            mol_mock.assert_not_called()
            echo_mock.reset_mock()
            mol_mock.reset_mock()

        with self.subTest("with diff"):
            echo_results(results, diff=True)
            echo_mock.assert_has_calls(
                [
                    call(f"Would format {f2}", err=True),
                    call(f"Formatted {f3}", err=True),
                ]
            )
            mol_mock.assert_has_calls(
                [
                    call("fakediff1"),
                    call("fakediff2"),
                ]
            )
            echo_mock.reset_mock()
            mol_mock.reset_mock()

    @patch("ufmt.cli.ufmt_paths")
    def test_check(self, ufmt_mock):
        runner = CliRunner()

        with self.subTest("no paths given"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = []
            result = runner.invoke(main, ["check"])
            ufmt_mock.assert_called_with([Path(".")], dry_run=True)
            self.assertRegex(result.stdout, r"No files found")
            self.assertEqual(1, result.exit_code)

        with self.subTest("already formatted"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(Path("foo/frob.py"), changed=False),
            ]
            result = runner.invoke(main, ["check", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")], dry_run=True
            )
            self.assertEqual(0, result.exit_code)

        with self.subTest("needs formatting"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(Path("foo/frob.py"), changed=True),
            ]
            result = runner.invoke(main, ["check", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")], dry_run=True
            )
            self.assertEqual(1, result.exit_code)

        with self.subTest("syntax error"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(
                    Path("foo/frob.py"),
                    error=ParserSyntaxError(
                        "bad",
                        lines=("", "", "", "foo bar fizzbuzz hello world"),
                        raw_line=4,
                        raw_column=15,
                    ),
                ),
            ]
            result = runner.invoke(main, ["check", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")], dry_run=True
            )
            self.assertRegex(
                result.stdout, r"Error formatting .*frob\.py: Syntax Error @ 4:16"
            )
            self.assertEqual(1, result.exit_code)

    @patch("ufmt.cli.ufmt_paths")
    def test_diff(self, ufmt_mock):
        runner = CliRunner()

        with self.subTest("no paths given"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = []
            result = runner.invoke(main, ["diff"])
            ufmt_mock.assert_called_with([Path(".")], dry_run=True, diff=True)
            self.assertRegex(result.stdout, r"No files found")
            self.assertEqual(1, result.exit_code)

        with self.subTest("already formatted"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(Path("foo/frob.py"), changed=False),
            ]
            result = runner.invoke(main, ["diff", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")], dry_run=True, diff=True
            )
            self.assertEqual(0, result.exit_code)

        with self.subTest("needs formatting"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(Path("foo/frob.py"), changed=True),
            ]
            result = runner.invoke(main, ["diff", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")], dry_run=True, diff=True
            )
            self.assertEqual(1, result.exit_code)

        with self.subTest("syntax error"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(
                    Path("foo/frob.py"),
                    error=ParserSyntaxError(
                        "bad",
                        lines=("", "", "", "foo bar fizzbuzz hello world"),
                        raw_line=4,
                        raw_column=15,
                    ),
                ),
            ]
            result = runner.invoke(main, ["diff", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")], dry_run=True, diff=True
            )
            self.assertRegex(
                result.stdout, r"Error formatting .*frob\.py: Syntax Error @ 4:16"
            )
            self.assertEqual(1, result.exit_code)

    @patch("ufmt.cli.ufmt_paths")
    def test_format(self, ufmt_mock):
        runner = CliRunner()

        with self.subTest("no paths given"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = []
            result = runner.invoke(main, ["format"])
            ufmt_mock.assert_called_with([Path(".")])
            self.assertRegex(result.stdout, r"No files found")
            self.assertEqual(1, result.exit_code)

        with self.subTest("already formatted"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(Path("foo/frob.py"), changed=False),
            ]
            result = runner.invoke(main, ["format", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with([Path("bar.py"), Path("foo/frob.py")])
            self.assertEqual(0, result.exit_code)

        with self.subTest("needs formatting"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(Path("foo/frob.py"), changed=True),
            ]
            result = runner.invoke(main, ["format", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with([Path("bar.py"), Path("foo/frob.py")])
            self.assertEqual(0, result.exit_code)

        with self.subTest("syntax error"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(
                    Path("foo/frob.py"),
                    error=ParserSyntaxError(
                        "bad",
                        lines=("", "", "", "foo bar fizzbuzz hello world"),
                        raw_line=4,
                        raw_column=15,
                    ),
                ),
            ]
            result = runner.invoke(main, ["format", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with([Path("bar.py"), Path("foo/frob.py")])
            self.assertRegex(
                result.stdout, r"Error formatting .*frob\.py: Syntax Error @ 4:16"
            )
            self.assertEqual(1, result.exit_code)

    @skipIf(platform.system() == "Windows", "stderr not supported on Windows")
    def test_stdin(self) -> None:
        runner = CliRunner(mix_stderr=False)

        with self.subTest("check clean"):
            result = runner.invoke(
                main,
                ["check", "-", "hello.py"],
                input=CORRECTLY_FORMATTED_CODE,
            )
            self.assertEqual("", result.stdout)
            self.assertEqual("", result.stderr)
            self.assertEqual(0, result.exit_code)

        with self.subTest("check dirty"):
            result = runner.invoke(
                main,
                ["check", "-"],
                input=POORLY_FORMATTED_CODE,
            )
            self.assertEqual("", result.stdout)
            self.assertEqual("Would format <stdin>\n", result.stderr)
            self.assertEqual(1, result.exit_code)

        with self.subTest("diff clean"):
            result = runner.invoke(
                main,
                ["diff", "-", "hello.py"],
                input=CORRECTLY_FORMATTED_CODE,
            )
            self.assertEqual("", result.stdout)
            self.assertEqual("", result.stderr)
            self.assertEqual(0, result.exit_code)

        with self.subTest("diff dirty"):
            result = runner.invoke(
                main,
                ["diff", "-", "hello.py"],
                input=POORLY_FORMATTED_CODE,
            )
            self.assertRegex(result.stdout, r"---.*\n\+\+\+")
            self.assertEqual("Would format hello.py\n", result.stderr)
            self.assertEqual(1, result.exit_code)

        with self.subTest("format clean"):
            result = runner.invoke(
                main,
                ["format", "-", "hello.py"],
                input=CORRECTLY_FORMATTED_CODE,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE, result.stdout)
            self.assertEqual("", result.stderr)
            self.assertEqual(0, result.exit_code)

        with self.subTest("format dirty"):
            result = runner.invoke(
                main,
                ["format", "-", "hello.py"],
                input=POORLY_FORMATTED_CODE,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE, result.stdout)
            self.assertEqual("Formatted hello.py\n", result.stderr)
            self.assertEqual(0, result.exit_code)
