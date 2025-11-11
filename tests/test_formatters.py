"""
Tests for DataFrame formatters.
"""

import pytest
import pandas as pd
from datetime import datetime
from chronomaly.infrastructure.transformers.formatters import ColumnFormatter


class TestColumnFormatter:
    """Tests for ColumnFormatter"""

    def test_custom_function_formatting(self):
        """Test formatting with custom function."""
        df = pd.DataFrame({
            'revenue': [1000.50, 2500.75, 3750.25],
            'sessions': [100, 250, 500]
        })

        formatter = ColumnFormatter({
            'revenue': lambda x: f"${x:,.2f}",
            'sessions': lambda x: f"{x:,}"
        })
        result = formatter.format(df)

        assert result.loc[0, 'revenue'] == "$1,000.50"
        assert result.loc[1, 'revenue'] == "$2,500.75"
        assert result.loc[0, 'sessions'] == "100"
        assert result.loc[2, 'sessions'] == "500"

    def test_percentage_helper_basic(self):
        """Test percentage helper method."""
        df = pd.DataFrame({
            'deviation_pct': [15.3, 25.7, 5.1]
        })

        formatter = ColumnFormatter.percentage('deviation_pct', decimal_places=1)
        result = formatter.format(df)

        assert result.loc[0, 'deviation_pct'] == "15.3%"
        assert result.loc[1, 'deviation_pct'] == "25.7%"
        assert result.loc[2, 'deviation_pct'] == "5.1%"

    def test_percentage_helper_multiple_columns(self):
        """Test percentage helper with multiple columns."""
        df = pd.DataFrame({
            'growth_rate': [15.3, 25.7],
            'change_pct': [10.5, 20.2]
        })

        formatter = ColumnFormatter.percentage(['growth_rate', 'change_pct'], decimal_places=2)
        result = formatter.format(df)

        assert result.loc[0, 'growth_rate'] == "15.30%"
        assert result.loc[1, 'change_pct'] == "20.20%"

    def test_percentage_helper_with_multiplication(self):
        """Test percentage helper with multiply_by_100."""
        df = pd.DataFrame({
            'conversion_rate': [0.153, 0.257]  # Values between 0-1
        })

        formatter = ColumnFormatter.percentage('conversion_rate', decimal_places=1, multiply_by_100=True)
        result = formatter.format(df)

        assert result.loc[0, 'conversion_rate'] == "15.3%"
        assert result.loc[1, 'conversion_rate'] == "25.7%"

    def test_percentage_helper_decimal_places(self):
        """Test percentage helper with different decimal places."""
        df = pd.DataFrame({
            'value': [15.3456, 25.7891]
        })

        formatter = ColumnFormatter.percentage('value', decimal_places=0)
        result = formatter.format(df)
        assert result.loc[0, 'value'] == "15%"

        formatter = ColumnFormatter.percentage('value', decimal_places=3)
        result = formatter.format(df)
        assert result.loc[0, 'value'] == "15.346%"

    def test_date_formatting(self):
        """Test custom date formatting."""
        df = pd.DataFrame({
            'date': [datetime(2024, 1, 15), datetime(2024, 2, 20)],
            'value': [100, 200]
        })

        formatter = ColumnFormatter({
            'date': lambda x: x.strftime('%Y-%m-%d')
        })
        result = formatter.format(df)

        assert result.loc[0, 'date'] == "2024-01-15"
        assert result.loc[1, 'date'] == "2024-02-20"

    def test_status_icon_formatting(self):
        """Test formatting with status icons."""
        df = pd.DataFrame({
            'status': ['IN_RANGE', 'BELOW_LOWER', 'ABOVE_UPPER', 'IN_RANGE']
        })

        formatter = ColumnFormatter({
            'status': lambda x: '⚠️' if x in ['BELOW_LOWER', 'ABOVE_UPPER'] else '✓'
        })
        result = formatter.format(df)

        assert result.loc[0, 'status'] == '✓'
        assert result.loc[1, 'status'] == '⚠️'
        assert result.loc[2, 'status'] == '⚠️'
        assert result.loc[3, 'status'] == '✓'

    def test_empty_dataframe(self):
        """Test formatting on empty DataFrame."""
        df = pd.DataFrame()
        formatter = ColumnFormatter({'value': lambda x: f"{x}%"})
        result = formatter.format(df)

        assert result.empty

    def test_missing_column(self):
        """Test formatting when column doesn't exist."""
        df = pd.DataFrame({
            'value': [100, 200, 300]
        })

        formatter = ColumnFormatter({
            'missing_column': lambda x: f"{x}%",
            'value': lambda x: f"${x}"
        })
        result = formatter.format(df)

        # Should format existing column, skip missing one
        assert result.loc[0, 'value'] == "$100"
        assert 'missing_column' not in result.columns

    def test_empty_formatters_raises_error(self):
        """Test that empty formatters dict raises error."""
        with pytest.raises(ValueError, match="formatters dictionary cannot be empty"):
            ColumnFormatter({})

    def test_percentage_negative_decimal_places_raises_error(self):
        """Test that negative decimal places raises error."""
        with pytest.raises(ValueError, match="decimal_places must be non-negative"):
            ColumnFormatter.percentage('value', decimal_places=-1)

    def test_preserve_original_dataframe(self):
        """Test that original DataFrame is not modified."""
        original_df = pd.DataFrame({
            'value': [100, 200, 300]
        })
        original_copy = original_df.copy()

        formatter = ColumnFormatter({
            'value': lambda x: f"${x}"
        })
        result = formatter.format(original_df)

        # Original should be unchanged
        pd.testing.assert_frame_equal(original_df, original_copy)

        # Result should be different
        assert result.loc[0, 'value'] == "$100"

    def test_multiple_formatters_on_same_column(self):
        """Test that last formatter wins when multiple formatters for same column."""
        df = pd.DataFrame({
            'value': [100.5, 200.7]
        })

        # Create two formatters and apply sequentially
        formatter1 = ColumnFormatter({
            'value': lambda x: f"${x}"
        })
        formatter2 = ColumnFormatter({
            'value': lambda x: f"{x}%"
        })

        result = formatter1.format(df)
        result = formatter2.format(result)

        # Second formatter should process the string output of first formatter
        assert result.loc[0, 'value'] == "$100.5%"

    def test_complex_formatting_pipeline(self):
        """Test complex formatting with multiple columns."""
        df = pd.DataFrame({
            'date': [datetime(2024, 1, 15)],
            'metric': ['desktop_organic'],
            'actual': [1234.56],
            'deviation_pct': [15.345],
            'status': ['ABOVE_UPPER']
        })

        formatter = ColumnFormatter({
            'date': lambda x: x.strftime('%Y-%m-%d'),
            'metric': lambda x: x.replace('_', ' ').title(),
            'actual': lambda x: f"{x:,.0f}",
            'deviation_pct': lambda x: f"{x:.1f}%",
            'status': lambda x: '⚠️ ' + x
        })

        result = formatter.format(df)

        assert result.loc[0, 'date'] == "2024-01-15"
        assert result.loc[0, 'metric'] == "Desktop Organic"
        assert result.loc[0, 'actual'] == "1,235"
        assert result.loc[0, 'deviation_pct'] == "15.3%"
        assert result.loc[0, 'status'] == "⚠️ ABOVE_UPPER"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
