"""
Column formatter - applies custom formatting functions to columns.
"""

import pandas as pd
from typing import List, Union, Callable, Dict
from .base import DataFrameFormatter


class ColumnFormatter(DataFrameFormatter):
    """
    Apply custom formatting functions to DataFrame columns.

    This is a UNIFIED GENERAL formatter for any column transformation.
    Supports both custom functions and built-in helpers like percentage formatting.

    Args:
        formatters: Dict mapping column names to formatting functions
                   Each function should take a single value and return formatted value

    Example 1 - Percentage formatting:
        formatter = ColumnFormatter.percentage(
            columns='deviation_pct',
            decimal_places=1
        )
        # 15.3 → "15.3%"
        formatted = formatter.format(anomaly_df)

    Example 2 - Custom functions:
        formatter = ColumnFormatter({
            'revenue': lambda x: f"${x:,.2f}",
            'sessions': lambda x: f"{x:,}",
            'date': lambda x: x.strftime('%Y-%m-%d')
        })
        formatted = formatter.format(df)

    Example 3 - Status icons:
        formatter = ColumnFormatter({
            'status': lambda x: '⚠️' if x in ['BELOW_LOWER', 'ABOVE_UPPER'] else '✓'
        })
        formatted = formatter.format(anomaly_df)

    Example 4 - Multiple columns with same format:
        formatter = ColumnFormatter({
            'growth_rate': lambda x: f"{x:.1f}%",
            'change_pct': lambda x: f"{x:.1f}%"
        })
        formatted = formatter.format(df)
    """

    def __init__(self, formatters: Dict[str, Callable]):
        if not formatters:
            raise ValueError("formatters dictionary cannot be empty")

        self.formatters: dict[str, Callable] = formatters

    @classmethod
    def percentage(
        cls,
        columns: Union[str, List[str]],
        decimal_places: int = 1,
        multiply_by_100: bool = False
    ):
        """
        Helper method to create percentage formatter.

        Args:
            columns: Column name or list of column names
            decimal_places: Number of decimal places (default: 1)
            multiply_by_100: If True, multiply by 100 before formatting (default: False)

        Returns:
            ColumnFormatter: Formatter configured for percentage formatting

        Example:
            formatter = ColumnFormatter.percentage('deviation_pct', decimal_places=2)
            formatted = formatter.format(df)
        """
        if decimal_places < 0:
            raise ValueError(f"decimal_places must be non-negative, got {decimal_places}")

        column_list = [columns] if isinstance(columns, str) else columns

        # Create formatting function
        def format_percentage(value):
            if multiply_by_100:
                value = value * 100
            return f"{value:.{decimal_places}f}%"

        # Create formatters dict
        formatters = {col: format_percentage for col in column_list}

        return cls(formatters)

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
