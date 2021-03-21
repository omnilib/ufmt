# Copyright 2021 John Reese
# Licensed under the MIT license

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch, call

from usort.config import Config

import ufmt

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


class CoreTest(TestCase):
    maxDiff = None

    def test_ufmt_string(self):
        config = Config()

        with self.subTest("changed"):
            result = ufmt.ufmt_string(Path("foo.py"), POORLY_FORMATTED_CODE, config)
            self.assertEqual(CORRECTLY_FORMATTED_CODE, result)

        with self.subTest("unchanged"):
            result = ufmt.ufmt_string(Path("foo.py"), CORRECTLY_FORMATTED_CODE, config)
            self.assertEqual(CORRECTLY_FORMATTED_CODE, result)

    def test_ufmt_file(self):
        with TemporaryDirectory() as td:
            td = Path(td)
            f = td / "foo.py"
            f.write_text(POORLY_FORMATTED_CODE)

            with self.subTest("dry run"):
                changed = ufmt.ufmt_file(f, dry_run=True)
                self.assertTrue(changed)
                self.assertEqual(POORLY_FORMATTED_CODE, f.read_text())

            with self.subTest("for reals"):
                changed = ufmt.ufmt_file(f)
                self.assertTrue(changed)
                self.assertEqual(CORRECTLY_FORMATTED_CODE, f.read_text())

            f.write_text(CORRECTLY_FORMATTED_CODE)

            with self.subTest("already formatted"):
                changed = ufmt.ufmt_file(f)
                self.assertFalse(changed)
                self.assertEqual(CORRECTLY_FORMATTED_CODE, f.read_text())

    @patch("ufmt.core.ufmt_file")
    def test_ufmt_paths(self, file_mock):
        file_mock.return_value = True

        with TemporaryDirectory() as td:
            td = Path(td)
            f1 = td / "bar.py"
            sd = td / "foo"
            sd.mkdir()
            f2 = sd / "baz.py"
            f3 = sd / "frob.py"

            for f in f1, f2, f3:
                f.write_text(POORLY_FORMATTED_CODE)

            with self.subTest("files"):
                changed = ufmt.ufmt_paths([f1, f3], dry_run=True)
                file_mock.assert_has_calls(
                    [
                        call(f1, dry_run=True),
                        call(f3, dry_run=True),
                    ],
                    any_order=True,
                )
                self.assertTrue(changed)
                file_mock.reset_mock()

            with self.subTest("subdir"):
                changed = ufmt.ufmt_paths([sd])
                file_mock.assert_has_calls(
                    [
                        call(f2, dry_run=False),
                        call(f3, dry_run=False),
                    ],
                    any_order=True,
                )
                self.assertTrue(changed)
                file_mock.reset_mock()
