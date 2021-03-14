"""
usort + black, in that order
"""

__author__ = "John Reese"
from .__version__ import __version__

import sys
from pathlib import Path
from typing import List

import click
from black import decode_bytes, format_file_contents, Mode, NothingChanged
from usort.config import Config
from usort.sorting import usort_string
from usort.util import walk



@click.command()
@click.version_option(__version__, "--version", "-V")
@click.option("-v", "--verbose", is_flag=True, help="Show files found")
@click.option("-n", "--dry_run", is_flag=True, help="Do not write changes")
@click.argument("filenames", nargs=-1)
def main(dry_run: bool, verbose: bool, filenames: List[str]) -> None:
    """"""
    return_code = 0

    if not filenames:
        filenames = ["."]

    for f in filenames:
        path = Path(f)
        config = Config.find(path)
        mode = Mode()  # TODO

        if path.is_dir():
            # TODO use black's version of walk?
            files = walk(path, "*.py")
        else:
            files = [path]
        for src in files:
            if verbose:
                print(f"{src} found", file=sys.stderr)
            with open(src, "rb") as buf:
                src_contents, encoding, newline = decode_bytes(buf.read())

            dst_contents = usort_string(src_contents, config, src)
            try:
                dst_contents = format_file_contents(dst_contents, fast=False, mode=mode)
            except NothingChanged:
                pass

            if src_contents != dst_contents:
                if dry_run:
                    print(f"{src} would be formatted", file=sys.stderr)
                    return_code |= 1
                else:
                    with open(src, "w", encoding=encoding, newline=newline) as f:
                        f.write(dst_contents)

    sys.exit(return_code)


if __name__ == "__main__":
    main()
