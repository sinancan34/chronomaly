"""
BigQuery data reader implementation.
"""

import pandas as pd
import os
import re
from typing import Optional, Dict, List, Callable
from google.cloud import bigquery
from google.oauth2 import service_account
from ..base import DataReader
from chronomaly.shared import TransformableMixin


class BigQueryDataReader(DataReader, TransformableMixin):
    """
    Data reader implementation for Google BigQuery.

    Args:
        service_account_file: Path to the service account JSON file
        project: GCP project ID
        query: SQL query to execute
        date_column: Name of the date column (required, will be parsed as datetime)
        transformers: Optional dict of transformer lists to apply after loading data

    Security Notes:
        - The query parameter is executed directly on BigQuery. Ensure queries
          are from trusted sources and properly validated to prevent SQL injection.
        - Never pass user-controlled input directly into queries without validation.
        - Consider using parameterized queries for user inputs.
    """

    def __init__(
        self,
        service_account_file: str,
        project: str,
        query: str,
        date_column: str,
        transformers: Optional[Dict[str, List[Callable]]] = None,
    ):
        if not service_account_file or not service_account_file.strip():
            raise ValueError("'service_account_file' cannot be empty")

        abs_path = os.path.abspath(service_account_file)
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(f"'service_account_file' not found: {abs_path}")

        if not os.access(abs_path, os.R_OK):
            raise PermissionError(f"'service_account_file' is not readable: {abs_path}")

        if not abs_path.endswith(".json"):
            raise ValueError(
                "'service_account_file' must be a JSON file (.json extension)"
            )
        self.service_account_file = abs_path

        if not project or not project.strip():
            raise ValueError("'project' cannot be empty")
        self.project = project

        if not query or not query.strip():
            raise ValueError("'query' cannot be empty")
        self.query = query

        if not date_column or not date_column.strip():
            raise ValueError("'date_column' cannot be empty")
        self.date_column = date_column

        self._client = None

        self.transformers = transformers or {}

    def _get_client(self) -> bigquery.Client:
        """
        Create and return BigQuery client.

        Returns:
            bigquery.Client: Initialized BigQuery client
        """
        if self._client is None:
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_file
                )

                self._client = bigquery.Client(
                    credentials=credentials, project=self.project
                )
            except Exception as e:
                raise RuntimeError(f"Failed to create BigQuery client: {str(e)}") from e

        return self._client

    def load(self) -> pd.DataFrame:
        """
        Load data from BigQuery using the provided query.

        Returns:
            pd.DataFrame: The loaded data

        Raises:
            ValueError: If query returns no data or date_column is invalid
            RuntimeError: If BigQuery query fails
        """

        try:
            client = self._get_client()

            query_job = client.query(self.query)
            result = query_job.result()
            df = result.to_dataframe()

        except Exception as e:
            # Provide context for various error types
            error_msg = f"BigQuery query failed: {str(e)}"
            if "Syntax error" in str(e):
                error_msg = f"SQL syntax error in query: {str(e)}"
            elif "Not found" in str(e):
                error_msg = f"Table or dataset not found: {str(e)}"
            elif "Access Denied" in str(e) or "Permission" in str(e):
                error_msg = (
                    f"Permission denied. Check service account permissions: {str(e)}"
                )

            raise RuntimeError(error_msg) from e

        if df.empty:
            raise ValueError(
                "'query' returned no data. Please check your query and data source."
            )

        if self.date_column not in df.columns:
            raise ValueError(
                f"date_column '{self.date_column}' not found in query results. "
                f"Available columns: {list(df.columns)}"
            )

        try:
            df[self.date_column] = pd.to_datetime(df[self.date_column])
        except Exception as e:
            raise ValueError(
                f"Failed to parse date_column '{self.date_column}' "
                f"as datetime: {str(e)}"
            ) from e

        # Apply transformers after loading data
        df = self._apply_transformers(df, "after")

        return df

    def close(self) -> None:
        """
        This should be called when done using the reader, especially in
        long-running applications to prevent resource leaks.
        """
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None

    def __enter__(self):
        """Support for context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure client is closed when used as context manager."""
        self.close()
        return False
