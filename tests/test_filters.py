"""
Tests for DataFrame filters.
"""

import pytest
import pandas as pd
from chronomaly.infrastructure.transformers.filters import ValueFilter, CumulativeThresholdFilter


class TestValueFilter:
    """Tests for ValueFilter"""

    def test_value_filter_include_mode(self):
        """Test filtering with include mode."""
        df = pd.DataFrame({
            'status': ['IN_RANGE', 'BELOW_LOWER', 'ABOVE_UPPER', 'IN_RANGE'],
            'value': [100, 50, 150, 90]
        })

        filter = ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER'], mode='include')
        result = filter.filter(df)

        assert len(result) == 2
        assert all(result['status'].isin(['BELOW_LOWER', 'ABOVE_UPPER']))

    def test_value_filter_exclude_mode(self):
        """Test filtering with exclude mode."""
        df = pd.DataFrame({
            'platform': ['desktop', 'mobile', 'tablet', 'desktop'],
            'value': [100, 50, 20, 90]
        })

        filter = ValueFilter('platform', values=['tablet'], mode='exclude')
        result = filter.filter(df)

        assert len(result) == 3
        assert 'tablet' not in result['platform'].values

    def test_value_filter_numeric_min(self):
        """Test filtering with minimum value."""
        df = pd.DataFrame({
            'deviation_pct': [5.0, 10.0, 15.0, 20.0],
            'metric': ['a', 'b', 'c', 'd']
        })

        filter = ValueFilter('deviation_pct', min_value=10.0)
        result = filter.filter(df)

        assert len(result) == 3
        assert all(result['deviation_pct'] >= 10.0)

    def test_value_filter_numeric_max(self):
        """Test filtering with maximum value."""
        df = pd.DataFrame({
            'sessions': [100, 500, 1000, 5000],
            'metric': ['a', 'b', 'c', 'd']
        })

        filter = ValueFilter('sessions', max_value=1000)
        result = filter.filter(df)

        assert len(result) == 3
        assert all(result['sessions'] <= 1000)

    def test_value_filter_numeric_range(self):
        """Test filtering with both min and max values."""
        df = pd.DataFrame({
            'sessions': [50, 100, 500, 1000, 5000],
            'metric': ['a', 'b', 'c', 'd', 'e']
        })

        filter = ValueFilter('sessions', min_value=100, max_value=1000)
        result = filter.filter(df)

        assert len(result) == 3
        assert all((result['sessions'] >= 100) & (result['sessions'] <= 1000))

    def test_value_filter_combined_categorical_and_numeric(self):
        """Test filtering with both categorical values and numeric threshold."""
        df = pd.DataFrame({
            'deviation_pct': [5.0, 15.0, 20.0, 25.0, 30.0]
        })

        # First filter by values, then by min_value
        filter = ValueFilter(
            'deviation_pct',
            values=[5.0, 15.0, 20.0, 30.0],  # Keep these values
            min_value=15.0  # Then filter those >= 15.0
        )
        result = filter.filter(df)

        # Should have: 15.0, 20.0, 30.0 (values in list and >= 15.0)
        assert len(result) == 3
        assert all(result['deviation_pct'].isin([15.0, 20.0, 30.0]))
        assert all(result['deviation_pct'] >= 15.0)

    def test_value_filter_empty_dataframe(self):
        """Test filtering on empty DataFrame."""
        df = pd.DataFrame()
        filter = ValueFilter('status', values=['BELOW_LOWER'])
        result = filter.filter(df)

        assert result.empty

    def test_value_filter_missing_column(self):
        """Test filtering when column doesn't exist."""
        df = pd.DataFrame({
            'value': [100, 200, 300]
        })

        filter = ValueFilter('missing_column', values=['test'])
        result = filter.filter(df)

        # Should return copy of original DataFrame
        assert len(result) == 3
        pd.testing.assert_frame_equal(result, df)

    def test_value_filter_no_parameters_raises_error(self):
        """Test that creating filter without parameters raises error."""
        with pytest.raises(ValueError, match="At least one of 'values', 'min_value', or 'max_value' must be specified"):
            ValueFilter('column')

    def test_value_filter_invalid_mode_raises_error(self):
        """Test that invalid mode raises error."""
        with pytest.raises(ValueError, match="mode must be 'include' or 'exclude'"):
            ValueFilter('column', values=['test'], mode='invalid')

    def test_value_filter_single_value_not_list(self):
        """Test filtering with single value (not in list)."""
        df = pd.DataFrame({
            'status': ['IN_RANGE', 'BELOW_LOWER', 'ABOVE_UPPER'],
            'value': [100, 50, 150]
        })

        filter = ValueFilter('status', values='BELOW_LOWER', mode='include')
        result = filter.filter(df)

        assert len(result) == 1
        assert result.iloc[0]['status'] == 'BELOW_LOWER'


