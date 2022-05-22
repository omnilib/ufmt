"""
Safe, atomic formatting with black and µsort
"""

__author__ = "John Reese"
from .__version__ import __version__
from .core import Result, ufmt_file, ufmt_paths, ufmt_string

__all__ = [
    "Result",
    "ufmt_file",
    "ufmt_paths",
    "ufmt_string",
]
