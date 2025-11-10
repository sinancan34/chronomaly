"""
Column filter - filters rows based on numeric column thresholds.
"""

import pandas as pd
from .base import DataFrameFilter


class ColumnFilter(DataFrameFilter):
    """
    Filter DataFrame rows based on numeric column thresholds.

    This is a GENERAL filter for any numeric filtering.

    Args:
        column: Column name to filter on
        min_value: Minimum value (inclusive), None for no minimum
        max_value: Maximum value (inclusive), None for no maximum

    Example - Minimum sapma:
        filter = ColumnFilter('deviation_pct', min_value=10.0)
        significant = filter.filter(anomaly_df)

    Example - Değer aralığı:
        filter = ColumnFilter('sessions', min_value=100, max_value=10000)
        filtered = filter.filter(data_df)

    Example - Maksimum filtre:
        filter = ColumnFilter('error_rate', max_value=0.05)
        acceptable = filter.filter(metrics_df)
    """

    def __init__(
        self,
        column: str,
        min_value: float = None,
        max_value: float = None
    ):
        if min_value is None and max_value is None:
            raise ValueError("At least one of min_value or max_value must be specified")

        self.column = column
        self.min_value = min_value
        self.max_value = max_value

    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter DataFrame by column threshold.

        Args:
            df: Input DataFrame

        Returns:
            pd.DataFrame: Filtered DataFrame
        """
        if df.empty or self.column not in df.columns:
            return df.copy()

        result = df.copy()

        if self.min_value is not None:
            result = result[result[self.column] >= self.min_value]

        if self.max_value is not None:
            result = result[result[self.column] <= self.max_value]

        return result
