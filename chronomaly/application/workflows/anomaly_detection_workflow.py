"""
Anomaly detection workflow orchestrator.
"""

import pandas as pd
from typing import Optional
from ...infrastructure.data.readers.base import DataReader
from ...infrastructure.anomaly_detectors.base import AnomalyDetector
from ...infrastructure.data.writers.base import DataWriter


class AnomalyDetectionWorkflow:
    """
    Main orchestrator class for the anomaly detection workflow.

    This workflow orchestrates the anomaly detection process:
    1. Load forecast data (via forecast_reader)
    2. Load actual data (via actual_reader)
    3. Detect anomalies (via anomaly_detector)
    4. Write results (via data_writer)

    Transformations should be configured at the component level:
    - forecast_reader: Use transformers={'after': [...]} for post-load transformations
    - actual_reader: Use transformers={'after': [...]} for post-load transformations
    - data_writer: Use transformers={'before': [...]} for pre-write transformations

    Args:
        forecast_reader: Data reader for forecast data
        actual_reader: Data reader for actual data
        anomaly_detector: Anomaly detector instance
        data_writer: Data writer for results (optional, if not provided
            results won't be written)
    """

    def __init__(
        self,
        forecast_reader: DataReader,
        actual_reader: DataReader,
        anomaly_detector: AnomalyDetector,
        data_writer: Optional[DataWriter] = None,
    ):
        # Validate forecast_reader
        if not isinstance(forecast_reader, DataReader):
            raise TypeError(
                f"forecast_reader must be a DataReader instance, "
                f"got {type(forecast_reader).__name__}"
            )

        # Validate actual_reader
        if not isinstance(actual_reader, DataReader):
            raise TypeError(
                f"actual_reader must be a DataReader instance, "
                f"got {type(actual_reader).__name__}"
            )

        # Validate anomaly_detector
        if not isinstance(anomaly_detector, AnomalyDetector):
            raise TypeError(
                f"anomaly_detector must be an AnomalyDetector instance, "
                f"got {type(anomaly_detector).__name__}"
            )

        # Validate data_writer (optional, but must be DataWriter if provided)
        if data_writer is not None and not isinstance(data_writer, DataWriter):
            raise TypeError(
                f"data_writer must be a DataWriter instance or None, "
                f"got {type(data_writer).__name__}"
            )

        self.forecast_reader = forecast_reader
        self.actual_reader = actual_reader
        self.anomaly_detector = anomaly_detector
        self.data_writer = data_writer

    def _execute_detection(self) -> pd.DataFrame:
        """
        Execute anomaly detection workflow.

        Pipeline:
        1. Load forecast data
        2. Load actual data
        3. Detect anomalies
        4. Return results (may be empty if no anomalies detected)

        Note: Transformations are handled by individual components (readers/writers).

        Returns:
            pd.DataFrame: Anomaly detection results (may be empty)

        Raises:
            ValueError: If data is empty or incompatible
        """
        # Step 1: Load forecast data
        forecast_df = self.forecast_reader.load()
        if forecast_df is None or forecast_df.empty:
            raise ValueError("Forecast reader returned empty dataset.")

        # Step 2: Load actual data
        actual_df = self.actual_reader.load()
        if actual_df is None or actual_df.empty:
            raise ValueError("Actual reader returned empty dataset.")

        # Step 3: Detect anomalies
        anomaly_df = self.anomaly_detector.detect(
            forecast_df=forecast_df, actual_df=actual_df
        )

        # Empty DataFrame is now a valid result (no anomalies detected)
        if anomaly_df is None:
            raise ValueError("Anomaly detector returned None instead of DataFrame.")

        return anomaly_df

    def run(self) -> pd.DataFrame:
        """
        Execute the complete anomaly detection workflow.

        Returns:
            pd.DataFrame: The anomaly detection results

        Raises:
            ValueError: If loaded data is empty or incompatible
        """
        anomaly_df = self._execute_detection()
        if self.data_writer:
            self.data_writer.write(anomaly_df)
        return anomaly_df