class TestCumulativeThresholdFilter:
    """Tests for CumulativeThresholdFilter"""

    def test_cumulative_threshold_basic(self):
        """Test basic cumulative threshold filtering."""
        df = pd.DataFrame({
            'metric': ['a', 'b', 'c', 'd'],
            'value': [100, 50, 30, 20]  # Total=200, cumsum=[100, 150, 180, 200]
        })

        # 95% of 200 = 190, so we need metrics totaling >= 190
        # This includes: a(100) + b(50) + c(30) + d(20) = 200
        # But cumulative 95% would be reached after c (180/200=90%)
        # So we need a+b+c+d to reach 95%
        filter = CumulativeThresholdFilter('value', threshold_pct=0.95)
        result = filter.filter(df)

        # All metrics should be included since we need all to reach 95%
        assert len(result) >= 3

    def test_cumulative_threshold_top_80_percent(self):
        """Test filtering to keep top 80%."""
        df = pd.DataFrame({
            'metric': ['a', 'b', 'c', 'd', 'e'],
            'value': [100, 50, 30, 15, 5]  # Total=200
        })

        # 80% of 200 = 160
        # Cumulative: a(100), a+b(150), a+b+c(180) > 160
        # So minimum value to keep = 30
        filter = CumulativeThresholdFilter('value', threshold_pct=0.80)
        result = filter.filter(df)

        assert len(result) >= 3
        assert result['value'].min() >= 30

    def test_cumulative_threshold_empty_dataframe(self):
        """Test filtering on empty DataFrame."""
        df = pd.DataFrame()
        filter = CumulativeThresholdFilter('value', threshold_pct=0.95)
        result = filter.filter(df)

        assert result.empty

    def test_cumulative_threshold_missing_column(self):
        """Test filtering when value column doesn't exist."""
        df = pd.DataFrame({
            'metric': ['a', 'b', 'c'],
            'other': [100, 50, 30]
        })

        filter = CumulativeThresholdFilter('value', threshold_pct=0.95)
        result = filter.filter(df)

        # Should return copy of original
        assert len(result) == 3
        pd.testing.assert_frame_equal(result, df)

    def test_cumulative_threshold_zero_total(self):
        """Test filtering when total value is zero."""
        df = pd.DataFrame({
            'metric': ['a', 'b', 'c'],
            'value': [0, 0, 0]
        })

        filter = CumulativeThresholdFilter('value', threshold_pct=0.95)
        result = filter.filter(df)

        # Should return copy when total is zero
        assert len(result) == 3

    def test_cumulative_threshold_invalid_percentage_raises_error(self):
        """Test that invalid percentage raises error."""
        with pytest.raises(ValueError, match="threshold_pct must be between 0 and 1"):
            CumulativeThresholdFilter('value', threshold_pct=1.5)

        with pytest.raises(ValueError, match="threshold_pct must be between 0 and 1"):
            CumulativeThresholdFilter('value', threshold_pct=0.0)

        with pytest.raises(ValueError, match="threshold_pct must be between 0 and 1"):
            CumulativeThresholdFilter('value', threshold_pct=-0.1)

    def test_cumulative_threshold_100_percent(self):
        """Test filtering with 100% threshold."""
        df = pd.DataFrame({
            'metric': ['a', 'b', 'c'],
            'value': [100, 50, 30]
        })

        filter = CumulativeThresholdFilter('value', threshold_pct=1.0)
        result = filter.filter(df)

        # Should keep all rows
        assert len(result) == 3

    def test_cumulative_threshold_with_exclude_columns(self):
        """Test filtering with exclude_columns parameter."""
        df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'metric': ['a', 'b', 'c'],
            'value': [100, 50, 30]
        })

        filter = CumulativeThresholdFilter('value', threshold_pct=0.80, exclude_columns=['date'])
        result = filter.filter(df)

        # Should still filter based on value column
        assert len(result) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
