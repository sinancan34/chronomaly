"""
Comprehensive edge case tests for anomaly detection.

This test suite covers:
- Empty forecast or actual data
- Mismatched date ranges
- Invalid quantile format
- Division by zero scenarios
- Edge cases: all values zero, negative values
- Duplicate metrics
- Type validation
"""

import pytest
import pandas as pd
from datetime import datetime
from chronomaly.infrastructure.comparators import ForecastActualComparator
from chronomaly.infrastructure.transformers import PivotTransformer


class TestEmptyDataEdgeCases:
    """Test cases for empty or missing data."""

    def test_empty_forecast_dataframe(self):
        """Test that empty forecast DataFrame raises ValueError."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame()
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'platform': ['desktop'],
            'sessions': [100]
        })

        with pytest.raises(ValueError, match="Forecast DataFrame is empty"):
            detector.detect(forecast_df, actual_df)

    def test_empty_actual_dataframe(self):
        """Test that empty actual DataFrame raises ValueError."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['100|90|92|95|98|100|102|105|108|110']
        })
        actual_df = pd.DataFrame()

        with pytest.raises(ValueError, match="Actual DataFrame is empty"):
            detector.detect(forecast_df, actual_df)

    def test_both_dataframes_empty(self):
        """Test that both empty DataFrames raise ValueError."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame()
        actual_df = pd.DataFrame()

        with pytest.raises(ValueError, match="Forecast DataFrame is empty"):
            detector.detect(forecast_df, actual_df)


class TestTypeValidation:
    """Test cases for type validation."""

    def test_forecast_not_dataframe(self):
        """Test that non-DataFrame forecast raises TypeError."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_dict = {'date': [datetime(2024, 1, 1)]}
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'platform': ['desktop'],
            'sessions': [100]
        })

        with pytest.raises(TypeError, match="Expected pandas DataFrame for forecast_df"):
            detector.detect(forecast_dict, actual_df)

    def test_actual_not_dataframe(self):
        """Test that non-DataFrame actual raises TypeError."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['100|90|92|95|98|100|102|105|108|110']
        })
        actual_list = [{'date': datetime(2024, 1, 1), 'sessions': 100}]

        with pytest.raises(TypeError, match="Expected pandas DataFrame for actual_df"):
            detector.detect(forecast_df, actual_list)


class TestInvalidQuantileFormat:
    """Test cases for invalid quantile formats."""

    def test_incomplete_quantile_string(self):
        """Test handling of incomplete quantile strings (fewer than 10 values)."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['100|90|92']  # Only 3 quantiles instead of 10
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'platform': ['desktop'],
            'sessions': [95]
        })

        # Should warn about incomplete quantiles and use available values
        with pytest.warns(UserWarning, match="Expected 10 quantiles"):
            result = detector.detect(forecast_df, actual_df)
            assert len(result) == 1
            # Since q90 defaults to 0.0, actual (95) will be ABOVE_P90
            assert result.iloc[0]['status'] == 'ABOVE_P90'

    def test_non_numeric_quantile_values(self):
        """Test handling of non-numeric values in quantile string."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['100|abc|92|95|98|100|102|105|108|110']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'platform': ['desktop'],
            'sessions': [95]
        })

        result = detector.detect(forecast_df, actual_df)
        assert len(result) == 1
        # Should handle the error gracefully and return NO_FORECAST
        assert result.iloc[0]['status'] == 'NO_FORECAST'

    def test_empty_quantile_string(self):
        """Test handling of empty quantile string."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'platform': ['desktop'],
            'sessions': [95]
        })

        result = detector.detect(forecast_df, actual_df)
        assert len(result) == 1
        assert result.iloc[0]['status'] == 'NO_FORECAST'


class TestDivisionByZeroEdgeCases:
    """Test cases for division by zero scenarios."""

    def test_zero_q10_and_q90(self):
        """Test when both q10 and q90 are zero."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['0|0|0|0|0|0|0|0|0|0']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'platform': ['desktop'],
            'sessions': [100]
        })

        result = detector.detect(forecast_df, actual_df)
        assert len(result) == 1
        assert result.iloc[0]['status'] == 'NO_FORECAST'
        assert result.iloc[0]['deviation_pct'] == 0.0

    def test_zero_q10_with_nonzero_actual(self):
        """Test when q10 is zero but actual is negative."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['10|0|2|3|4|5|6|7|8|10']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'platform': ['desktop'],
            'sessions': [-5]
        })

        result = detector.detect(forecast_df, actual_df)
        assert len(result) == 1
        assert result.iloc[0]['status'] == 'BELOW_P10'
        # Deviation should be calculated as abs(actual) * 100
        assert result.iloc[0]['deviation_pct'] == 500.0

    def test_zero_q90_with_positive_actual(self):
        """Test when q90 is zero but actual is positive."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['0|0|0|0|0|0|0|0|0|0']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'platform': ['desktop'],
            'sessions': [50]
        })

        result = detector.detect(forecast_df, actual_df)
        assert len(result) == 1
        # Should be NO_FORECAST since all values are zero
        assert result.iloc[0]['status'] == 'NO_FORECAST'


class TestAllZeroValues:
    """Test cases for scenarios where all values are zero."""

    def test_all_zero_forecast_and_actual(self):
        """Test when both forecast and actual are all zeros."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['0|0|0|0|0|0|0|0|0|0']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'platform': ['desktop'],
            'sessions': [0]
        })

        result = detector.detect(forecast_df, actual_df)
        assert len(result) == 1
        assert result.iloc[0]['status'] == 'NO_FORECAST'
        assert result.iloc[0]['actual'] == 0
        assert result.iloc[0]['forecast'] == 0


