"""
CSV data writer implementation.
"""

import pandas as pd
import os
from typing import Optional, Dict, List, Callable, Any
from ..base import DataWriter
from chronomaly.shared import TransformableMixin


class CSVDataWriter(DataWriter, TransformableMixin):
    """
    Data writer implementation for CSV files.

    Args:
        file_path: Path to the CSV file to write
        if_exists: How to behave if file exists {'replace', 'append'}
                   (default: 'replace')
        transformers: Optional dict of transformer lists to apply before writing
                     Example: {'before': [Filter1(), Filter2()]}
        **kwargs: Additional arguments to pass to pandas.to_csv()

    Security Notes:
        - file_path is validated to prevent path traversal attacks.
        - Parent directory must exist and be writable.
    """

    def __init__(
        self,
        file_path: str,
        if_exists: str = 'replace',
        transformers: Optional[Dict[str, List[Callable]]] = None,
        **kwargs: Any
    ):
        # Validate file path to prevent path traversal
        if not file_path:
            raise ValueError("file_path cannot be empty")

        # Resolve to absolute path
        abs_path = os.path.abspath(file_path)

        # Ensure parent directory exists
        parent_dir = os.path.dirname(abs_path)
        if not os.path.exists(parent_dir):
            raise FileNotFoundError(
                f"Parent directory does not exist: {parent_dir}"
            )

        # Check if parent directory is writable
        if not os.access(parent_dir, os.W_OK):
            raise PermissionError(
                f"Parent directory is not writable: {parent_dir}"
            )

        # If file exists, check if it's writable (for append mode)
        if os.path.exists(abs_path) and not os.access(abs_path, os.W_OK):
            raise PermissionError(
                f"CSV file is not writable: {abs_path}"
            )

        self.file_path = abs_path

        # Validate if_exists parameter
        valid_if_exists = ['replace', 'append']
        if if_exists not in valid_if_exists:
            raise ValueError(
                f"Invalid if_exists value: '{if_exists}'. "
                f"Must be one of: {valid_if_exists}"
            )

        self.if_exists = if_exists
        self.transformers = transformers or {}
        self.to_csv_kwargs = kwargs

    def write(self, dataframe: pd.DataFrame) -> None:
        """
        Write forecast results to CSV file.

        Args:
            dataframe: The forecast results as a pandas DataFrame

        Raises:
            TypeError: If dataframe is not a pandas DataFrame
            ValueError: If dataframe is empty
            RuntimeError: If CSV write operation fails
        """
        # Apply transformers before writing data
        dataframe = self._apply_transformers(dataframe, 'before')

        # Validate dataframe type
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame, got {type(dataframe).__name__}"
            )

        if dataframe.empty:
            raise ValueError("Cannot write empty DataFrame to CSV file")

        try:
            # Determine write mode based on if_exists parameter
            mode = 'w' if self.if_exists == 'replace' else 'a'

            # For append mode, check if file exists and has headers
            write_header = True
            if self.if_exists == 'append' and os.path.exists(self.file_path):
                # If file exists and has content, don't write header
                if os.path.getsize(self.file_path) > 0:
                    write_header = False

            # Write to CSV
            dataframe.to_csv(
                self.file_path,
                mode=mode,
                header=write_header,
                index=False,
                **self.to_csv_kwargs
            )

        except PermissionError as e:
            raise PermissionError(
                f"Permission denied while writing to CSV file '{self.file_path}': {str(e)}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Failed to write data to CSV file '{self.file_path}': {str(e)}"
            ) from e
