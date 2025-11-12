"""
Tests for ColumnSelector formatter.
"""

import pytest
import pandas as pd
from chronomaly.infrastructure.transformers.formatters import ColumnSelector


class TestColumnSelectorDrop:
    """Tests for ColumnSelector in drop mode"""

    def test_drop_single_column(self):
        """Test dropping a single column"""
        df = pd.DataFrame({
            'a': [1, 2, 3],
            'b': [4, 5, 6],
            'c': [7, 8, 9]
        })

        formatter = ColumnSelector('b', mode='drop')
        result = formatter.format(df)

        assert 'a' in result.columns
        assert 'b' not in result.columns
        assert 'c' in result.columns
        assert len(result) == 3

    def test_drop_multiple_columns(self):
        """Test dropping multiple columns"""
        df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02'],
            'metric': ['sales', 'revenue'],
            'value': [100, 200],
            'internal_id': [1, 2],
            'temp_field': ['x', 'y']
        })

        formatter = ColumnSelector(['internal_id', 'temp_field'], mode='drop')
        result = formatter.format(df)

        assert 'date' in result.columns
        assert 'metric' in result.columns
        assert 'value' in result.columns
        assert 'internal_id' not in result.columns
        assert 'temp_field' not in result.columns
        assert len(result) == 2

    def test_drop_non_existent_column(self):
        """Test dropping a column that doesn't exist"""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})

        formatter = ColumnSelector('non_existent', mode='drop')
        result = formatter.format(df)

        # Should return original DataFrame (no columns dropped)
        assert 'a' in result.columns
        assert 'b' in result.columns
        assert len(result) == 2

    def test_drop_mixed_existent_and_non_existent(self):
        """Test dropping mix of existing and non-existing columns"""
        df = pd.DataFrame({
            'a': [1, 2],
            'b': [3, 4],
            'c': [5, 6]
        })

        formatter = ColumnSelector(['b', 'non_existent', 'd'], mode='drop')
        result = formatter.format(df)

        # Only 'b' should be dropped
        assert 'a' in result.columns
        assert 'b' not in result.columns
        assert 'c' in result.columns

    def test_drop_all_columns(self):
        """Test dropping all columns"""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})

        formatter = ColumnSelector(['a', 'b'], mode='drop')
        result = formatter.format(df)

        # Should return empty DataFrame with same index
        assert len(result.columns) == 0
        assert len(result) == 2  # Rows preserved

    def test_drop_empty_dataframe(self):
        """Test dropping columns from empty DataFrame"""
        df = pd.DataFrame()

        formatter = ColumnSelector(['a', 'b'], mode='drop')
        result = formatter.format(df)

        assert result.empty


class TestColumnSelectorKeep:
    """Tests for ColumnSelector in keep mode"""

    def test_keep_single_column(self):
        """Test keeping a single column"""
        df = pd.DataFrame({
            'a': [1, 2, 3],
            'b': [4, 5, 6],
            'c': [7, 8, 9]
        })

        formatter = ColumnSelector('b', mode='keep')
        result = formatter.format(df)

        assert 'a' not in result.columns
        assert 'b' in result.columns
        assert 'c' not in result.columns
        assert len(result) == 3

    def test_keep_multiple_columns(self):
        """Test keeping multiple columns"""
        df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02'],
            'metric': ['sales', 'revenue'],
            'value': [100, 200],
            'internal_id': [1, 2],
            'temp_field': ['x', 'y']
        })

        formatter = ColumnSelector(['date', 'metric', 'value'], mode='keep')
        result = formatter.format(df)

        assert 'date' in result.columns
        assert 'metric' in result.columns
        assert 'value' in result.columns
        assert 'internal_id' not in result.columns
        assert 'temp_field' not in result.columns

    def test_keep_non_existent_column(self):
        """Test keeping a column that doesn't exist"""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})

        formatter = ColumnSelector('non_existent', mode='keep')
        result = formatter.format(df)

        # Should return empty DataFrame (no columns match)
        assert len(result.columns) == 0
        assert len(result) == 2  # Rows preserved

    def test_keep_mixed_existent_and_non_existent(self):
        """Test keeping mix of existing and non-existing columns"""
        df = pd.DataFrame({
            'a': [1, 2],
            'b': [3, 4],
            'c': [5, 6]
        })

        formatter = ColumnSelector(['a', 'non_existent', 'd'], mode='keep')
        result = formatter.format(df)

        # Only 'a' should be kept
        assert 'a' in result.columns
        assert 'b' not in result.columns
        assert 'c' not in result.columns
        assert len(result.columns) == 1


