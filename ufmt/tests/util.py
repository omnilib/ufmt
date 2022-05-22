# Copyright 2021 John Reese, Tim Hatch
# Licensed under the MIT license

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import tomlkit
from black import TargetVersion

import ufmt
from .core import FAKE_CONFIG, POORLY_FORMATTED_CODE


class UtilTest(TestCase):
    def test_black_config(self):
        black_config = dict(
            target_version=["py36", "py37"],
            skip_string_normalization=True,
            line_length=87,
        )

        doc = tomlkit.parse(FAKE_CONFIG)
        black = tomlkit.table()
        for key, value in black_config.items():
            black[key] = value
        doc["tool"].add("black", black)

        with TemporaryDirectory() as td:
            td = Path(td)

            pyproj = td / "pyproject.toml"
            pyproj.write_text(tomlkit.dumps(doc))

            f = td / "foo.py"
            f.write_text(POORLY_FORMATTED_CODE)

            result = ufmt.ufmt_file(f, dry_run=True)
            self.assertTrue(result.changed)

            mode = ufmt.util.make_black_config(td)

            with self.subTest("target_versions"):
                self.assertEqual(
                    mode.target_versions,
                    {
                        TargetVersion[item.upper()]
                        for item in black_config["target_version"]
                    },
                )

            with self.subTest("string_normalization"):
                self.assertIs(
                    mode.string_normalization,
                    not black_config["skip_string_normalization"],
                )

            with self.subTest("line_length"):
                self.assertEqual(mode.line_length, black_config["line_length"])
