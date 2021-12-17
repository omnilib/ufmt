# Copyright 2021 John Reese
# Licensed under the MIT license

from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase

from trailrunner.tests.core import cd

from ufmt.config import ufmt_config, UfmtConfig


class ConfigTest(TestCase):
    maxDiff = None

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

        with TemporaryDirectory() as td:
            td = Path(td).resolve()
            foo = td / "foo"
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

            pyproj = td / "pyproject.toml"
            pyproj.write_text("")

            with self.subTest("absolute path, empty pyproject.toml"):
                config = ufmt_config(bar)
                self.assertEqual(
                    UfmtConfig(project_root=td, pyproject_path=pyproj, excludes=[]),
                    config,
                )

            with self.subTest("local path, empty pyproject.toml"):
                with cd(td):
                    config = ufmt_config()
                    self.assertEqual(
                        UfmtConfig(project_root=td, pyproject_path=pyproj, excludes=[]),
                        config,
                    )

            pyproj = td / "pyproject.toml"
            pyproj.write_text(fake_config)

            with self.subTest("absolute path, with pyproject.toml"):
                config = ufmt_config(bar)
                self.assertEqual(
                    UfmtConfig(
                        project_root=td, pyproject_path=pyproj, excludes=["a", "b"]
                    ),
                    config,
                )

            with self.subTest("local path, with pyproject.toml"):
                with cd(td):
                    config = ufmt_config()
                    self.assertEqual(
                        UfmtConfig(
                            project_root=td, pyproject_path=pyproj, excludes=["a", "b"]
                        ),
                        config,
                    )
