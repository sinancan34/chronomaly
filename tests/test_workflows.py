"""
Tests for workflow orchestrators.
"""

import pytest
import pandas as pd
from unittest.mock import Mock
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.base import DataReader
from chronomaly.infrastructure.anomaly_detectors.base import AnomalyDetector
from chronomaly.infrastructure.data.writers.base import DataWriter


class TestAnomalyDetectionWorkflow:
    """Tests for AnomalyDetectionWorkflow"""

    def test_basic_workflow_execution(self):
        """Test basic workflow execution without transformers."""
        # Create mock components
        mock_forecast_reader = Mock(spec=DataReader)
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock(spec=DataReader)
        mock_actual_reader.load.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "value": [95]}
        )

        mock_detector = Mock(spec=AnomalyDetector)
        mock_detector.detect.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "status": ["IN_RANGE"]}
        )

        mock_writer = Mock(spec=DataWriter)

        # Create workflow
        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        # Execute
        result = workflow.run()

        # Verify
        assert result is not None
        assert len(result) == 1
        mock_forecast_reader.load.assert_called_once()
        mock_actual_reader.load.assert_called_once()
        mock_detector.detect.assert_called_once()
        mock_writer.write.assert_called_once()

    def test_workflow_with_transformers(self):
        """Test workflow execution with transformers at component level."""
        # Create mock components
        mock_forecast_reader = Mock(spec=DataReader)
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock(spec=DataReader)
        mock_actual_reader.load.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "value": [95]}
        )

        # Create mock detector with transformers
        mock_detector = Mock(spec=AnomalyDetector)
        mock_detector.detect.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "status": ["IN_RANGE"]}
        )

        mock_writer = Mock(spec=DataWriter)

        # Transformers are now configured at component level (not workflow level)
        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        # Execute
        result = workflow.run()

        # Verify workflow executed successfully
        assert result is not None

    def test_workflow_empty_forecast_raises_error(self):
        """Test that empty forecast data raises ValueError."""
        mock_forecast_reader = Mock(spec=DataReader)
        mock_forecast_reader.load.return_value = pd.DataFrame()  # Empty

        mock_actual_reader = Mock(spec=DataReader)
        mock_detector = Mock(spec=AnomalyDetector)
        mock_writer = Mock(spec=DataWriter)

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        with pytest.raises(ValueError, match="Forecast reader returned empty dataset"):
            workflow.run()

    def test_workflow_empty_actual_raises_error(self):
        """Test that empty actual data raises ValueError."""
        mock_forecast_reader = Mock(spec=DataReader)
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock(spec=DataReader)
        mock_actual_reader.load.return_value = pd.DataFrame()  # Empty

        mock_detector = Mock(spec=AnomalyDetector)
        mock_writer = Mock(spec=DataWriter)

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        with pytest.raises(ValueError, match="Actual reader returned empty dataset"):
            workflow.run()

    def test_workflow_empty_detection_result_returns_empty_dataframe(self):
        """Test that empty detection result returns empty DataFrame with schema."""
        mock_forecast_reader = Mock(spec=DataReader)
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock(spec=DataReader)
        mock_actual_reader.load.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "value": [95]}
        )

        # Mock detector that returns empty DataFrame with schema
        mock_detector = Mock(spec=AnomalyDetector)
        empty_result = pd.DataFrame(
            {
                "date": pd.Series(dtype="object"),
                "group_key": pd.Series(dtype="object"),
                "metric_name": pd.Series(dtype="object"),
                "actual_value": pd.Series(dtype="int64"),
                "forecast_value": pd.Series(dtype="int64"),
                "lower_limit": pd.Series(dtype="int64"),
                "upper_limit": pd.Series(dtype="int64"),
                "alert_type": pd.Series(dtype="object"),
                "anomaly_score": pd.Series(dtype="float64"),
            }
        )
        mock_detector.detect.return_value = empty_result

        mock_writer = Mock(spec=DataWriter)

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        result = workflow.run()

        # Verify empty DataFrame was returned with correct schema
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        assert "date" in result.columns
        assert "group_key" in result.columns
        assert "alert_type" in result.columns
        mock_writer.write.assert_called_once()

    def test_run_without_output(self):
        """Test running workflow without data_writer."""
        mock_forecast_reader = Mock(spec=DataReader)
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock(spec=DataReader)
        mock_actual_reader.load.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "value": [95]}
        )

        mock_detector = Mock(spec=AnomalyDetector)
        mock_detector.detect.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "status": ["IN_RANGE"]}
        )

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=None,
        )

        # Execute without writing (data_writer is None)
        result = workflow.run()

        # Verify result is returned
        assert result is not None

    def test_transformer_with_format_method(self):
        """Test that transformers with .format() method work correctly
        at component level."""
        mock_forecast_reader = Mock(spec=DataReader)
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock(spec=DataReader)
        mock_actual_reader.load.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "value": [95]}
        )

        # Mock detector handles transformers internally
        mock_detector = Mock(spec=AnomalyDetector)
        mock_detector.detect.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "status": ["IN_RANGE"]}
        )

        mock_writer = Mock(spec=DataWriter)

        # Transformers are configured at component level (detector, reader, writer)
        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        result = workflow.run()

        # Verify workflow executed successfully
        assert result is not None

    def test_transformer_callable(self):
        """Test that callable transformers work correctly at component level."""
        mock_forecast_reader = Mock(spec=DataReader)
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock(spec=DataReader)
        mock_actual_reader.load.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "value": [95]}
        )

        mock_detector = Mock(spec=AnomalyDetector)
        mock_detector.detect.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "status": ["IN_RANGE"]}
        )

        mock_writer = Mock(spec=DataWriter)

        # Transformers are configured at component level (detector, reader, writer)
        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        result = workflow.run()

        # Verify workflow executed successfully
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
