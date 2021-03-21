"""
usort + black, in that order
"""

__author__ = "John Reese"
import sys
from pathlib import Path
from typing import List

import click
from black import decode_bytes, format_file_contents, Mode, NothingChanged
from usort.config import Config
from usort.sorting import usort_string
from usort.util import walk

from .__version__ import __version__
from .core import ufmt_paths, ufmt_file, ufmt_string
