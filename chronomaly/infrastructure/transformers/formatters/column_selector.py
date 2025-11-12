"""
Column selector formatter - keeps or drops specified columns.
"""

import pandas as pd
from typing import List, Union
from .base import DataFrameFormatter


class ColumnSelector(DataFrameFormatter):
    """
    Select or drop columns from DataFrame.

    This formatter allows you to keep only specified columns or drop unwanted columns.
    Supports both include (keep) and exclude (drop) modes for flexible column management.

    Args:
        columns: Column name or list of column names to keep or drop
        mode: 'keep' to keep only specified columns, 'drop' to remove them (default: 'drop')

    Examples:
        # Drop unwanted columns
        from chronomaly.infrastructure.transformers.formatters import ColumnSelector

        formatter = ColumnSelector(['internal_id', 'temp_column'], mode='drop')
        result = formatter.format(df)

        # Keep only specific columns
        formatter = ColumnSelector(['date', 'metric', 'value'], mode='keep')
        result = formatter.format(df)

        # Drop single column
        formatter = ColumnSelector('unwanted_column', mode='drop')
        result = formatter.format(df)

        # Use in workflow
        from chronomaly.infrastructure.notifiers import EmailNotifier

        email_notifier = EmailNotifier(
            to=["team@example.com"],
            transformers={
                'before': [
                    ColumnSelector(['internal_id', 'temp_field'], mode='drop')
                ]
            }
        )
    """

    def __init__(
        self,
        columns: Union[str, List[str]],
        mode: str = 'drop'
    ):
        """
        Initialize ColumnSelector.

        Args:
            columns: Column name or list of column names
            mode: 'keep' or 'drop' (default: 'drop')

        Raises:
            ValueError: If mode is not 'keep' or 'drop'
            ValueError: If columns list is empty
        """
        # Validate mode
        if mode not in ['keep', 'drop']:
            raise ValueError(
                f"mode must be 'keep' or 'drop', got '{mode}'"
            )

        # Normalize columns to list
        if isinstance(columns, str):
            self.columns = [columns]
        elif isinstance(columns, list):
            self.columns = list(columns)
        else:
            raise TypeError(
                f"columns must be a string or list of strings, got {type(columns).__name__}"
            )

        # Validate columns not empty
        if not self.columns:
            raise ValueError("columns list cannot be empty")

        self.mode = mode

    def format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Select or drop columns from DataFrame.

        Args:
            df: Input DataFrame

        Returns:
            pd.DataFrame: DataFrame with selected columns
        """
        # Handle empty DataFrame
        if df.empty:
            return df.copy()

        if self.mode == 'drop':
            # Drop specified columns (only those that exist)
            columns_to_drop = [col for col in self.columns if col in df.columns]
            return df.drop(columns=columns_to_drop).copy()
        else:  # mode == 'keep'
            # Keep only specified columns (only those that exist)
            columns_to_keep = [col for col in self.columns if col in df.columns]

            # If no columns match, return empty DataFrame with same index
            if not columns_to_keep:
                return pd.DataFrame(index=df.index)

            return df[columns_to_keep].copy()
