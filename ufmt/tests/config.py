# Copyright 2022 Amethyst Reese
# Licensed under the MIT license

from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase

from trailrunner.tests.core import cd

from ufmt.config import ufmt_config, UfmtConfig


class ConfigTest(TestCase):
    maxDiff = None

    def setUp(self):
        self._td = TemporaryDirectory()
        self.addCleanup(self._td.cleanup)

        self.td = Path(self._td.name).resolve()
        self.pyproject = self.td / "pyproject.toml"

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
