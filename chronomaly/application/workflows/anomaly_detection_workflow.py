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
        data_writer: Data writer for results (optional, if not provided results won't be written)

    Example:
        from chronomaly.infrastructure.transformers.filters import ValueFilter
        from chronomaly.infrastructure.transformers.formatters import ColumnFormatter

        # Configure transformations at component level
        forecast_reader = BigQueryDataReader(
            ...,
            transformers={'after': [ValueFilter('confidence', min_value=0.8)]}
        )

        data_writer = BigQueryDataWriter(
            ...,
            transformers={'before': [
                ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER']),
                ColumnFormatter({'deviation_pct': lambda x: f"{x:.1f}%"})
            ]}
        )

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=forecast_reader,
            actual_reader=actual_reader,
            anomaly_detector=detector,
            data_writer=data_writer
        )
    """

    def __init__(
        self,
        forecast_reader: DataReader,
        actual_reader: DataReader,
        anomaly_detector: AnomalyDetector,
        data_writer: Optional[DataWriter] = None
    ):
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
        4. Return results

        Note: Transformations are handled by individual components (readers/writers).

        Returns:
            pd.DataFrame: Anomaly detection results

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
            forecast_df=forecast_df,
            actual_df=actual_df
        )

        if anomaly_df is None or anomaly_df.empty:
            raise ValueError("Anomaly detector returned empty results.")

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
