# Copyright Amethyst Reese, Tim Hatch
# Licensed under the MIT license

import time
from pathlib import Path
from typing import Any, List

from typing_extensions import Self

from ufmt import ufmt_file, ufmt_paths

ROOT = Path(__file__).parent.parent.parent


class Timer:
    def __init__(self, name: str) -> None:
        self.name = name
        self.totals: List[int] = []

    @classmethod
    def fields(self) -> str:
        headline = f"{'name':^40}  {'min':^10}  {'mean':^10}  {'max':^10}"
        underline = "-" * len(headline)
        return f"{headline}\n{underline}"

    def __str__(self) -> str:
        short = min(self.totals)
        long = max(self.totals)
        avg = sum(self.totals) // len(self.totals)
        fields = "  ".join(f"{value // 1000:>7} µs" for value in (short, avg, long))
        return f"{self.name + ':':<40}  {fields}"

    def __enter__(self) -> Self:
        self.before = time.monotonic_ns()
        return self

    def __exit__(self, *args: Any) -> None:
        after = time.monotonic_ns()
        self.totals.append(after - self.before)


def benchmark() -> None:
    print("starting benchmark...")

    ufmt_dir = ROOT / "ufmt"
    ufmt_core = ufmt_dir / "core.py"
    assert ufmt_dir.is_dir(), f"{ufmt_dir} not found, must run benchmark from repo"

    print()
    print(Timer.fields())

    timer = Timer("ufmt_file")
    for _ in range(5):
        with timer:
            ufmt_file(ufmt_core, dry_run=True)
    print(timer)

    timer = Timer("ufmt_file, diff=True")
    for _ in range(5):
        with timer:
            ufmt_file(ufmt_core, dry_run=True, diff=True)
    print(timer)

    timer = Timer("ufmt_file, return_content=True")
    for _ in range(5):
        with timer:
            ufmt_file(ufmt_core, dry_run=True, return_content=True)
    print(timer)

    timer = Timer("ufmt_paths")
    for _ in range(5):
        with timer:
            list(ufmt_paths([ufmt_dir], dry_run=True))
    print(timer)

    timer = Timer("ufmt_paths, diff=True")
    for _ in range(5):
        with timer:
            list(ufmt_paths([ufmt_dir], dry_run=True, diff=True))
    print(timer)

    timer = Timer("ufmt_paths, return_content=True")
    for _ in range(5):
        with timer:
            list(ufmt_paths([ufmt_dir], dry_run=True, diff=True))
    print(timer)


if __name__ == "__main__":
    benchmark()
