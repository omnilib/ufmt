# Copyright 2021 John Reese
# Licensed under the MIT license

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch, call

from click.testing import CliRunner

from ufmt.cli import main, echo_results
from ufmt.core import Result


@patch("ufmt.core.EXECUTOR", ThreadPoolExecutor)
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
                    call(f"Would format {f2}"),
                    call(f"Formatted {f3}"),
                ]
            )
            mol_mock.assert_not_called()
            echo_mock.reset_mock()
            mol_mock.reset_mock()

        with self.subTest("with diff"):
            echo_results(results, diff=True)
            echo_mock.assert_has_calls(
                [
                    call(f"Would format {f2}"),
                    call(f"Formatted {f3}"),
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

        with self.subTest("paths not exist"):
            ufmt_mock.reset_mock()
            result = runner.invoke(main, ["check", "fake.py"])
            ufmt_mock.assert_not_called()
            self.assertEqual(2, result.exit_code)
            self.assertRegex(result.output, "Path '.*' does not exist")

        with self.subTest("no paths given"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = []
            result = runner.invoke(main, ["check"])
            ufmt_mock.assert_called_with([Path(".")], dry_run=True)
            self.assertEqual(0, result.exit_code)

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

    @patch("ufmt.cli.ufmt_paths")
    def test_diff(self, ufmt_mock):
        runner = CliRunner()

        with self.subTest("paths not exist"):
            ufmt_mock.reset_mock()
            result = runner.invoke(main, ["diff", "fake.py"])
            ufmt_mock.assert_not_called()
            self.assertEqual(2, result.exit_code)
            self.assertRegex(result.output, "Path '.*' does not exist")

        with self.subTest("no paths given"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = []
            result = runner.invoke(main, ["diff"])
            ufmt_mock.assert_called_with([Path(".")], dry_run=True, diff=True)
            self.assertEqual(0, result.exit_code)

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

    @patch("ufmt.cli.ufmt_paths")
    def test_format(self, ufmt_mock):
        runner = CliRunner()

        with self.subTest("paths not exist"):
            ufmt_mock.reset_mock()
            result = runner.invoke(main, ["format", "fake.py"])
            self.assertEqual(2, result.exit_code)
            self.assertRegex(result.output, "Path '.*' does not exist")

        with self.subTest("no paths given"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = []
            result = runner.invoke(main, ["format"])
            ufmt_mock.assert_called_with([Path(".")])
            self.assertEqual(0, result.exit_code)

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
