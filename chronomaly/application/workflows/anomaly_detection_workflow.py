"""
Anomaly detection workflow orchestrator.
"""

import pandas as pd
from typing import Optional
from ...infrastructure.data.readers.base import DataReader
from ...infrastructure.comparators.base import AnomalyDetector
from ...infrastructure.data.writers.base import DataWriter


class AnomalyDetectionWorkflow:
    """
    Main orchestrator class for the anomaly detection workflow.

    This class coordinates the entire anomaly detection workflow:
    1. Load forecast data from source
    2. Load actual data from source
    3. Detect anomalies by comparing forecast vs actual
    4. Write results to output

    Args:
        forecast_reader: Data reader instance for forecast data
        actual_reader: Data reader instance for actual data
        anomaly_detector: Anomaly detector instance (e.g., ForecastActualComparator)
        data_writer: Data writer instance for anomaly results
    """

    def __init__(
        self,
        forecast_reader: DataReader,
        actual_reader: DataReader,
        anomaly_detector: AnomalyDetector,
        data_writer: DataWriter
    ):
        self.forecast_reader = forecast_reader
        self.actual_reader = actual_reader
        self.anomaly_detector = anomaly_detector
        self.data_writer = data_writer

    def run(self) -> pd.DataFrame:
        """
        Execute the complete anomaly detection workflow.

        Returns:
            pd.DataFrame: The anomaly detection results

        Raises:
            ValueError: If loaded data is empty or incompatible
        """
        # Step 1: Load forecast data
        forecast_df = self.forecast_reader.load()

        # Validate forecast data
        if forecast_df is None or forecast_df.empty:
            raise ValueError(
                "Forecast reader returned empty dataset. Cannot proceed with anomaly detection."
            )

        # Step 2: Load actual data
        actual_df = self.actual_reader.load()

        # Validate actual data
        if actual_df is None or actual_df.empty:
            raise ValueError(
                "Actual reader returned empty dataset. Cannot proceed with anomaly detection."
            )

        # Step 3: Detect anomalies
        anomaly_df = self.anomaly_detector.detect(
            forecast_df=forecast_df,
            actual_df=actual_df
        )

        # Validate anomaly detection results
        if anomaly_df is None or anomaly_df.empty:
            raise ValueError(
                "Anomaly detector returned empty results. Check your data and configuration."
            )

        # Step 4: Write results to output
        self.data_writer.write(anomaly_df)

        return anomaly_df

    def run_without_output(self) -> pd.DataFrame:
        """
        Execute anomaly detection workflow without writing to output.

        Useful for testing or when you want to inspect results before writing.

        Returns:
            pd.DataFrame: The anomaly detection results

        Raises:
            ValueError: If loaded data is empty or incompatible
        """
        # Step 1: Load forecast data
        forecast_df = self.forecast_reader.load()

        # Validate forecast data
        if forecast_df is None or forecast_df.empty:
            raise ValueError(
                "Forecast reader returned empty dataset. Cannot proceed with anomaly detection."
            )

        # Step 2: Load actual data
        actual_df = self.actual_reader.load()

        # Validate actual data
        if actual_df is None or actual_df.empty:
            raise ValueError(
                "Actual reader returned empty dataset. Cannot proceed with anomaly detection."
            )

        # Step 3: Detect anomalies
        anomaly_df = self.anomaly_detector.detect(
            forecast_df=forecast_df,
            actual_df=actual_df
        )

        # Validate anomaly detection results
        if anomaly_df is None or anomaly_df.empty:
            raise ValueError(
                "Anomaly detector returned empty results. Check your data and configuration."
            )

        return anomaly_df