class TestColumnSelectorValidation:
    """Tests for ColumnSelector validation"""

    def test_invalid_mode(self):
        """Test that invalid mode raises error"""
        with pytest.raises(ValueError, match="mode must be 'keep' or 'drop'"):
            ColumnSelector(['a'], mode='invalid')

    def test_empty_columns_list(self):
        """Test that empty columns list raises error"""
        with pytest.raises(ValueError, match="columns list cannot be empty"):
            ColumnSelector([])

    def test_invalid_columns_type(self):
        """Test that invalid columns type raises error"""
        with pytest.raises(TypeError, match="columns must be a string or list"):
            ColumnSelector(123)

    def test_default_mode_is_drop(self):
        """Test that default mode is 'drop'"""
        formatter = ColumnSelector('a')
        assert formatter.mode == 'drop'


class TestColumnSelectorDataIntegrity:
    """Tests for data integrity and immutability"""

    def test_returns_copy(self):
        """Test that format() returns a copy, not modifying original"""
        df = pd.DataFrame({
            'a': [1, 2, 3],
            'b': [4, 5, 6]
        })

        formatter = ColumnSelector('b', mode='drop')
        result = formatter.format(df)

        # Modify result
        result['a'] = [10, 20, 30]

        # Original should be unchanged
        assert df['a'].tolist() == [1, 2, 3]

    def test_preserves_row_order(self):
        """Test that row order is preserved"""
        df = pd.DataFrame({
            'id': [3, 1, 2],
            'value': [30, 10, 20],
            'unwanted': ['x', 'y', 'z']
        })

        formatter = ColumnSelector('unwanted', mode='drop')
        result = formatter.format(df)

        assert result['id'].tolist() == [3, 1, 2]
        assert result['value'].tolist() == [30, 10, 20]

    def test_preserves_column_order_in_keep_mode(self):
        """Test that column order matches input list in keep mode"""
        df = pd.DataFrame({
            'a': [1],
            'b': [2],
            'c': [3],
            'd': [4]
        })

        formatter = ColumnSelector(['c', 'a'], mode='keep')
        result = formatter.format(df)

        # Note: pandas preserves original DataFrame column order
        # not the order specified in the list
        assert 'a' in result.columns
        assert 'c' in result.columns
        assert len(result.columns) == 2


class TestColumnSelectorIntegration:
    """Integration tests with realistic scenarios"""

    def test_use_with_email_notifier_simulation(self):
        """Test dropping columns before email notification"""
        # Simulate anomaly detection results
        anomalies_df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02'],
            'metric': ['sales', 'revenue'],
            'status': ['ABOVE_UPPER', 'BELOW_LOWER'],
            'actual': [100, 50],
            'forecast': [80, 70],
            'deviation_pct': [0.25, -0.29],
            'internal_id': [12345, 67890],  # Don't want in email
            'temp_calc': [999, 888]  # Don't want in email
        })

        # Drop internal columns before email
        formatter = ColumnSelector(['internal_id', 'temp_calc'], mode='drop')
        email_ready = formatter.format(anomalies_df)

        # Verify clean data for email
        assert 'date' in email_ready.columns
        assert 'metric' in email_ready.columns
        assert 'status' in email_ready.columns
        assert 'internal_id' not in email_ready.columns
        assert 'temp_calc' not in email_ready.columns

    def test_keep_only_essential_columns(self):
        """Test keeping only essential columns for display"""
        full_df = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['sales'],
            'actual': [100],
            'forecast': [80],
            'status': ['ABOVE_UPPER'],
            'deviation_pct': [0.25],
            'lower_bound': [70],
            'upper_bound': [90],
            'internal_metadata': ['xyz'],
            'debug_info': ['abc']
        })

        # Keep only columns for display
        formatter = ColumnSelector(
            ['date', 'metric', 'actual', 'forecast', 'status', 'deviation_pct'],
            mode='keep'
        )
        display_df = formatter.format(full_df)

        assert len(display_df.columns) == 6
        assert 'internal_metadata' not in display_df.columns
        assert 'debug_info' not in display_df.columns
