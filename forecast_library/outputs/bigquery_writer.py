"""
BigQuery output writer implementation.
"""

import pandas as pd
from typing import Optional
from google.cloud import bigquery
from .base import OutputWriter


class BigQueryOutputWriter(OutputWriter):
    """
    Output writer implementation for Google BigQuery.

    Args:
        service_account_file: Path to the service account JSON file for authentication
        project: GCP project ID
        dataset: BigQuery dataset name
        table: BigQuery table name
        create_disposition: Specifies behavior if table doesn't exist
                           (default: CREATE_IF_NEEDED)
        write_disposition: Specifies behavior if table exists
                          (default: WRITE_TRUNCATE - replaces existing data)
    """

    def __init__(
        self,
        service_account_file: Optional[str] = None,
        project: Optional[str] = None,
        dataset: str = None,
        table: str = None,
        create_disposition: str = 'CREATE_IF_NEEDED',
        write_disposition: str = 'WRITE_TRUNCATE'
    ):
        if dataset is None:
            raise ValueError("dataset parameter is required")
        if table is None:
            raise ValueError("table parameter is required")

        self.service_account_file = service_account_file
        self.project = project
        self.dataset = dataset
        self.table = table
        self.create_disposition = create_disposition
        self.write_disposition = write_disposition
        self._client = None

    def _get_client(self) -> bigquery.Client:
        """
        Get or create BigQuery client.

        Returns:
            bigquery.Client: Initialized BigQuery client
        """
        if self._client is None:
            if self.service_account_file:
                self._client = bigquery.Client.from_service_account_json(
                    self.service_account_file,
                    project=self.project
                )
            else:
                self._client = bigquery.Client(project=self.project)
        return self._client

    def write(self, dataframe: pd.DataFrame) -> None:
        """
        Write forecast results to BigQuery table.

        Args:
            dataframe: The forecast results as a pandas DataFrame
        """
        client = self._get_client()

        # Get dataset and table references
        bigquery_dataset = client.dataset(self.dataset)
        bigquery_table = bigquery_dataset.table(self.table)

        # Configure load job
        bigquery_job_config = bigquery.LoadJobConfig()

        # Set create disposition
        if self.create_disposition == 'CREATE_IF_NEEDED':
            bigquery_job_config.create_disposition = bigquery.CreateDisposition.CREATE_IF_NEEDED
        elif self.create_disposition == 'CREATE_NEVER':
            bigquery_job_config.create_disposition = bigquery.CreateDisposition.CREATE_NEVER

        # Set write disposition
        if self.write_disposition == 'WRITE_TRUNCATE':
            bigquery_job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
        elif self.write_disposition == 'WRITE_APPEND':
            bigquery_job_config.write_disposition = bigquery.WriteDisposition.WRITE_APPEND
        elif self.write_disposition == 'WRITE_EMPTY':
            bigquery_job_config.write_disposition = bigquery.WriteDisposition.WRITE_EMPTY

        # Load dataframe to BigQuery
        job = client.load_table_from_dataframe(
            dataframe,
            bigquery_table,
            job_config=bigquery_job_config
        )

        # Wait for the job to complete
        job.result()
