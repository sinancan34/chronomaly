"""
CSV data reader implementation.
"""

import pandas as pd
import os
from typing import Optional, Dict, Any, List, Callable
from ..base import DataReader
from chronomaly.shared import TransformableMixin


class CSVDataReader(DataReader, TransformableMixin):
    """
    Data reader implementation for CSV files.

    Args:
        file_path: Path to the CSV file
        date_column: Name of the date column (will be parsed as datetime)
        transformers: Optional dict of transformer lists to apply after loading data
                     Example: {'after': [Filter1(), Filter2()]}
                     Note: 'before' stage not supported for readers
        **kwargs: Additional arguments to pass to pandas.read_csv()

    Security Notes:
        - file_path is validated to prevent path traversal attacks.
        - Only files that exist and are readable will be processed.
    """

    def __init__(
        self,
        file_path: str,
        date_column: Optional[str] = None,
        transformers: Optional[Dict[str, List[Callable]]] = None,
        **kwargs: Any
    ):
        # BUG-17 FIX: Validate file path to prevent path traversal
        if not file_path:
            raise ValueError("file_path cannot be empty")

        # Resolve to absolute path
        abs_path = os.path.abspath(file_path)

        # BUG-41 FIX: Check if file exists
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(
                f"CSV file not found: {abs_path}"
            )

        # Check if file is readable
        if not os.access(abs_path, os.R_OK):
            raise PermissionError(
                f"CSV file is not readable: {abs_path}"
            )

        self.file_path = abs_path
        self.date_column = date_column
        self.transformers = transformers or {}
        self.read_csv_kwargs = kwargs

    def load(self) -> pd.DataFrame:
        """
        Load data from CSV file.

        Returns:
            pd.DataFrame: The loaded data

        Raises:
            FileNotFoundError: If CSV file does not exist
            ValueError: If date_column is not found or data is invalid
        """
        try:
            df = pd.read_csv(self.file_path, **self.read_csv_kwargs)
        except Exception as e:
            raise RuntimeError(
                f"Failed to read CSV file '{self.file_path}': {str(e)}"
            ) from e

        if df.empty:
            raise ValueError(
                f"CSV file is empty: {self.file_path}"
            )

        if self.date_column:
            if self.date_column not in df.columns:
                raise ValueError(
                    f"date_column '{self.date_column}' not found in CSV file. "
                    f"Available columns: {list(df.columns)}"
                )

            try:
                df[self.date_column] = pd.to_datetime(df[self.date_column])
            except Exception as e:
                raise ValueError(
                    f"Failed to parse date_column '{self.date_column}' as datetime: {str(e)}"
                ) from e

        # Apply transformers after loading data
        df = self._apply_transformers(df, 'after')

        return df
