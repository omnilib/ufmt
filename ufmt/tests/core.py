# Copyright 2021 John Reese
# Licensed under the MIT license

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch, call, Mock

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


@patch("ufmt.core.EXECUTOR", ThreadPoolExecutor)
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

            f.write_text(CORRECTLY_FORMATTED_CODE)

            with self.subTest("already formatted"):
                result = ufmt.ufmt_file(f)
                self.assertFalse(result.changed)
                self.assertEqual(CORRECTLY_FORMATTED_CODE, f.read_text())

    def test_ufmt_paths(self):
        with TemporaryDirectory() as td:
            td = Path(td)
            f1 = td / "bar.py"
            sd = td / "foo"
            sd.mkdir()
            f2 = sd / "baz.py"
            f3 = sd / "frob.py"

            for f in f1, f2, f3:
                f.write_text(POORLY_FORMATTED_CODE)

            file_wrapper = Mock(name="ufmt_file", wraps=ufmt.ufmt_file)
            with patch("ufmt.core.ufmt_file", file_wrapper):
                with self.subTest("files"):
                    results = ufmt.ufmt_paths([f1, f3], dry_run=True)
                    self.assertEqual(2, len(results))
                    file_wrapper.assert_has_calls(
                        [
                            call(f1, dry_run=True, diff=False),
                            call(f3, dry_run=True, diff=False),
                        ],
                        any_order=True,
                    )
                    self.assertTrue(all(r.changed for r in results))
                    file_wrapper.reset_mock()

                with self.subTest("files with diff"):
                    results = ufmt.ufmt_paths([f1, f3], dry_run=True, diff=True)
                    self.assertEqual(2, len(results))
                    file_wrapper.assert_has_calls(
                        [
                            call(f1, dry_run=True, diff=True),
                            call(f3, dry_run=True, diff=True),
                        ],
                        any_order=True,
                    )
                    self.assertTrue(all(r.changed for r in results))
                    file_wrapper.reset_mock()

                with self.subTest("subdir"):
                    results = ufmt.ufmt_paths([sd])
                    file_wrapper.assert_has_calls(
                        [
                            call(f2, dry_run=False, diff=False),
                            call(f3, dry_run=False, diff=False),
                        ],
                        any_order=True,
                    )
                    self.assertTrue(all(r.changed for r in results))
                    file_wrapper.reset_mock()
