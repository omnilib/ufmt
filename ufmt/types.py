# Copyright 2021 John Reese, Tim Hatch
# Licensed under the MIT license

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from black import Mode as BlackConfig
from usort import Config as UsortConfig

Encoding = str
FileContent = bytes

BlackConfigFactory = Callable[[Path], BlackConfig]
UsortConfigFactory = Callable[[Path], UsortConfig]


@dataclass
class Result:
    path: Path
    changed: bool = False
    written: bool = False
    diff: Optional[str] = None
