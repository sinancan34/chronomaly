"""
Data transformation utilities for pivot operations.
"""

import pandas as pd
from typing import Union, List


class DataTransformer:
    """
    Data transformer for converting time series data into pivot format.

    This class transforms long-format time series data into wide-format
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
        self.index = index
        self.columns = columns
        self.values = values

    def pivot_table(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Transform dataframe into pivot table format.

        Args:
            dataframe: Input pandas DataFrame

        Returns:
            pd.DataFrame: Pivoted dataframe
        """
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

        # Clean string columns (lowercase, remove special characters)
        for column in df.columns:
            if df[column].dtype == 'object' and column not in index_list:
                df[column] = df[column].str.lower().str.replace(
                    r'[\(\)\.\-\_\s]', '', regex=True
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

        # Create pivot table
        dataframe_pivot = df.pivot_table(
            index=index_list,
            columns=pivot_columns,
            values=self.values,
            aggfunc='sum'
        )

        # Fill NaN values with 0
        dataframe_pivot = dataframe_pivot.fillna(0)

        # If single index column is 'date', set daily frequency
        if len(index_list) == 1 and index_list[0] == 'date':
            dataframe_pivot = dataframe_pivot.asfreq('D', fill_value=0)

        return dataframe_pivot
