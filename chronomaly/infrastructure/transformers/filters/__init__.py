"""
General-purpose DataFrame filters.

Filters can be applied at ANY stage of the pipeline:
- Before forecast
- After forecast
- Before anomaly detection
- After anomaly detection
- Before writing
"""

from .base import DataFrameFilter
from .cumulative_threshold import CumulativeThresholdFilter
from .value_filter import ValueFilter

__all__ = [
    'DataFrameFilter',
    'CumulativeThresholdFilter',
    'ValueFilter'
]
