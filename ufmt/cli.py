# Copyright 2022 Amethyst Reese
# Licensed under the MIT license

import logging
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import click
from moreorless.click import echo_color_precomputed_diff

from .__version__ import __version__
from .core import ufmt_paths
from .types import Options, Result
from .util import enable_libcst_native


def init_logging(*, debug: Optional[bool] = None) -> None:
    format = "%(message)s" if not debug else "%(levelname)s %(name)s %(message)s"
    level = (
        logging.DEBUG if debug else (logging.INFO if debug is None else logging.ERROR)
    )
    logging.basicConfig(stream=sys.stderr, level=level, format=format)
    logging.getLogger("blib2to3").setLevel(logging.WARNING)


def echo_results(
    results: Iterable[Result], diff: bool = False, quiet: bool = False
) -> Tuple[int, int]:
    empty = True
    error = 0
    changed = 0
    written = 0
    clean = 0

    for result in results:
        empty = False

        if result.error is not None:
            msg = str(result.error)
            lines = msg.splitlines()
            msg = lines[0] if lines else repr(result.error)
            click.secho(f"Error formatting {result.path}: {msg}", fg="yellow", err=True)
            error += 1

        elif result.skipped:
            reason = f": {result.skipped}" if isinstance(result.skipped, str) else ""
            if not quiet:
                click.secho(f"Skipped {result.path}{reason}", err=True)

        elif result.changed:
            if result.written:
                written += 1
                if not quiet:
                    click.secho(f"Formatted {result.path}", err=True)
            else:
                changed += 1
                click.secho(f"Would format {result.path}", err=True)
            if diff and result.diff:
                echo_color_precomputed_diff(result.diff)

        else:
            clean += 1

    if not quiet:

        def f(v: int, word: str = "file") -> str:
            return f"{v} {word if v == 1 else word + 's'}"

        reports = []
        if error:
            reports += [click.style(f(error, "error"), fg="yellow", bold=True)]
        if changed:
            reports += [click.style(f"{f(changed)} would be formatted", bold=True)]
        if written:
            reports += [click.style(f"{f(written)} formatted")]
        if clean:
            reports += [click.style(f"{f(clean)} already formatted")]

        if empty:
            click.secho("❗️ No files found ❗️", fg="yellow", err=True)
        else:
            message = ", ".join(reports)
            click.secho(f"✨ {message} ✨", err=True)

    return (changed + written), error


@click.group()
@click.pass_context
@click.version_option(__version__, "--version", "-V")
@click.option(
    "--debug/--quiet",
    "-v/-q",
    is_flag=True,
    default=None,
    help="Enable debug/verbose output",
)
@click.option(
    "--concurrency",
    type=int,
    default=None,
    help="Override the default concurrency",
)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Specify the root directory for project configuration",
)
def main(
    ctx: click.Context,
    debug: Optional[bool],
    concurrency: Optional[int],
    root: Optional[Path],
) -> None:
    init_logging(debug=debug)

    ctx.obj = Options(
        debug=debug is True,
        quiet=debug is False,
        concurrency=concurrency,
        root=root,
    )
    enable_libcst_native()


@main.command()
@click.pass_context
@click.argument(
    "names", type=click.Path(allow_dash=True), nargs=-1, metavar="[PATH] ..."
)
def check(ctx: click.Context, names: List[str]) -> None:
    """Check formatting of one or more paths"""
    options: Options = ctx.obj
    paths = [Path(name) for name in names] if names else [Path(".")]
    results = ufmt_paths(
        paths, dry_run=True, concurrency=options.concurrency, root=options.root
    )
    changed, error = echo_results(results, quiet=options.quiet)
    if changed or error:
        ctx.exit(1)


@main.command()
@click.pass_context
@click.argument(
    "names", type=click.Path(allow_dash=True), nargs=-1, metavar="[PATH] ..."
)
def diff(ctx: click.Context, names: List[str]) -> None:
    """Generate diffs for any files that need formatting"""
    options: Options = ctx.obj
    paths = [Path(name) for name in names] if names else [Path(".")]
    results = ufmt_paths(
        paths,
        dry_run=True,
        diff=True,
        concurrency=options.concurrency,
        root=options.root,
    )
    changed, error = echo_results(results, diff=True, quiet=options.quiet)
    if changed or error:
        ctx.exit(1)


@main.command()
@click.pass_context
@click.argument(
    "names", type=click.Path(allow_dash=True), nargs=-1, metavar="[PATH] ..."
)
def format(ctx: click.Context, names: List[str]) -> None:
    """Format one or more paths in place"""
    options: Options = ctx.obj
    paths = [Path(name) for name in names] if names else [Path(".")]
    results = ufmt_paths(paths, concurrency=options.concurrency, root=options.root)
    _, error = echo_results(results, quiet=options.quiet)
    if error:
        ctx.exit(1)


@main.command()
@click.pass_context
@click.option("--tcp", is_flag=True)
@click.option("--ws", is_flag=True)
@click.option("--port", type=int, default=8971)
def lsp(ctx: click.Context, tcp: bool, ws: bool, port: int) -> None:
    """Experimental: start an LSP formatting server"""
    from .lsp import ufmt_lsp

    options: Options = ctx.obj
    server = ufmt_lsp(root=options.root)

    if tcp:
        server.start_tcp("localhost", port)
    elif ws:
        server.start_ws("localhost", port)
    else:
        server.start_io()
