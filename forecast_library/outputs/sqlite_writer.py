"""
SQLite output writer implementation.
"""

import pandas as pd
import sqlite3
from typing import Optional
from .base import OutputWriter


class SQLiteOutputWriter(OutputWriter):
    """
    Output writer implementation for SQLite databases.

    Args:
        database_path: Path to the SQLite database file
        table_name: Name of the table to write to
        if_exists: How to behave if table exists {'fail', 'replace', 'append'}
                   (default: 'replace')
        **kwargs: Additional arguments to pass to pandas.to_sql()
    """

    def __init__(
        self,
        database_path: str,
        table_name: str,
        if_exists: str = 'replace',
        **kwargs
    ):
        self.database_path = database_path
        self.table_name = table_name
        self.if_exists = if_exists
        self.to_sql_kwargs = kwargs

    def write(self, dataframe: pd.DataFrame) -> None:
        """
        Write forecast results to SQLite database.

        Args:
            dataframe: The forecast results as a pandas DataFrame
        """
        conn = sqlite3.connect(self.database_path)

        try:
            dataframe.to_sql(
                name=self.table_name,
                con=conn,
                if_exists=self.if_exists,
                index=False,
                **self.to_sql_kwargs
            )

        finally:
            conn.close()
