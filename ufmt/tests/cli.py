# Copyright 2022 Amethyst Reese
# Licensed under the MIT license

import os
import platform
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipIf, TestCase
from unittest.mock import call, Mock, patch

import trailrunner
from click.testing import CliRunner
from libcst import ParserSyntaxError

from ufmt.cli import echo_results, main
from ufmt.types import Result

from .core import CORRECTLY_FORMATTED_CODE, POORLY_FORMATTED_CODE


@patch.object(trailrunner.core.Trailrunner, "DEFAULT_EXECUTOR", ThreadPoolExecutor)
class CliTest(TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner(mix_stderr=False)
        self.cwd = os.getcwd()
        self.td = TemporaryDirectory()
        self.tdp = Path(self.td.name).resolve()
        os.chdir(self.tdp)

    def tearDown(self) -> None:
        os.chdir(self.cwd)
        self.td.cleanup()

    @patch("ufmt.cli.echo_color_precomputed_diff")
    @patch("ufmt.cli.click.secho")
    def test_echo(self, echo_mock: Mock, mol_mock: Mock) -> None:
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

        with self.subTest("upstream exception"):
            results = [
                Result(f1, changed=False),
                Result(f2, error=AssertionError()),
                Result(f3, error=Exception("something weird happened")),
            ]
            echo_results(results)

            echo_mock.assert_has_calls(
                [
                    call(
                        f"Error formatting {f2}: AssertionError()",
                        fg="yellow",
                        err=True,
                    ),
                    call(
                        f"Error formatting {f3}: something weird happened",
                        fg="yellow",
                        err=True,
                    ),
                ]
            )
            mol_mock.assert_not_called()
            echo_mock.reset_mock()
            mol_mock.reset_mock()

    @patch("ufmt.cli.ufmt_paths")
    def test_check(self, ufmt_mock: Mock) -> None:
        with self.subTest("no paths given"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = []
            result = self.runner.invoke(main, ["check"])
            ufmt_mock.assert_called_with(
                [Path(".")], dry_run=True, concurrency=None, root=None
            )
            self.assertRegex(result.stderr, r"No files found")
            self.assertEqual(0, result.exit_code)

        with self.subTest("already formatted"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(Path("foo/frob.py"), changed=False),
            ]
            result = self.runner.invoke(main, ["check", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")],
                dry_run=True,
                concurrency=None,
                root=None,
            )
            self.assertEqual(0, result.exit_code)

        with self.subTest("needs formatting"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(Path("foo/frob.py"), changed=True),
            ]
            result = self.runner.invoke(main, ["check", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")],
                dry_run=True,
                concurrency=None,
                root=None,
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
            result = self.runner.invoke(main, ["check", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")],
                dry_run=True,
                concurrency=None,
                root=None,
            )
            self.assertRegex(
                result.stderr, r"Error formatting .*frob\.py: Syntax Error @ 4:16"
            )
            self.assertEqual(1, result.exit_code)

        with self.subTest("skipped file"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("foo.py"), skipped="special"),
            ]
            result = self.runner.invoke(main, ["check", "foo.py"])
            ufmt_mock.assert_called_with(
                [Path("foo.py")], dry_run=True, concurrency=None, root=None
            )
            self.assertRegex(result.stderr, r"Skipped .*foo\.py: special")
            self.assertEqual(0, result.exit_code)

    @patch("ufmt.cli.ufmt_paths")
    def test_diff(self, ufmt_mock: Mock) -> None:
        with self.subTest("no paths given"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = []
            result = self.runner.invoke(main, ["diff"])
            ufmt_mock.assert_called_with(
                [Path(".")], dry_run=True, diff=True, concurrency=None, root=None
            )
            self.assertRegex(result.stderr, r"No files found")
            self.assertEqual(0, result.exit_code)

        with self.subTest("already formatted"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(Path("foo/frob.py"), changed=False),
            ]
            result = self.runner.invoke(main, ["diff", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")],
                dry_run=True,
                diff=True,
                concurrency=None,
                root=None,
            )
            self.assertEqual(0, result.exit_code)

        with self.subTest("needs formatting"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(Path("foo/frob.py"), changed=True),
            ]
            result = self.runner.invoke(main, ["diff", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")],
                dry_run=True,
                diff=True,
                concurrency=None,
                root=None,
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
            result = self.runner.invoke(main, ["diff", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")],
                dry_run=True,
                diff=True,
                concurrency=None,
                root=None,
            )
            self.assertRegex(
                result.stderr, r"Error formatting .*frob\.py: Syntax Error @ 4:16"
            )
            self.assertEqual(1, result.exit_code)

        with self.subTest("skipped file"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("foo.py"), skipped="special"),
            ]
            result = self.runner.invoke(main, ["diff", "foo.py"])
            ufmt_mock.assert_called_with(
                [Path("foo.py")], dry_run=True, diff=True, concurrency=None, root=None
            )
            self.assertRegex(result.stderr, r"Skipped .*foo\.py: special")
            self.assertEqual(0, result.exit_code)

        with self.subTest("skipped file quiet"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("foo.py"), skipped="special"),
            ]
            result = self.runner.invoke(main, ["--quiet", "diff", "foo.py"])
            ufmt_mock.assert_called_with(
                [Path("foo.py")], dry_run=True, diff=True, concurrency=None, root=None
            )
            self.assertEqual("", result.stderr)
            self.assertEqual(0, result.exit_code)

        with self.subTest("bad root dir"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
            ]
            result = self.runner.invoke(
                main, ["--root", "DOES_NOT_EXIST", "diff", "bar.py"]
            )
            self.assertIn(
                r"Directory 'DOES_NOT_EXIST' does not exist",
                result.stderr,
            )
            self.assertEqual(2, result.exit_code)

    @patch("ufmt.cli.ufmt_paths")
    def test_format(self, ufmt_mock: Mock) -> None:
        with self.subTest("no paths given"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = []
            result = self.runner.invoke(main, ["format"])
            ufmt_mock.assert_called_with([Path(".")], concurrency=None, root=None)
            self.assertRegex(result.stderr, r"No files found")
            self.assertEqual(0, result.exit_code)

        with self.subTest("already formatted"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(Path("foo/frob.py"), changed=False),
            ]
            result = self.runner.invoke(main, ["format", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")], concurrency=None, root=None
            )
            self.assertEqual(0, result.exit_code)

        with self.subTest("needs formatting"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("bar.py"), changed=False),
                Result(Path("foo/frob.py"), changed=True),
            ]
            result = self.runner.invoke(main, ["format", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")], concurrency=None, root=None
            )
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
            result = self.runner.invoke(main, ["format", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")], concurrency=None, root=None
            )
            self.assertRegex(
                result.stderr, r"Error formatting .*frob\.py: Syntax Error @ 4:16"
            )
            self.assertRegex(result.stderr, " 1 error, 1 file already formatted")
            self.assertEqual(1, result.exit_code)

        with self.subTest("skipped file"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = [
                Result(Path("foo.py"), skipped="special"),
            ]
            result = self.runner.invoke(main, ["format", "foo.py"])
            ufmt_mock.assert_called_with([Path("foo.py")], concurrency=None, root=None)
            self.assertRegex(result.stderr, r"Skipped .*foo\.py: special")
            self.assertEqual(0, result.exit_code)

    @skipIf(platform.system() == "Windows", "stderr not supported on Windows")
    def test_stdin(self) -> None:
        with self.subTest("check clean"):
            result = self.runner.invoke(
                main,
                ["check", "-", "hello.py"],
                input=CORRECTLY_FORMATTED_CODE,
            )
            self.assertEqual("", result.stdout)
            self.assertRegex(result.stderr, r"✨ 1 file already formatted ✨")
            self.assertEqual(0, result.exit_code)

        with self.subTest("check dirty"):
            result = self.runner.invoke(
                main,
                ["check", "-"],
                input=POORLY_FORMATTED_CODE,
            )
            self.assertEqual("", result.stdout)
            self.assertIn("Would format stdin\n", result.stderr)
            self.assertEqual(1, result.exit_code)

        with self.subTest("diff clean"):
            result = self.runner.invoke(
                main,
                ["diff", "-", "hello.py"],
                input=CORRECTLY_FORMATTED_CODE,
            )
            self.assertEqual("", result.stdout)
            self.assertIn("✨ 1 file already formatted ✨", result.stderr)
            self.assertEqual(0, result.exit_code)

        with self.subTest("diff dirty"):
            result = self.runner.invoke(
                main,
                ["diff", "-", "hello.py"],
                input=POORLY_FORMATTED_CODE,
            )
            self.assertRegex(result.stdout, r"--- hello.py\n\+\+\+ hello.py")
            self.assertIn("Would format hello.py\n", result.stderr)
            self.assertEqual(1, result.exit_code)

        with self.subTest("format clean"):
            result = self.runner.invoke(
                main,
                ["format", "-", "hello.py"],
                input=CORRECTLY_FORMATTED_CODE,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE, result.stdout)
            self.assertIn("✨ 1 file already formatted ✨", result.stderr)
            self.assertEqual(0, result.exit_code)

        with self.subTest("format dirty"):
            result = self.runner.invoke(
                main,
                ["format", "-", "hello.py"],
                input=POORLY_FORMATTED_CODE,
            )
            self.assertEqual(CORRECTLY_FORMATTED_CODE, result.stdout)
            self.assertIn("Formatted hello.py\n", result.stderr)
            self.assertEqual(0, result.exit_code)

    def test_end_to_end(self) -> None:
        alpha = self.tdp / "alpha.py"
        beta = self.tdp / "beta.py"
        (self.tdp / "sub").mkdir()
        gamma = self.tdp / "sub" / "gamma.py"
        kappa = self.tdp / "sub" / "kappa.py"

        def reset() -> None:
            alpha.write_text(CORRECTLY_FORMATTED_CODE)
            beta.write_text(POORLY_FORMATTED_CODE)
            gamma.write_text(CORRECTLY_FORMATTED_CODE)
            kappa.write_text(POORLY_FORMATTED_CODE)

        with self.subTest("check"):
            reset()
            result = self.runner.invoke(main, ["check", self.tdp.as_posix()])
            self.assertEqual("", result.stdout)
            self.assertIn(f"Would format {beta}", result.stderr)
            self.assertIn(f"Would format {kappa}", result.stderr)
            self.assertIn(
                "2 files would be formatted, 2 files already formatted", result.stderr
            )
            self.assertEqual(POORLY_FORMATTED_CODE, beta.read_text())
            self.assertEqual(POORLY_FORMATTED_CODE, kappa.read_text())

        with self.subTest("diff"):
            reset()
            result = self.runner.invoke(main, ["diff", self.tdp.as_posix()])
            self.assertIn(f"--- {beta.as_posix()}", result.stdout)
            self.assertIn(f"+++ {beta.as_posix()}", result.stdout)
            self.assertIn(f"Would format {beta}", result.stderr)
            self.assertIn(f"--- {kappa.as_posix()}", result.stdout)
            self.assertIn(f"+++ {kappa.as_posix()}", result.stdout)
            self.assertIn(f"Would format {kappa}", result.stderr)
            self.assertIn(
                "2 files would be formatted, 2 files already formatted", result.stderr
            )
            self.assertEqual(POORLY_FORMATTED_CODE, beta.read_text())
            self.assertEqual(POORLY_FORMATTED_CODE, kappa.read_text())

        with self.subTest("format"):
            reset()
            result = self.runner.invoke(main, ["format", self.tdp.as_posix()])
            self.assertEqual("", result.stdout)
            self.assertIn(f"Formatted {beta}", result.stderr)
            self.assertIn(f"Formatted {kappa}", result.stderr)
            self.assertIn("2 files formatted, 2 files already formatted", result.stderr)
            self.assertEqual(CORRECTLY_FORMATTED_CODE, beta.read_text())
            self.assertEqual(CORRECTLY_FORMATTED_CODE, kappa.read_text())

        with self.subTest("format quiet"):
            reset()
            result = self.runner.invoke(
                main, ["--quiet", "format", self.tdp.as_posix()]
            )
            self.assertEqual("", result.stdout)
            self.assertEqual("", result.stderr)
            self.assertEqual(CORRECTLY_FORMATTED_CODE, beta.read_text())
            self.assertEqual(CORRECTLY_FORMATTED_CODE, kappa.read_text())

        with self.subTest("format subdir"):
            reset()
            result = self.runner.invoke(main, ["format", (self.tdp / "sub").as_posix()])
            self.assertEqual("", result.stdout)
            self.assertNotIn(f"Formatted {beta}", result.stderr)
            self.assertIn(f"Formatted {kappa}", result.stderr)
            self.assertIn("1 file formatted, 1 file already formatted", result.stderr)
            self.assertEqual(POORLY_FORMATTED_CODE, beta.read_text())
            self.assertEqual(CORRECTLY_FORMATTED_CODE, kappa.read_text())

    @patch("ufmt.lsp.ufmt_lsp")  # dynamic import, patch at definition
    def test_lsp(self, lsp_mock: Mock) -> None:
        with self.subTest("default"):
            lsp_mock.reset_mock()
            self.runner.invoke(main, ["lsp"])

            lsp_mock.assert_called_with(root=None)
            lsp_mock.return_value.start_io.assert_called_with()

        with self.subTest("tcp"):
            lsp_mock.reset_mock()
            self.runner.invoke(main, ["lsp", "--tcp", "--port", "4567"])

            lsp_mock.assert_called_with(root=None)
            lsp_mock.return_value.start_tcp.assert_called_with("localhost", 4567)

        with self.subTest("ws"):
            lsp_mock.reset_mock()
            self.runner.invoke(main, ["lsp", "--ws", "--port", "8765"])

            lsp_mock.assert_called_with(root=None)
            lsp_mock.return_value.start_ws.assert_called_with("localhost", 8765)
