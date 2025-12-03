"""
Cumulative threshold filter - keeps top X% of rows by value.
"""

import pandas as pd
from typing import List, Optional
from .base import DataFrameFilter


class CumulativeThresholdFilter(DataFrameFilter):
    """
    Filter to keep only top X% of rows by cumulative sum.

    This is a GENERAL filter that can be used:
    - Before forecast: Filter historical data
    - After forecast: Filter forecast results
    - Before anomaly detection: Filter metrics
    - After anomaly detection: Filter anomaly results

    Args:
        value_column: Column to use for cumulative calculation
        threshold_pct: Cumulative percentage threshold (e.g., 0.95 for top 95%)
        exclude_columns: Columns to exclude from row removal (e.g., ['date'])

    Example - Forecast öncesi:
        filter = CumulativeThresholdFilter('sessions', threshold_pct=0.95)
        filtered_data = filter.filter(historical_df)

    Example - Anomaly detection öncesi:
        filter = CumulativeThresholdFilter('forecast', threshold_pct=0.90)
        filtered_forecast = filter.filter(forecast_df)

    Example - Anomaly sonrası:
        filter = CumulativeThresholdFilter('deviation_pct', threshold_pct=0.80)
        top_anomalies = filter.filter(anomaly_results)
    """

    def __init__(
        self,
        value_column: str,
        threshold_pct: float = 0.95,
        exclude_columns: Optional[List[str]] = None
    ):
        if not 0 < threshold_pct <= 1.0:
            raise ValueError(f"threshold_pct must be between 0 and 1, got {threshold_pct}")

        self.value_column: str = value_column
        self.threshold_pct: float = threshold_pct
        self.exclude_columns: list[str] = exclude_columns or []

    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter DataFrame to keep only top X% of rows by cumulative sum.

        Args:
            df: Input DataFrame

        Returns:
            pd.DataFrame: Filtered DataFrame with top X% rows
        """
        if df.empty or self.value_column not in df.columns:
            return df.copy()

        # Calculate total
        total_value = df[self.value_column].sum()

        if total_value == 0:
            return df.copy()

        # Sort and calculate cumulative percentage
        sorted_values = df[self.value_column].sort_values(ascending=False)
        cumulative_sum = sorted_values.cumsum()
        cumulative_pct = cumulative_sum / total_value

        # Find minimum threshold value
        threshold_mask = cumulative_pct >= self.threshold_pct
        if threshold_mask.any():
            first_exceed_idx = threshold_mask.idxmax()  # İlk True = ilk kez aştığı nokta
            min_threshold = sorted_values.loc[:first_exceed_idx].min()
        else:
            min_threshold = sorted_values.min()

        # Filter original DataFrame
        return df[df[self.value_column] >= min_threshold].copy()
