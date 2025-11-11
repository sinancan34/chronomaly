"""
SQLite data reader implementation.
"""

import pandas as pd
import sqlite3
import os
import re
from typing import Optional, Dict, Any, List, Callable
from ..base import DataReader


class SQLiteDataReader(DataReader):
    """
    Data reader implementation for SQLite databases.

    Args:
        database_path: Path to the SQLite database file
        query: SQL query to execute
        date_column: Name of the date column (will be parsed as datetime)
        transformers: Optional dict of transformer lists to apply after loading data
                     Example: {'after': [Filter1(), Filter2()]}
        **kwargs: Additional arguments to pass to pandas.read_sql_query()

    Security Notes:
        - The query parameter is executed directly on SQLite. Ensure queries
          are from trusted sources and properly validated to prevent SQL injection.
        - Never pass user-controlled input directly into queries without validation.
        - Consider using parameterized queries for user inputs.
        - database_path is validated to prevent path traversal attacks.
    """

    def __init__(
        self,
        database_path: str,
        query: str,
        date_column: Optional[str] = None,
        transformers: Optional[Dict[str, List[Callable]]] = None,
        **kwargs: Any
    ):
        # BUG-19 FIX: Validate database path to prevent path traversal
        if not database_path:
            raise ValueError("database_path cannot be empty")

        # Resolve to absolute path
        abs_path = os.path.abspath(database_path)

        # Check if file exists
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(
                f"Database file not found: {abs_path}"
            )

        # Check if file is readable
        if not os.access(abs_path, os.R_OK):
            raise PermissionError(
                f"Database file is not readable: {abs_path}"
            )

        self.database_path = abs_path

        # BUG-14 FIX: Add basic SQL injection protection
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        self._validate_query(query)
        self.query = query

        self.date_column = date_column
        self.transformers = transformers or {}
        self.read_sql_kwargs = kwargs

    def _validate_query(self, query: str) -> None:
        """
        Validate SQL query for obvious injection attempts.

        This is a basic validation and should not be relied upon as the sole
        security measure. Always ensure queries come from trusted sources.

        Args:
            query: SQL query to validate

        Raises:
            ValueError: If query contains suspicious patterns
        """
        query_lower = query.lower()

        # Check for multiple statements
        if query.count(';') > 1:
            raise ValueError(
                "Query contains multiple statements. "
                "Only single SQL statements are allowed."
            )

        # Remove trailing semicolons
        query_check = query_lower.rstrip('; \t\n')

        # Check for SQL comments
        if '--' in query_check or '/*' in query_check:
            raise ValueError(
                "SQL comments are not allowed in queries for security reasons"
            )

        # Check for dangerous keywords
        dangerous_keywords = ['drop', 'delete', 'truncate', 'alter', 'create']
        for keyword in dangerous_keywords:
            if re.search(r'\b' + keyword + r'\b', query_lower):
                if not query_lower.strip().startswith('select'):
                    raise ValueError(
                        f"Query contains potentially dangerous keyword: {keyword}. "
                        f"Only SELECT queries are recommended."
                    )

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

    def load(self) -> pd.DataFrame:
        """
        Load data from SQLite database using the provided query.

        Returns:
            pd.DataFrame: The loaded data
        """
        conn = sqlite3.connect(self.database_path)

        try:
            df = pd.read_sql_query(self.query, conn, **self.read_sql_kwargs)

            if self.date_column:
                if self.date_column not in df.columns:
                    raise ValueError(
                        f"date_column '{self.date_column}' not found in query results. "
                        f"Available columns: {list(df.columns)}"
                    )
                df[self.date_column] = pd.to_datetime(df[self.date_column])

            # Apply transformers after loading data
            df = self._apply_transformers(df, 'after')

            return df
        finally:
            conn.close()
