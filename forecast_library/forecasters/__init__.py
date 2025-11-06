"""
Forecaster implementations for time series prediction.
"""

from .base import Forecaster
from .timesfm import TimesFMForecaster

__all__ = [
    "Forecaster",
    "TimesFMForecaster",
]
