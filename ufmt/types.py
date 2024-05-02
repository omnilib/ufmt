# Copyright 2022 Amethyst Reese, Tim Hatch
# Licensed under the MIT license

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Union

from black import Mode as BlackConfig
from typing_extensions import Protocol
from usort import Config as UsortConfig

__all__ = [
    "BlackConfig",
    "BlackConfigFactory",
    "Encoding",
    "FileContent",
    "Newline",
    "Options",
    "Processor",
    "Result",
    "SkipFormatting",
    "STDIN",
    "UsortConfig",
    "UsortConfigFactory",
]

STDIN = Path("-")

Encoding = str
FileContent = bytes
Newline = bytes

BlackConfigFactory = Callable[[Path], BlackConfig]
UsortConfigFactory = Callable[[Path], UsortConfig]


class Formatter(Enum):
    """
    Select preferred formatter implementation.
    """

    black = "black"
    """Use black (default)."""

    ruff_api = "ruff-api"
    """
    **Experimental:**
    Use Ruff via unofficial `ruff-api <https://pypi.org/project/ruff-api>`_ extension.

    .. note::
        This implementation still depends on and uses the ``[tool.black]`` configuration
        table from ``pyproject.toml`` rather than Ruff's own configuration options.
        This may change in future updates.
    """


class Sorter(Enum):
    """
    Preferred import sorter implementation.
    """

    skip = "skip"
    """Skip sorting imports"""

    usort = "usort"
    """Use µsort (default)."""

    ruff_api = "ruff-api"
    """
    **Experimental:**
    Use Ruff's isort lint rules via unofficial
    `ruff-api <https://pypi.org/project/ruff-api>`_ extension.

    .. note::
        This implementation still depends on and uses the ``[tool.usort]`` configuration
        table from ``pyproject.toml`` rather than Ruff's own configuration options.
        This may change in future updates.
    """


@dataclass
class UfmtConfig:
    project_root: Optional[Path] = None
    pyproject_path: Optional[Path] = None
    excludes: List[str] = field(default_factory=list)
    formatter: Formatter = Formatter.black
    sorter: Sorter = Sorter.usort


UfmtConfigFactory = Callable[[Optional[Path], Optional[Path]], UfmtConfig]


@dataclass
class Options:
    debug: bool = False
    quiet: bool = False
    concurrency: Optional[int] = None
    root: Optional[Path] = None


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


class SkipFormatting(Exception):
    """Raise this exception in a pre/post processor to skip formatting a file."""


@dataclass
class Result:
    """
    Basic metadata results from formatting files.
    """

    path: Path
    changed: bool = False
    written: bool = False
    skipped: Union[bool, str] = False
    diff: Optional[str] = None
    error: Optional[Exception] = None
    before: bytes = b""  # only set if return_content=True
    after: bytes = b""  # only set if return_content=True
