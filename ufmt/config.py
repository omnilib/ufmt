# Copyright 2021 John Reese
# Licensed under the MIT license

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import tomlkit
from trailrunner import project_root


@dataclass
class UfmtConfig:
    project_root: Optional[Path] = None
    pyproject_path: Optional[Path] = None
    excludes: List[str] = field(default_factory=list)


def ufmt_config(path: Optional[Path] = None) -> UfmtConfig:
    path = path or Path.cwd()
    root = project_root(path)
    config_path = root / "pyproject.toml"
    if config_path.is_file():
        pyproject = tomlkit.loads(config_path.read_text())
        config: Dict[str, Any] = {}

        if "tool" in pyproject and "ufmt" in pyproject["tool"]:  # type: ignore
            config.update(pyproject["tool"]["ufmt"])  # type: ignore

        config["project_root"] = root
        config["pyproject_path"] = config_path
        return UfmtConfig(**config)

    return UfmtConfig()
