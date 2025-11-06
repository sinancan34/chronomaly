"""
Base abstract class for forecasters.
"""

from abc import ABC, abstractmethod
import pandas as pd


class Forecaster(ABC):
    """
    Abstract base class for all forecaster implementations.

    All forecaster implementations must inherit from this class
    and implement the forecast() method.
    """

    @abstractmethod
    def forecast(self, dataframe: pd.DataFrame, horizon: int) -> pd.DataFrame:
        """
        Generate forecast for the given dataframe.

        Args:
            dataframe: Input pandas DataFrame with time series data
            horizon: Number of periods to forecast

        Returns:
            pd.DataFrame: Forecast results as a pandas DataFrame
        """
        pass
