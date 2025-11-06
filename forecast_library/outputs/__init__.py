"""
Output writer implementations for forecast results.
"""

from .base import OutputWriter
from .sqlite_writer import SQLiteOutputWriter
from .bigquery_writer import BigQueryOutputWriter

__all__ = [
    "OutputWriter",
    "SQLiteOutputWriter",
    "BigQueryOutputWriter",
]
