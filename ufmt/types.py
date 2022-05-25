# Copyright 2021 John Reese, Tim Hatch
# Licensed under the MIT license

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from black import Mode as BlackConfig
from typing_extensions import Protocol
from usort import Config as UsortConfig

STDIN = Path("-")

Encoding = str
FileContent = bytes
Newline = bytes

BlackConfigFactory = Callable[[Path], BlackConfig]
UsortConfigFactory = Callable[[Path], UsortConfig]


class Processor(Protocol):
    def __call__(
        self,
        path: Path,
        content: FileContent,
        *,
        encoding: Encoding = "utf-8",
    ) -> FileContent:  # pragma: nocover
        """
        Process bytes before or after formatting and return the updated file content.
        """
        ...


@dataclass
class Result:
    """
    Basic metadata results from formatting files.
    """

    path: Path
    changed: bool = False
    written: bool = False
    diff: Optional[str] = None
    error: Optional[Exception] = None
    before: bytes = b""  # only set if return_content=True
    after: bytes = b""  # only set if return_content=True
