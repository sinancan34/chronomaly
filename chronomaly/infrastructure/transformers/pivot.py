"""
Data transformation utilities for pivot operations.
"""

import pandas as pd
from typing import Union, List


class PivotTransformer:
    """
    Pivot transformer for converting time series data between long and wide formats.

    This class transforms long-format time series data into wide-format (pivot table)
    suitable for forecasting models.

    Args:
        index: Column name(s) to use as index (typically date column)
        columns: Column name(s) to use as pivot columns (time series identifiers)
        values: Column name to use as values
    """

    def __init__(
        self,
        index: Union[str, List[str]],
        columns: Union[str, List[str]],
        values: str
    ):
        self.index: str | list[str] = index
        self.columns: str | list[str] = columns
        self.values: str = values

    def __call__(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Make PivotTransformer callable for use in transformers list.

        This allows using PivotTransformer in the transformers parameter:
        transformers={'after': [PivotTransformer(...)]}

        Args:
            dataframe: Input pandas DataFrame

        Returns:
            pd.DataFrame: Pivoted dataframe
        """
        return self.pivot_table(dataframe)

    def pivot_table(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Transform dataframe into pivot table format.

        Args:
            dataframe: Input pandas DataFrame

        Returns:
            pd.DataFrame: Pivoted dataframe

        Raises:
            TypeError: If dataframe is not a pandas DataFrame
            ValueError: If dataframe is empty or required columns are missing
        """
        # Validate input type
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame, got {type(dataframe).__name__}"
            )

        if dataframe.empty:
            raise ValueError("Cannot transform empty DataFrame")

        df = dataframe.copy()

        # Convert index to list
        if isinstance(self.index, str):
            index_list = [self.index]
        else:
            index_list = list(self.index)

        # Convert columns to list
        if isinstance(self.columns, str):
            columns_list = [self.columns]
        else:
            columns_list = list(self.columns)

        # BUG-36 FIX: Validate that required columns exist in dataframe
        all_required_columns = set(index_list + columns_list + [self.values])
        missing_columns = all_required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                f"Required columns not found in DataFrame: {sorted(missing_columns)}. "
                f"Available columns: {sorted(df.columns)}"
            )

        # Convert pivot columns to string before cleaning
        for column in columns_list:
            df[column] = df[column].astype(str)

        # Clean string columns (lowercase, remove special characters)
        # BUG-35 FIX: Add logging/warning instead of silent pass
        for column in df.columns:
            if df[column].dtype == 'object' and column not in index_list:
                # Check if column actually contains strings
                try:
                    # Only apply string operations if column contains strings
                    if df[column].apply(lambda x: isinstance(x, str) if x is not None else True).all():
                        df[column] = df[column].str.lower().str.replace(
                            r'[\(\)\.\-\_\s]', '', regex=True
                        )
                except (AttributeError, TypeError) as e:
                    # Skip columns that don't support string operations
                    # Log the issue for debugging but don't fail
                    import warnings
                    warnings.warn(
                        f"Could not apply string transformations to column '{column}': {str(e)}",
                        UserWarning
                    )

        # Fill NaN values in numeric columns with 0
        numeric_cols = df.select_dtypes(include='number').columns
        df[numeric_cols] = df[numeric_cols].fillna(0)

        # Create combined timeseries_id if multiple columns
        if len(columns_list) > 1:
            df['timeseries_id'] = df[columns_list].apply(
                lambda x: '_'.join(x.astype(str)), axis=1
            )
            pivot_columns = 'timeseries_id'
        else:
            pivot_columns = columns_list[0]

        # BUG-37 FIX: Add error handling around pivot_table operation
        try:
            # Create pivot table
            dataframe_pivot = df.pivot_table(
                index=index_list,
                columns=pivot_columns,
                values=self.values,
                aggfunc='sum'
            )
        except ValueError as e:
            # Common issues: duplicate indices, incompatible types, etc.
            raise ValueError(
                f"Failed to create pivot table. "
                f"This often happens with duplicate index/column combinations. "
                f"Original error: {str(e)}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error during pivot table creation: {str(e)}"
            ) from e

        # Fill NaN values with 0
        dataframe_pivot = dataframe_pivot.fillna(0)

        # If single index is DatetimeIndex, set daily frequency
        if len(index_list) == 1 and isinstance(dataframe_pivot.index, pd.DatetimeIndex):
            dataframe_pivot = dataframe_pivot.asfreq('D', fill_value=0)

        return dataframe_pivot
