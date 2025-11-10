"""
Base class for general DataFrame filters.
"""

from abc import ABC, abstractmethod
import pandas as pd


class DataFrameFilter(ABC):
    """
    Abstract base class for DataFrame filters.

    Filters can be applied at ANY stage:
    - Forecast data filtering
    - Actual data filtering
    - Anomaly results filtering
    - Any DataFrame transformation

    This is a general-purpose transformer, not specific to anomaly detection.
    """

    @abstractmethod
    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter a DataFrame.

        Args:
            df: Input DataFrame

        Returns:
            pd.DataFrame: Filtered DataFrame
        """
        pass
