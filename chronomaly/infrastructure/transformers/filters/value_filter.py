"""
Value filter - keeps rows based on column values or numeric thresholds.
"""

import pandas as pd
from typing import Any, List, Union, Optional
from .base import DataFrameFilter


class ValueFilter(DataFrameFilter):
    """
    Filter DataFrame rows based on column values (categorical or numeric).

    This is a UNIFIED GENERAL filter that supports:
    1. Categorical filtering: Filter by specific values (include/exclude mode)
    2. Numeric filtering: Filter by min/max thresholds
    3. Both: Apply both categorical and numeric filters together

    Args:
        column: Column name to filter on
        values: Value or list of values to keep/exclude (optional)
        mode: 'include' to keep matching rows, 'exclude' to remove them (default: 'include')
        min_value: Minimum value (inclusive), None for no minimum (optional)
        max_value: Maximum value (inclusive), None for no maximum (optional)

    Example 1 - Kategorik filtreleme (sadece anomalileri tut):
        filter = ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER'], mode='include')
        anomalies = filter.filter(results_df)

    Example 2 - Belirli platformları çıkar:
        filter = ValueFilter('platform', values=['tablet', 'other'], mode='exclude')
        filtered = filter.filter(data_df)

    Example 3 - Sayısal filtreleme (minimum sapma):
        filter = ValueFilter('deviation_pct', min_value=10.0)
        significant = filter.filter(anomaly_df)

    Example 4 - Sayısal aralık:
        filter = ValueFilter('sessions', min_value=100, max_value=10000)
        filtered = filter.filter(data_df)

    Example 5 - Her ikisi birlikte:
        filter = ValueFilter('sessions', values=[100, 200, 300], min_value=150)
        # First filters to values [100, 200, 300], then applies min_value >= 150
        # Result: [200, 300]
    """

    def __init__(
        self,
        column: str,
        values: Optional[Union[Any, List[Any]]] = None,
        mode: str = 'include',
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ):
        # Validate inputs
        if values is None and min_value is None and max_value is None:
            raise ValueError("At least one of 'values', 'min_value', or 'max_value' must be specified")

        if mode not in ['include', 'exclude']:
            raise ValueError(f"mode must be 'include' or 'exclude', got {mode}")

        self.column = column
        self.values = values if values is None else (values if isinstance(values, list) else [values])
        self.mode = mode
        self.min_value = min_value
        self.max_value = max_value

    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter DataFrame by column values and/or numeric thresholds.

        Args:
            df: Input DataFrame

        Returns:
            pd.DataFrame: Filtered DataFrame
        """
        if df.empty or self.column not in df.columns:
            return df.copy()

        result = df.copy()

        # Apply categorical filter (if values specified)
        if self.values is not None:
            if self.mode == 'include':
                result = result[result[self.column].isin(self.values)]
            else:  # exclude
                result = result[~result[self.column].isin(self.values)]

        # Apply numeric filters (if min/max specified)
        if self.min_value is not None:
            result = result[result[self.column] >= self.min_value]

        if self.max_value is not None:
            result = result[result[self.column] <= self.max_value]

        return result
