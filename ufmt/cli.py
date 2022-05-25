# Copyright 2021 John Reese
# Licensed under the MIT license

import logging
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

import click
from moreorless.click import echo_color_precomputed_diff

from .__version__ import __version__
from .core import Result, ufmt_paths


def init_logging(*, debug: bool = False) -> None:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG if debug else logging.INFO,
        format="%(message)s" if not debug else "%(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("blib2to3").setLevel(logging.WARNING)


def echo_results(results: Iterable[Result], diff: bool = False) -> Tuple[bool, bool]:
    empty = True
    error = False
    changed = False

    for result in results:
        empty = False

        if result.error is not None:
            msg = str(result.error)
            lines = msg.splitlines()
            msg = lines[0]
            click.secho(f"Error formatting {result.path}: {msg}", fg="yellow", err=True)
            error = True

        if result.changed:
            changed = True
            if result.written:
                click.echo(f"Formatted {result.path}", err=True)
            else:
                click.echo(f"Would format {result.path}", err=True)
            if diff and result.diff:
                echo_color_precomputed_diff(result.diff)

    if empty:
        click.secho("No files found", fg="yellow", err=True)
        error = True

    return changed, error


@click.group()
@click.version_option(__version__, "--version", "-V")
@click.option("--debug", "-d", "-v", is_flag=True, help="Enable debug/verbose output")
def main(debug: bool):
    init_logging(debug=debug)


@main.command()
@click.pass_context
@click.argument(
    "names", type=click.Path(allow_dash=True), nargs=-1, metavar="[PATH] ..."
)
def check(ctx: click.Context, names: List[str]):
    """Check formatting of one or more paths"""
    paths = [Path(name) for name in names] if names else [Path(".")]
    results = ufmt_paths(paths, dry_run=True)
    changed, error = echo_results(results)
    if changed or error:
        ctx.exit(1)


@main.command()
@click.pass_context
@click.argument(
    "names", type=click.Path(allow_dash=True), nargs=-1, metavar="[PATH] ..."
)
def diff(ctx: click.Context, names: List[str]):
    """Generate diffs for any files that need formatting"""
    paths = [Path(name) for name in names] if names else [Path(".")]
    results = ufmt_paths(paths, dry_run=True, diff=True)
    changed, error = echo_results(results, diff=True)
    if changed or error:
        ctx.exit(1)


@main.command()
@click.pass_context
@click.argument(
    "names", type=click.Path(allow_dash=True), nargs=-1, metavar="[PATH] ..."
)
def format(ctx: click.Context, names: List[str]):
    """Format one or more paths in place"""
    paths = [Path(name) for name in names] if names else [Path(".")]
    results = ufmt_paths(paths)
    _, error = echo_results(results)
    if error:
        ctx.exit(1)
