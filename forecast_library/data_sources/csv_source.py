"""
CSV data source implementation.
"""

import pandas as pd
from typing import Optional, Dict, Any
from .base import DataSource


class CSVDataSource(DataSource):
    """
    Data source implementation for CSV files.

    Args:
        file_path: Path to the CSV file
        date_column: Name of the date column (will be parsed as datetime)
        **kwargs: Additional arguments to pass to pandas.read_csv()
    """

    def __init__(
        self,
        file_path: str,
        date_column: Optional[str] = None,
        **kwargs: Any
    ):
        self.file_path = file_path
        self.date_column = date_column
        self.read_csv_kwargs = kwargs

    def load(self) -> pd.DataFrame:
        """
        Load data from CSV file.

        Returns:
            pd.DataFrame: The loaded data
        """
        df = pd.read_csv(self.file_path, **self.read_csv_kwargs)

        if self.date_column and self.date_column in df.columns:
            df[self.date_column] = pd.to_datetime(df[self.date_column])

        return df
