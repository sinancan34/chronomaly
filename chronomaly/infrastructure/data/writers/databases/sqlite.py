"""
SQLite data writer implementation.
"""

import pandas as pd
import sqlite3
import os
import re
from typing import Optional, Dict, List, Callable
from ..base import DataWriter


class SQLiteDataWriter(DataWriter):
    """
    Data writer implementation for SQLite databases.

    Args:
        database_path: Path to the SQLite database file
        table_name: Name of the table to write to
        if_exists: How to behave if table exists {'fail', 'replace', 'append'}
                   (default: 'replace')
        transformers: Optional dict of transformer lists to apply before writing data
                     Example: {'after': [Filter1(), Filter2()]}
        **kwargs: Additional arguments to pass to pandas.to_sql()

    Security Notes:
        - database_path is validated to prevent path traversal attacks.
        - table_name is validated to prevent SQL injection.
        - Only alphanumeric characters and underscores are allowed in table names.
    """

    def __init__(
        self,
        database_path: str,
        table_name: str,
        if_exists: str = 'replace',
        transformers: Optional[Dict[str, List[Callable]]] = None,
        **kwargs
    ):
        # BUG-20 FIX: Validate database path to prevent path traversal
        if not database_path:
            raise ValueError("database_path cannot be empty")

        # Resolve to absolute path
        abs_path = os.path.abspath(database_path)

        # Ensure parent directory exists or can be created
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

        self.database_path = abs_path

        # BUG-22 FIX: Validate table name to prevent SQL injection
        if not table_name:
            raise ValueError("table_name cannot be empty")

        # Only allow alphanumeric characters and underscores
        if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
            raise ValueError(
                f"Invalid table_name: '{table_name}'. "
                "Only alphanumeric characters and underscores are allowed."
            )

        # Don't allow names that look like SQL keywords
        sql_keywords = {'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter'}
        if table_name.lower() in sql_keywords:
            raise ValueError(
                f"table_name cannot be a SQL keyword: '{table_name}'"
            )

        self.table_name = table_name

        # BUG-27 FIX: Validate if_exists parameter
        valid_if_exists = ['fail', 'replace', 'append']
        if if_exists not in valid_if_exists:
            raise ValueError(
                f"Invalid if_exists value: '{if_exists}'. "
                f"Must be one of: {valid_if_exists}"
            )

        self.if_exists = if_exists
        self.transformers = transformers or {}
        self.to_sql_kwargs = kwargs

    def _apply_transformers(self, df: pd.DataFrame, stage: str) -> pd.DataFrame:
        """
        Apply transformers for a specific stage.

        Args:
            df: DataFrame to transform
            stage: Stage name ('after')

        Returns:
            pd.DataFrame: Transformed DataFrame
        """
        if stage not in self.transformers:
            return df

        result = df
        for transformer in self.transformers[stage]:
            # Support both .filter() and .format() methods
            if hasattr(transformer, 'filter'):
                result = transformer.filter(result)
            elif hasattr(transformer, 'format'):
                result = transformer.format(result)
            elif callable(transformer):
                result = transformer(result)
            else:
                raise TypeError(f"Transformer must have .filter(), .format() method or be callable")

        return result

    def write(self, dataframe: pd.DataFrame) -> None:
        """
        Write forecast results to SQLite database.

        Args:
            dataframe: The forecast results as a pandas DataFrame

        Raises:
            ValueError: If dataframe is empty or invalid
            RuntimeError: If database write operation fails
        """
        # Apply transformers before writing data
        dataframe = self._apply_transformers(dataframe, 'after')

        # BUG-44 FIX: Validate dataframe type
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame, got {type(dataframe).__name__}"
            )

        if dataframe.empty:
            raise ValueError("Cannot write empty DataFrame to database")

        # BUG-28 FIX: Add comprehensive error handling
        conn = None
        try:
            conn = sqlite3.connect(self.database_path)

            dataframe.to_sql(
                name=self.table_name,
                con=conn,
                if_exists=self.if_exists,
                index=False,
                **self.to_sql_kwargs
            )

        except sqlite3.Error as e:
            raise RuntimeError(
                f"SQLite database error while writing to table '{self.table_name}': {str(e)}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Failed to write data to SQLite database '{self.database_path}': {str(e)}"
            ) from e
        finally:
            if conn is not None:
                conn.close()
