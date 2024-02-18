# Copyright 2022 Amethyst Reese
# Licensed under the MIT license

from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase
from unittest.mock import ANY, patch

from trailrunner.tests.core import cd

from ufmt.config import ufmt_config, UfmtConfig


class ConfigTest(TestCase):
    maxDiff = None

    def setUp(self):
        self._td = TemporaryDirectory()
        self.addCleanup(self._td.cleanup)

        self.td = Path(self._td.name).resolve()
        self.pyproject = self.td / "pyproject.toml"

    def subTest(self, *args, **kwargs):
        ufmt_config.cache_clear()
        return super().subTest(*args, **kwargs)

    def test_ufmt_config(self):
        fake_config = dedent(
            """
            [tool.ufmt]
            excludes = [
                "a",
                "b",
            ]
            """
        )

        foo = self.td / "foo"
        foo.mkdir()
        bar = foo / "bar.py"
        bar.write_text("print('hello world')\n")

        with self.subTest("absolute path, no pyproject.toml"):
            config = ufmt_config(bar)
            self.assertEqual(UfmtConfig(), config)

        with self.subTest("local path, no pyproject.toml"):
            with cd(foo):
                config = ufmt_config()
                self.assertEqual(UfmtConfig(), config)

        self.pyproject.write_text("")

        with self.subTest("absolute path, empty pyproject.toml"):
            config = ufmt_config(bar)
            self.assertEqual(
                UfmtConfig(
                    project_root=self.td, pyproject_path=self.pyproject, excludes=[]
                ),
                config,
            )

        with self.subTest("local path, empty pyproject.toml"):
            with cd(self.td):
                config = ufmt_config()
                self.assertEqual(
                    UfmtConfig(
                        project_root=self.td,
                        pyproject_path=self.pyproject,
                        excludes=[],
                    ),
                    config,
                )

        self.pyproject.write_text(fake_config)

        with self.subTest("absolute path, with pyproject.toml"):
            config = ufmt_config(bar)
            self.assertEqual(
                UfmtConfig(
                    project_root=self.td,
                    pyproject_path=self.pyproject,
                    excludes=["a", "b"],
                ),
                config,
            )

        with self.subTest("local path, with pyproject.toml"):
            with cd(self.td):
                config = ufmt_config()
                self.assertEqual(
                    UfmtConfig(
                        project_root=self.td,
                        pyproject_path=self.pyproject,
                        excludes=["a", "b"],
                    ),
                    config,
                )

        with self.subTest("absolute path, manually specify project root"):
            config = ufmt_config(root=self.td)
            self.assertEqual(
                UfmtConfig(
                    project_root=self.td,
                    pyproject_path=self.pyproject,
                    excludes=["a", "b"],
                ),
                config,
            )

    @patch("ufmt.config.LOG")
    def test_invalid_config(self, log_mock):
        with self.subTest("string"):
            self.pyproject.write_text(
                dedent(
                    """
                    [tool]
                    ufmt = "hello"
                    """
                )
            )
            expected = UfmtConfig(project_root=self.td, pyproject_path=self.pyproject)
            result = ufmt_config(self.td / "fake.py")
            self.assertEqual(expected, result)

            log_mock.warning.assert_called_once()
            log_mock.reset_mock()

        with self.subTest("array"):
            self.pyproject.write_text(
                dedent(
                    """
                    [[tool.ufmt]]
                    excludes = ["fixtures/"]
                    """
                )
            )
            expected = UfmtConfig(project_root=self.td, pyproject_path=self.pyproject)
            result = ufmt_config(self.td / "fake.py")
            self.assertEqual(expected, result)

            log_mock.warning.assert_called_once()
            log_mock.reset_mock()

        with self.subTest("extra"):
            self.pyproject.write_text(
                dedent(
                    """
                    [tool.ufmt]
                    unknown_element = true
                    hello_world = "my name is"
                    """
                )
            )
            expected = UfmtConfig(project_root=self.td, pyproject_path=self.pyproject)
            result = ufmt_config(self.td / "fake.py")
            self.assertEqual(expected, result)

            log_mock.warning.assert_called_with(
                ANY, self.pyproject, ["hello_world", "unknown_element"]
            )
            log_mock.reset_mock()

        with self.subTest("unsupported formatter"):
            self.pyproject.write_text(
                dedent(
                    """
                    [tool.ufmt]
                    formatter = "garbage"
                    """
                )
            )
            with self.assertRaisesRegex(
                ValueError, "'garbage' is not a valid Formatter"
            ):
                ufmt_config(self.td / "fake.py")

    @patch("ufmt.config.LOG")
    def test_config_excludes(self, log_mock):
        with self.subTest("missing"):
            self.pyproject.write_text(
                dedent(
                    """
                    [tool.ufmt]
                    """
                )
            )
            expected = UfmtConfig(project_root=self.td, pyproject_path=self.pyproject)
            result = ufmt_config(self.td / "fake.py")
            self.assertEqual(expected, result)
            log_mock.assert_not_called()

        with self.subTest("empty"):
            self.pyproject.write_text(
                dedent(
                    """
                    [tool.ufmt]
                    excludes = []
                    """
                )
            )
            expected = UfmtConfig(
                project_root=self.td, pyproject_path=self.pyproject, excludes=[]
            )
            result = ufmt_config(self.td / "fake.py")
            self.assertEqual(expected, result)
            log_mock.assert_not_called()

        with self.subTest("list"):
            self.pyproject.write_text(
                dedent(
                    """
                    [tool.ufmt]
                    excludes = ["fixtures/"]
                    """
                )
            )
            expected = UfmtConfig(
                project_root=self.td,
                pyproject_path=self.pyproject,
                excludes=["fixtures/"],
            )
            result = ufmt_config(self.td / "fake.py")
            self.assertEqual(expected, result)
            log_mock.assert_not_called()

        with self.subTest("string"):
            self.pyproject.write_text(
                dedent(
                    """
                    [tool.ufmt]
                    excludes = "fixtures/"
                    """
                )
            )
            with self.assertRaisesRegex(
                ValueError, "excludes must be a list of strings"
            ):
                ufmt_config(self.td / "fake.py")
