"""
Anomaly detection workflow orchestrator.
"""

import pandas as pd
from typing import Optional, List, Dict, Callable
from ...infrastructure.data.readers.base import DataReader
from ...infrastructure.anomaly_detectors.base import AnomalyDetector
from ...infrastructure.data.writers.base import DataWriter


class AnomalyDetectionWorkflow:
    """
    Main orchestrator class for the anomaly detection workflow.

    This workflow supports flexible DataFrame transformers at ANY stage:
    1. Load forecast data
    2. Apply transformers (after_forecast_read) - Optional
    3. Load actual data
    4. Apply transformers (after_actual_read) - Optional
    5. Detect anomalies
    6. Apply transformers (after_detection) - Optional
    7. Write results

    Args:
        forecast_reader: Data reader for forecast data
        actual_reader: Data reader for actual data
        anomaly_detector: Anomaly detector instance
        data_writer: Data writer for results
        transformers: Dict of transformer lists for different stages

    Transformer Stages:
        'after_forecast_read': Applied after loading forecast data
        'after_actual_read': Applied after loading actual data
        'after_detection': Applied after anomaly detection
        'before_write': Applied just before writing (rarely needed)

    Example - Simple (backward compatible):
        workflow = AnomalyDetectionWorkflow(
            forecast_reader=reader,
            actual_reader=reader,
            anomaly_detector=detector,
            data_writer=writer
        )

    Example - With transformers:
        from chronomaly.infrastructure.transformers.filters import (
            CumulativeThresholdFilter, ValueFilter
        )
        from chronomaly.infrastructure.transformers.formatters import (
            PercentageFormatter
        )

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=reader,
            actual_reader=reader,
            anomaly_detector=detector,
            data_writer=writer,
            transformers={
                'after_detection': [
                    ValueFilter('status', ['BELOW_LOWER', 'ABOVE_UPPER']),
                    PercentageFormatter('deviation_pct')
                ]
            }
        )
    """

    def __init__(
        self,
        forecast_reader: DataReader,
        actual_reader: DataReader,
        anomaly_detector: AnomalyDetector,
        data_writer: DataWriter,
        transformers: Optional[Dict[str, List[Callable]]] = None
    ):
        self.forecast_reader = forecast_reader
        self.actual_reader = actual_reader
        self.anomaly_detector = anomaly_detector
        self.data_writer = data_writer
        self.transformers = transformers or {}

        # Validate transformer stages
        valid_stages = {'after_forecast_read', 'after_actual_read', 'after_detection', 'before_write'}
        for stage in self.transformers.keys():
            if stage not in valid_stages:
                raise ValueError(f"Invalid transformer stage: {stage}. Must be one of {valid_stages}")

    def _apply_transformers(self, df: pd.DataFrame, stage: str) -> pd.DataFrame:
        """
        Apply transformers for a specific stage.

        Args:
            df: DataFrame to transform
            stage: Stage name ('after_forecast_read', 'after_actual_read', etc.)

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

    def _execute_detection(self) -> pd.DataFrame:
        """
        Execute anomaly detection with flexible transformer pipeline.

        Pipeline:
        1. Load forecast data
        2. Apply transformers (after_forecast_read)
        3. Load actual data
        4. Apply transformers (after_actual_read)
        5. Detect anomalies
        6. Apply transformers (after_detection)
        7. Return results

        Returns:
            pd.DataFrame: Anomaly detection results

        Raises:
            ValueError: If data is empty or incompatible
        """
        # Step 1: Load forecast data
        forecast_df = self.forecast_reader.load()
        if forecast_df is None or forecast_df.empty:
            raise ValueError("Forecast reader returned empty dataset.")

        # Step 2: Apply forecast transformers
        forecast_df = self._apply_transformers(forecast_df, 'after_forecast_read')

        # Step 3: Load actual data
        actual_df = self.actual_reader.load()
        if actual_df is None or actual_df.empty:
            raise ValueError("Actual reader returned empty dataset.")

        # Step 4: Apply actual transformers
        actual_df = self._apply_transformers(actual_df, 'after_actual_read')

        # Step 5: Detect anomalies
        anomaly_df = self.anomaly_detector.detect(
            forecast_df=forecast_df,
            actual_df=actual_df
        )

        if anomaly_df is None or anomaly_df.empty:
            raise ValueError("Anomaly detector returned empty results.")

        # Step 6: Apply detection result transformers
        anomaly_df = self._apply_transformers(anomaly_df, 'after_detection')

        # Step 7: Apply before-write transformers (optional)
        anomaly_df = self._apply_transformers(anomaly_df, 'before_write')

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
        return self._execute_detection()
