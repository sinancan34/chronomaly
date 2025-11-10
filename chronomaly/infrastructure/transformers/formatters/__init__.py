"""
General-purpose DataFrame formatters.

Formatters transform DataFrame column values without filtering rows.
Can be applied at ANY stage of the pipeline.
"""

from .base import DataFrameFormatter
from .column_formatter import ColumnFormatter

__all__ = [
    'DataFrameFormatter',
    'ColumnFormatter'
]
