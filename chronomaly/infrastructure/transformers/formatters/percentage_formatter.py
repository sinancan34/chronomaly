"""
Percentage formatter - formats numeric columns as percentage strings.
"""

import pandas as pd
from typing import List, Union
from .base import DataFrameFormatter


class PercentageFormatter(DataFrameFormatter):
    """
    Format numeric columns as percentage strings.

    This is a GENERAL formatter for any DataFrame.

    Args:
        columns: Column name or list of column names to format
        decimal_places: Number of decimal places (default: 1)
        multiply_by_100: If True, multiply value by 100 before formatting (default: False)

    Example - Anomaly deviation formatla:
        formatter = PercentageFormatter('deviation_pct', decimal_places=1)
        # 15.3 → "15.3%"
        formatted = formatter.format(anomaly_df)

    Example - Conversion rate formatla:
        formatter = PercentageFormatter('conversion_rate', decimal_places=2, multiply_by_100=True)
        # 0.153 → "15.30%"
        formatted = formatter.format(metrics_df)

    Example - Birden fazla kolon:
        formatter = PercentageFormatter(['growth_rate', 'change_pct'], decimal_places=1)
        formatted = formatter.format(df)
    """

    def __init__(
        self,
        columns: Union[str, List[str]],
        decimal_places: int = 1,
        multiply_by_100: bool = False
    ):
        if decimal_places < 0:
            raise ValueError(f"decimal_places must be non-negative, got {decimal_places}")

        self.columns = [columns] if isinstance(columns, str) else columns
        self.decimal_places = decimal_places
        self.multiply_by_100 = multiply_by_100

    def format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Format columns as percentage strings.

        Args:
            df: Input DataFrame

        Returns:
            pd.DataFrame: Formatted DataFrame
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        for column in self.columns:
            if column in result.columns:
                values = result[column]

                # Multiply by 100 if needed
                if self.multiply_by_100:
                    values = values * 100

                # Format as string with percentage sign
                result[column] = (
                    values.round(self.decimal_places)
                    .astype(str) + '%'
                )

        return result
