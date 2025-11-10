"""
Column formatter - applies custom formatting functions to columns.
"""

import pandas as pd
from typing import List, Union, Callable, Dict
from .base import DataFrameFormatter


class ColumnFormatter(DataFrameFormatter):
    """
    Apply custom formatting functions to DataFrame columns.

    This is the most FLEXIBLE formatter - you can define any transformation.

    Args:
        formatters: Dict mapping column names to formatting functions
                   or single column name with format_func

    Example - Tarih formatla:
        formatter = ColumnFormatter({'date': lambda x: x.strftime('%Y-%m-%d')})
        formatted = formatter.format(df)

    Example - Sayıları formatla:
        formatter = ColumnFormatter({
            'revenue': lambda x: f"${x:,.2f}",
            'sessions': lambda x: f"{x:,}"
        })
        formatted = formatter.format(df)

    Example - Custom transformation:
        formatter = ColumnFormatter({
            'status': lambda x: '⚠️' if x in ['BELOW_LOWER', 'ABOVE_UPPER'] else '✓'
        })
        formatted = formatter.format(anomaly_df)
    """

    def __init__(self, formatters: Dict[str, Callable]):
        if not formatters:
            raise ValueError("formatters dictionary cannot be empty")

        self.formatters = formatters

    def format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply formatting functions to columns.

        Args:
            df: Input DataFrame

        Returns:
            pd.DataFrame: Formatted DataFrame
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        for column, format_func in self.formatters.items():
            if column in result.columns:
                result[column] = result[column].apply(format_func)

        return result
