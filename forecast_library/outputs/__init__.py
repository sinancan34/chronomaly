"""
Output writer implementations for forecast results.
"""

from .base import OutputWriter
from .sqlite_writer import SQLiteOutputWriter

__all__ = [
    "OutputWriter",
    "SQLiteOutputWriter",
]
