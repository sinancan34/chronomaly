"""
Tests for pivot transformer.
Tests for bugs #3, #4.
"""

import pytest
import pandas as pd
import numpy as np
from chronomaly.infrastructure.transformers import PivotTransformer


class TestPivotTransformer:
    """Tests for PivotTransformer"""

    def test_basic_pivot(self):
        """Test basic pivot functionality"""
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=3),
            'product': ['A', 'B', 'A'],
            'sales': [100, 200, 150]
        })

        transformer = PivotTransformer(
            index='date',
            columns='product',
            values='sales'
        )
        result = transformer.pivot_table(df)

        # Columns are lowercased by transformer
        assert 'a' in result.columns
        assert 'b' in result.columns
        assert len(result) == 3

    def test_pivot_with_object_column_containing_non_strings(self):
        """
        Bug #3: Test that transformer handles object columns with non-string data.
        Currently this test will FAIL with AttributeError.
        """
        # Create dataframe with object column containing datetime objects
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=3),
            'product': ['A', 'B', 'A'],
            'sales': [100, 200, 150],
            'metadata': [pd.Timestamp('2024-01-01'), None, pd.Timestamp('2024-01-02')]
        })

        transformer = PivotTransformer(
            index='date',
            columns='product',
            values='sales'
        )

        # Should not crash on object columns with non-string data (BUG #3)
        try:
            result = transformer.pivot_table(df)
            # If it doesn't crash, test passes
            assert True
        except AttributeError as e:
            # This is the bug - it tries to call .str methods on non-strings
            pytest.fail(f"Bug #3: AttributeError when handling object column: {e}")

    def test_pivot_with_datetime_index_not_named_date(self):
        """
        Bug #4: Test that frequency is set for datetime index regardless of name.
        Currently this test will FAIL because frequency is only set for 'date' column.
        """
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'product': ['A', 'B', 'A', 'B', 'A'],
            'sales': [100, 200, 150, 300, 250]
        })

        transformer = PivotTransformer(
            index='timestamp',
            columns='product',
            values='sales'
        )
        result = transformer.pivot_table(df)

        # The result index should have frequency set (BUG #4)
        # Currently fails because code checks for column name == 'date'
        assert result.index.freq is not None, "Bug #4: Frequency not set for datetime index named 'timestamp'"

    def test_pivot_with_string_columns_cleaning(self):
        """Test that string columns are properly cleaned"""
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=3),
            'product': ['Product A', 'Product B', 'Product A'],
            'sales': [100, 200, 150]
        })

        transformer = PivotTransformer(
            index='date',
            columns='product',
            values='sales'
        )
        result = transformer.pivot_table(df)

        # Verify that column names are cleaned (lowercase, no spaces)
        assert 'producta' in result.columns
        assert 'productb' in result.columns