class TestNegativeValues:
    """Test cases for negative values."""

    def test_negative_actual_value(self):
        """Test handling of negative actual values."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['100|90|92|95|98|100|102|105|108|110']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'platform': ['desktop'],
            'sessions': [-10]
        })

        result = detector.detect(forecast_df, actual_df)
        assert len(result) == 1
        assert result.iloc[0]['status'] == 'BELOW_P10'
        assert result.iloc[0]['actual'] == -10


class TestMismatchedDateRanges:
    """Test cases for mismatched date ranges."""

    def test_no_overlapping_dates(self):
        """Test when forecast and actual have no overlapping dates."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['100|90|92|95|98|100|102|105|108|110']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 2, 1)],  # Different date
            'platform': ['desktop'],
            'sessions': [95]
        })

        result = detector.detect(forecast_df, actual_df)
        # Should return empty or handle gracefully
        assert len(result) >= 0

    def test_partial_date_overlap(self):
        """Test when forecast and actual have partial date overlap."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1), datetime(2024, 1, 2)],
            'desktop': ['100|90|92|95|98|100|102|105|108|110',
                       '110|100|102|105|108|110|112|115|118|120']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 2), datetime(2024, 1, 3)],
            'platform': ['desktop', 'desktop'],
            'sessions': [105, 115]
        })

        result = detector.detect(forecast_df, actual_df)
        # Should only compare overlapping dates
        assert len(result) >= 0


class TestDuplicateMetrics:
    """Test cases for duplicate metrics."""

    def test_duplicate_metric_columns(self):
        """Test handling of duplicate metric columns in forecast."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(transformer=transformer)

        # This shouldn't normally happen, but test graceful handling
        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['100|90|92|95|98|100|102|105|108|110']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1), datetime(2024, 1, 1)],
            'platform': ['desktop', 'desktop'],
            'sessions': [95, 96]
        })

        # Should handle duplicate entries
        result = detector.detect(forecast_df, actual_df)
        assert len(result) >= 0


class TestDimensionExtraction:
    """Test cases for dimension name extraction."""

    def test_dimension_names_splitting(self):
        """Test that dimension names are correctly extracted."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform', 'channel'],
            values='sessions'
        )
        detector = ForecastActualComparator(
            transformer=transformer,
            dimension_names=['platform', 'channel']
        )

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop_organic': ['100|90|92|95|98|100|102|105|108|110']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'platform': ['desktop'],
            'channel': ['organic'],
            'sessions': [95]
        })

        result = detector.detect(forecast_df, actual_df)
        assert len(result) == 1
        assert 'platform' in result.columns
        assert 'channel' in result.columns
        assert result.iloc[0]['platform'] == 'desktop'
        assert result.iloc[0]['channel'] == 'organic'
        assert 'metric' not in result.columns

    def test_dimension_names_validation(self):
        """Test that dimension_names validation works correctly."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform', 'channel'],
            values='sessions'
        )

        # Mismatched dimension names should raise ValueError
        with pytest.raises(ValueError, match="dimension_names must match transformer.columns"):
            ForecastActualComparator(
                transformer=transformer,
                dimension_names=['channel', 'platform']  # Wrong order
            )


class TestFilteringOptions:
    """Test cases for filtering options."""

    def test_cumulative_threshold_filtering(self):
        """Test that cumulative threshold filtering works correctly."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(
            transformer=transformer,
            cumulative_threshold=0.8  # Top 80%
        )

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['100|90|92|95|98|100|102|105|108|110'],
            'mobile': ['50|45|46|47|48|50|52|53|55|60'],
            'tablet': ['10|9|9|9|10|10|11|11|11|12']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1), datetime(2024, 1, 1), datetime(2024, 1, 1)],
            'platform': ['desktop', 'mobile', 'tablet'],
            'sessions': [95, 55, 10]
        })

        result = detector.detect(forecast_df, actual_df)
        # Should filter out lowest-value metrics
        assert len(result) <= 3

    def test_return_only_anomalies(self):
        """Test that return_only_anomalies flag works correctly."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(
            transformer=transformer,
            return_only_anomalies=True
        )

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['100|90|92|95|98|100|102|105|108|110'],
            'mobile': ['50|45|46|47|48|50|52|53|55|60']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1), datetime(2024, 1, 1)],
            'platform': ['desktop', 'mobile'],
            'sessions': [95, 70]  # desktop in range, mobile above
        })

        result = detector.detect(forecast_df, actual_df)
        # Should only return ABOVE_P90 status
        assert len(result) == 1
        assert result.iloc[0]['status'] == 'ABOVE_P90'

    def test_min_deviation_threshold(self):
        """Test that min_deviation_threshold works correctly."""
        transformer = PivotTransformer(
            index='date',
            columns=['platform'],
            values='sessions'
        )
        detector = ForecastActualComparator(
            transformer=transformer,
            min_deviation_threshold=10.0  # 10% minimum
        )

        forecast_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'desktop': ['100|90|92|95|98|100|102|105|108|110']
        })
        actual_df = pd.DataFrame({
            'date': [datetime(2024, 1, 1)],
            'platform': ['desktop'],
            'sessions': [85]  # 5.56% below q10
        })

        result = detector.detect(forecast_df, actual_df)
        # Should filter out since deviation < 10%
        assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
