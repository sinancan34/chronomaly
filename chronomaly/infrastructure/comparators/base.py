"""
Base abstract class for anomaly detectors.
"""

from abc import ABC, abstractmethod
import pandas as pd


class AnomalyDetector(ABC):
    """
    Abstract base class for all anomaly detector implementations.

    All anomaly detector implementations must inherit from this class
    and implement the detect() method.
    """

    @abstractmethod
    def detect(
        self,
        forecast_df: pd.DataFrame,
        actual_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Detect anomalies by comparing forecast and actual data.

        Args:
            forecast_df: Forecast data as pandas DataFrame
            actual_df: Actual data as pandas DataFrame

        Returns:
            pd.DataFrame: Anomaly detection results with status and deviation metrics
        """
        pass
