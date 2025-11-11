"""
Tests for workflow orchestrators.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock
from chronomaly.application.workflows import AnomalyDetectionWorkflow, ForecastWorkflow


class TestAnomalyDetectionWorkflow:
    """Tests for AnomalyDetectionWorkflow"""

    def test_basic_workflow_execution(self):
        """Test basic workflow execution without transformers."""
        # Create mock components
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric_a': ['100|90|92|95|98|100|102|105|108|110']
        })

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['metric_a'],
            'value': [95]
        })

        mock_detector = Mock()
        mock_detector.detect.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['metric_a'],
            'status': ['IN_RANGE']
        })

        mock_writer = Mock()

        # Create workflow
        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer
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
        """Test workflow execution with transformers at different stages."""
        # Create mock components
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric_a': ['100|90|92|95|98|100|102|105|108|110']
        })

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['metric_a'],
            'value': [95]
        })

        mock_detector = Mock()
        mock_detector.detect.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['metric_a'],
            'status': ['IN_RANGE']
        })

        mock_writer = Mock()

        # Create mock transformer
        mock_transformer = Mock()
        mock_transformer.filter = Mock(side_effect=lambda df: df)

        # Create workflow with transformers
        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
            transformers={
                'after_detection': [mock_transformer]
            }
        )

        # Execute
        result = workflow.run()

        # Verify transformer was called
        mock_transformer.filter.assert_called_once()

    def test_workflow_invalid_transformer_stage_raises_error(self):
        """Test that invalid transformer stage raises ValueError."""
        mock_forecast_reader = Mock()
        mock_actual_reader = Mock()
        mock_detector = Mock()
        mock_writer = Mock()
        mock_transformer = Mock()

        # Should raise ValueError for invalid stage
        with pytest.raises(ValueError, match="Invalid transformer stage"):
            AnomalyDetectionWorkflow(
                forecast_reader=mock_forecast_reader,
                actual_reader=mock_actual_reader,
                anomaly_detector=mock_detector,
                data_writer=mock_writer,
                transformers={
                    'invalid_stage': [mock_transformer]
                }
            )

    def test_workflow_empty_forecast_raises_error(self):
        """Test that empty forecast data raises ValueError."""
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame()  # Empty

        mock_actual_reader = Mock()
        mock_detector = Mock()
        mock_writer = Mock()

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer
        )

        with pytest.raises(ValueError, match="Forecast reader returned empty dataset"):
            workflow.run()

    def test_workflow_empty_actual_raises_error(self):
        """Test that empty actual data raises ValueError."""
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric_a': ['100|90|92|95|98|100|102|105|108|110']
        })

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame()  # Empty

        mock_detector = Mock()
        mock_writer = Mock()

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer
        )

        with pytest.raises(ValueError, match="Actual reader returned empty dataset"):
            workflow.run()

    def test_workflow_empty_detection_result_raises_error(self):
        """Test that empty detection result raises ValueError."""
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric_a': ['100|90|92|95|98|100|102|105|108|110']
        })

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['metric_a'],
            'value': [95]
        })

        mock_detector = Mock()
        mock_detector.detect.return_value = pd.DataFrame()  # Empty

        mock_writer = Mock()

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer
        )

        with pytest.raises(ValueError, match="Anomaly detector returned empty results"):
            workflow.run()

    def test_run_without_output(self):
        """Test run_without_output method."""
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric_a': ['100|90|92|95|98|100|102|105|108|110']
        })

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['metric_a'],
            'value': [95]
        })

        mock_detector = Mock()
        mock_detector.detect.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['metric_a'],
            'status': ['IN_RANGE']
        })

        mock_writer = Mock()

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer
        )

        # Execute without writing
        result = workflow.run_without_output()

        # Verify writer was NOT called
        assert result is not None
        mock_writer.write.assert_not_called()

    def test_transformer_with_format_method(self):
        """Test that transformers with .format() method work correctly."""
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric_a': ['100|90|92|95|98|100|102|105|108|110']
        })

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['metric_a'],
            'value': [95]
        })

        mock_detector = Mock()
        mock_detector.detect.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['metric_a'],
            'status': ['IN_RANGE']
        })

        mock_writer = Mock()

        # Create mock formatter with .format() method (but no .filter())
        mock_formatter = Mock(spec=['format'])
        mock_formatter.format = Mock(side_effect=lambda df: df)

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
            transformers={
                'after_detection': [mock_formatter]
            }
        )

        workflow.run()

        # Verify formatter.format() was called
        mock_formatter.format.assert_called_once()

    def test_transformer_callable(self):
        """Test that callable transformers work correctly."""
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric_a': ['100|90|92|95|98|100|102|105|108|110']
        })

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['metric_a'],
            'value': [95]
        })

        mock_detector = Mock()
        mock_detector.detect.return_value = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['metric_a'],
            'status': ['IN_RANGE']
        })

        mock_writer = Mock()

        # Create callable transformer
        transformer_called = []

        def callable_transformer(df):
            transformer_called.append(True)
            return df

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
            transformers={
                'after_detection': [callable_transformer]
            }
        )

        workflow.run()

        # Verify callable was invoked
        assert len(transformer_called) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
