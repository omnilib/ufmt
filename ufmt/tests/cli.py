# Copyright 2021 John Reese
# Licensed under the MIT license

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from click.testing import CliRunner

from ufmt.cli import main


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
            ufmt_mock.return_value = False
            result = runner.invoke(main, ["check"])
            ufmt_mock.assert_called_with([Path(".")], dry_run=True)
            self.assertEqual(0, result.exit_code)

        with self.subTest("given paths formatted"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = False
            result = runner.invoke(main, ["check", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")], dry_run=True
            )
            self.assertEqual(0, result.exit_code)

        with self.subTest("given paths unformatted"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = True
            result = runner.invoke(main, ["check", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with(
                [Path("bar.py"), Path("foo/frob.py")], dry_run=True
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
            ufmt_mock.return_value = False
            result = runner.invoke(main, ["format"])
            ufmt_mock.assert_called_with([Path(".")])
            self.assertEqual(0, result.exit_code)

        with self.subTest("given paths formatted"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = False
            result = runner.invoke(main, ["format", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with([Path("bar.py"), Path("foo/frob.py")])
            self.assertEqual(0, result.exit_code)

        with self.subTest("given paths unformatted"):
            ufmt_mock.reset_mock()
            ufmt_mock.return_value = True
            result = runner.invoke(main, ["format", "bar.py", "foo/frob.py"])
            ufmt_mock.assert_called_with([Path("bar.py"), Path("foo/frob.py")])
            self.assertEqual(0, result.exit_code)
