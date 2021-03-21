# Copyright 2021 John Reese
# Licensed under the MIT license

import logging
import sys
from pathlib import Path
from typing import List

import click

from .__version__ import __version__
from .core import ufmt_paths


def init_logging(*, debug: bool = False) -> None:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG if debug else logging.INFO,
        format="%(message)s" if not debug else "%(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("blib2to3").setLevel(logging.WARNING)


@click.group()
@click.version_option(__version__, "--version", "-V")
@click.option("--debug", "-d", "-v", is_flag=True, help="Enable debug/verbose output")
def main(debug: bool):
    init_logging(debug=debug)


@main.command()
@click.pass_context
@click.argument("names", type=click.Path(exists=True), nargs=-1, metavar="[PATH] ...")
def check(ctx: click.Context, names: List[str]):
    """Check formatting of one or more paths"""
    paths = [Path(name) for name in names] if names else [Path(".")]
    changed = ufmt_paths(paths, dry_run=True)
    if changed:
        ctx.exit(1)


@main.command()
@click.argument("names", type=click.Path(exists=True), nargs=-1, metavar="[PATH] ...")
def format(names: List[str]):
    """Format one or more paths in place"""
    paths = [Path(name) for name in names] if names else [Path(".")]
    ufmt_paths(paths)
