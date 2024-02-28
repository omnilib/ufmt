# Copyright Amethyst Reese, Tim Hatch
# Licensed under the MIT license

import time
from pathlib import Path
from typing import Any, List

from typing_extensions import Self

from ufmt import ufmt_file, ufmt_paths

ROOT = Path(__file__).parent.parent.parent


class Benchmark:
    def __init__(self, target: int = 5) -> None:
        self.target = target
        self.last_time: int = 0
        self.title: str = ""
        self.totals: List[int] = []

    @classmethod
    def fields(self) -> str:
        headline = f"{'benchmark':^40}  {'min':^10}  {'mean':^10}  {'max':^10}"
        underline = "-" * len(headline)
        return f"{headline}\n{underline}"

    def results(self) -> str:
        totals = self.totals
        short = min(totals)
        long = max(totals)
        avg = sum(totals) // len(totals)
        fields = "  ".join(f"{value // 1000:>7} µs" for value in (short, avg, long))
        return f"{self.title + ':':<40}  {fields}"

    def __enter__(self) -> Self:
        print()
        print(self.fields())
        return self

    def __exit__(self, *args: Any) -> None:
        print()

    def __call__(self, name: str) -> Self:
        self.title = name
        return self

    def __iter__(self) -> Self:
        self.last_time = 0
        self.totals = []
        return self

    def __next__(self) -> None:
        now = time.monotonic_ns()
        if self.last_time > 0:
            self.totals += [now - self.last_time]
        if len(self.totals) >= self.target:
            print(self.results())
            self.totals = []
            self.title = ""

            raise StopIteration
        self.last_time = time.monotonic_ns()


def benchmark() -> None:
    ufmt_dir = ROOT / "ufmt"
    ufmt_core = ufmt_dir / "core.py"
    assert ufmt_dir.is_dir(), f"{ufmt_dir} not found, must run benchmark from repo"

    with Benchmark() as benchmark:

        for _ in benchmark("ufmt_file"):
            ufmt_file(ufmt_core, dry_run=True)

        for _ in benchmark("ufmt_paths"):
            list(ufmt_paths([ufmt_dir], dry_run=True))


if __name__ == "__main__":
    benchmark()
