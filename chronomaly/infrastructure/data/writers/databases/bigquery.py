"""
BigQuery data writer implementation.
"""

import os

import pandas as pd
from typing import Optional, Dict, List, Callable
from google.cloud import bigquery
from google.oauth2 import service_account
from ..base import DataWriter
from chronomaly.shared import TransformableMixin


class BigQueryDataWriter(DataWriter, TransformableMixin):
    """
    Data writer implementation for Google BigQuery.

    Args:
        service_account_file: Path to the service account JSON file for authentication
        project: GCP project ID
        dataset: BigQuery dataset name
        table: BigQuery table name
        create_disposition: Specifies behavior if table doesn't exist
                           (default: CREATE_IF_NEEDED)
        write_disposition: Specifies behavior if table exists
                          (default: WRITE_TRUNCATE - replaces existing data)
        transformers: Optional dict of transformer lists to apply before/after writing
    """

    # Valid disposition values
    VALID_CREATE_DISPOSITIONS = {"CREATE_IF_NEEDED", "CREATE_NEVER"}
    VALID_WRITE_DISPOSITIONS = {"WRITE_TRUNCATE", "WRITE_APPEND", "WRITE_EMPTY"}

    def __init__(
        self,
        service_account_file: str,
        project: str,
        dataset: str,
        table: str,
        create_disposition: str = "CREATE_IF_NEEDED",
        write_disposition: str = "WRITE_TRUNCATE",
        transformers: Optional[Dict[str, List[Callable]]] = None,
    ):
        # Validate service_account_file (same as BigQueryDataReader)
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

        # Validate project
        if not project or not project.strip():
            raise ValueError("'project' cannot be empty")
        self.project = project

        # Validate dataset
        if not dataset or not dataset.strip():
            raise ValueError("'dataset' cannot be empty")
        self.dataset = dataset

        # Validate table
        if not table or not table.strip():
            raise ValueError("'table' cannot be empty")
        self.table = table

        # Validate disposition parameters
        if create_disposition not in self.VALID_CREATE_DISPOSITIONS:
            raise ValueError(
                f"Invalid create_disposition: '{create_disposition}'. "
                f"Must be one of: {', '.join(sorted(self.VALID_CREATE_DISPOSITIONS))}"
            )
        if write_disposition not in self.VALID_WRITE_DISPOSITIONS:
            raise ValueError(
                f"Invalid write_disposition: '{write_disposition}'. "
                f"Must be one of: {', '.join(sorted(self.VALID_WRITE_DISPOSITIONS))}"
            )

        self.create_disposition = create_disposition
        self.write_disposition = write_disposition
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

    def write(self, dataframe: pd.DataFrame) -> None:
        """
        Write forecast results to BigQuery table.

        Args:
            dataframe: The forecast results as a pandas DataFrame

        Raises:
            RuntimeError: If the BigQuery write job fails
        """
        # Apply transformers before writing data
        dataframe = self._apply_transformers(dataframe, "before")

        # Convert all columns to string for consistent BigQuery schema
        # This prevents type mismatches between empty and non-empty DataFrames
        dataframe = dataframe.astype(str)

        client = self._get_client()

        # Construct table ID (modern API - replaces deprecated dataset().table())
        table_id = f"{self.project}.{self.dataset}.{self.table}"

        # Configure load job
        bigquery_job_config = bigquery.LoadJobConfig()

        # Set create disposition
        if self.create_disposition == "CREATE_IF_NEEDED":
            bigquery_job_config.create_disposition = (
                bigquery.CreateDisposition.CREATE_IF_NEEDED
            )
        elif self.create_disposition == "CREATE_NEVER":
            bigquery_job_config.create_disposition = (
                bigquery.CreateDisposition.CREATE_NEVER
            )

        # Set write disposition
        if self.write_disposition == "WRITE_TRUNCATE":
            bigquery_job_config.write_disposition = (
                bigquery.WriteDisposition.WRITE_TRUNCATE
            )
        elif self.write_disposition == "WRITE_APPEND":
            bigquery_job_config.write_disposition = (
                bigquery.WriteDisposition.WRITE_APPEND
            )
        elif self.write_disposition == "WRITE_EMPTY":
            bigquery_job_config.write_disposition = (
                bigquery.WriteDisposition.WRITE_EMPTY
            )

        # Load dataframe to BigQuery using table_id string
        job = client.load_table_from_dataframe(
            dataframe, table_id, job_config=bigquery_job_config
        )

        # Wait for the job to complete with proper error handling
        try:
            job.result()
        except Exception as e:
            raise RuntimeError(
                f"Failed to write to BigQuery table {self.dataset}.{self.table}. "
                f"Error: {str(e)}"
            ) from e
