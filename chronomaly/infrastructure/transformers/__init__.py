"""
Data transformers - general-purpose DataFrame transformations.

This module provides:
- Pivot: Convert between wide and long formats
- Filters: Filter DataFrame rows based on conditions
- Formatters: Format DataFrame column values

All transformers are general-purpose and can be used at any pipeline stage.
"""

from .pivot import PivotTransformer
from . import filters
from . import formatters

__all__ = [
    'PivotTransformer',
    'filters',
    'formatters'
]
