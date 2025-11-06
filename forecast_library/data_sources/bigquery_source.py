"""
BigQuery data source implementation.
"""

import pandas as pd
from typing import Optional
from google.cloud import bigquery
from google.oauth2 import service_account
from .base import DataSource


class BigQueryDataSource(DataSource):
    """
    Data source implementation for Google BigQuery.

    Args:
        service_account_file: Path to the service account JSON file
        project: GCP project ID
        query: SQL query to execute
        date_column: Name of the date column (will be parsed as datetime)
    """

    def __init__(
        self,
        service_account_file: str,
        project: str,
        query: str,
        date_column: Optional[str] = None
    ):
        self.service_account_file = service_account_file
        self.project = project
        self.query = query
        self.date_column = date_column
        self._client = None

    def _get_client(self) -> bigquery.Client:
        """
        Create and return BigQuery client.

        Returns:
            bigquery.Client: Initialized BigQuery client
        """
        if self._client is None:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file
            )

            self._client = bigquery.Client(
                credentials=credentials,
                project=self.project
            )

        return self._client

    def load(self) -> pd.DataFrame:
        """
        Load data from BigQuery using the provided query.

        Returns:
            pd.DataFrame: The loaded data
        """
        client = self._get_client()

        query_job = client.query(self.query)
        result = query_job.result()
        df = result.to_dataframe()

        if self.date_column and self.date_column in df.columns:
            df[self.date_column] = pd.to_datetime(df[self.date_column])

        return df
