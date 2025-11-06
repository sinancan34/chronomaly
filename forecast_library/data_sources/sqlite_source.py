"""
SQLite data source implementation.
"""

import pandas as pd
import sqlite3
from typing import Optional, Dict, Any
from .base import DataSource


class SQLiteDataSource(DataSource):
    """
    Data source implementation for SQLite databases.

    Args:
        database_path: Path to the SQLite database file
        query: SQL query to execute
        date_column: Name of the date column (will be parsed as datetime)
        **kwargs: Additional arguments to pass to pandas.read_sql_query()
    """

    def __init__(
        self,
        database_path: str,
        query: str,
        date_column: Optional[str] = None,
        **kwargs: Any
    ):
        self.database_path = database_path
        self.query = query
        self.date_column = date_column
        self.read_sql_kwargs = kwargs

    def load(self) -> pd.DataFrame:
        """
        Load data from SQLite database using the provided query.

        Returns:
            pd.DataFrame: The loaded data
        """
        conn = sqlite3.connect(self.database_path)

        try:
            df = pd.read_sql_query(self.query, conn, **self.read_sql_kwargs)

            if self.date_column and self.date_column in df.columns:
                df[self.date_column] = pd.to_datetime(df[self.date_column])

        finally:
            conn.close()

        return df
