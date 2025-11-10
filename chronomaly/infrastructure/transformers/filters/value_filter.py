"""
Value filter - keeps rows based on column values.
"""

import pandas as pd
from typing import List, Union
from .base import DataFrameFilter


class ValueFilter(DataFrameFilter):
    """
    Filter DataFrame rows based on column values.

    This is a GENERAL filter that works on any DataFrame column.

    Args:
        column: Column name to filter on
        values: Value or list of values to keep/exclude
        mode: 'include' to keep matching rows, 'exclude' to remove them

    Example - Sadece anomalileri tut:
        filter = ValueFilter('status', ['BELOW_LOWER', 'ABOVE_UPPER'], mode='include')
        anomalies = filter.filter(results_df)

    Example - Belirli platformları çıkar:
        filter = ValueFilter('platform', ['tablet', 'other'], mode='exclude')
        filtered = filter.filter(data_df)

    Example - Belirli tarih aralığı:
        filter = ValueFilter('date', pd.date_range('2024-01-01', '2024-01-31'), mode='include')
        january_data = filter.filter(data_df)
    """

    def __init__(
        self,
        column: str,
        values: Union[any, List[any]],
        mode: str = 'include'
    ):
        if mode not in ['include', 'exclude']:
            raise ValueError(f"mode must be 'include' or 'exclude', got {mode}")

        self.column = column
        self.values = values if isinstance(values, list) else [values]
        self.mode = mode

    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter DataFrame by column values.

        Args:
            df: Input DataFrame

        Returns:
            pd.DataFrame: Filtered DataFrame
        """
        if df.empty or self.column not in df.columns:
            return df.copy()

        if self.mode == 'include':
            return df[df[self.column].isin(self.values)].copy()
        else:  # exclude
            return df[~df[self.column].isin(self.values)].copy()
