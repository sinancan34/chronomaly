"""
Tests for CSVDataWriter implementation.
"""

import pytest
import pandas as pd
import os
from chronomaly.infrastructure.data.writers.files import CSVDataWriter


class TestCSVDataWriterInitialization:
    """Tests for CSVDataWriter initialization and validation"""

    def test_empty_file_path_raises_error(self):
        """Test that empty file_path raises ValueError"""
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            CSVDataWriter(file_path="")

    def test_invalid_if_exists_raises_error(self, tmp_path):
        """Test that invalid if_exists value raises ValueError"""
        csv_file = tmp_path / "test.csv"
        with pytest.raises(ValueError, match="Invalid if_exists value"):
            CSVDataWriter(file_path=str(csv_file), if_exists="invalid_mode")

    def test_nonexistent_parent_directory_raises_error(self):
        """Test that nonexistent parent directory raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="Parent directory does not exist"):
            CSVDataWriter(file_path="/nonexistent/path/to/file.csv")

    def test_valid_initialization_replace_mode(self, tmp_path):
        """Test valid initialization with replace mode"""
        csv_file = tmp_path / "test.csv"
        writer = CSVDataWriter(file_path=str(csv_file), if_exists='replace')
        assert writer.if_exists == 'replace'
        assert writer.file_path == str(csv_file)

    def test_valid_initialization_append_mode(self, tmp_path):
        """Test valid initialization with append mode"""
        csv_file = tmp_path / "test.csv"
        writer = CSVDataWriter(file_path=str(csv_file), if_exists='append')
        assert writer.if_exists == 'append'


class TestCSVDataWriterWrite:
    """Tests for CSVDataWriter write functionality"""

    def test_write_simple_dataframe_replace_mode(self, tmp_path):
        """Test writing a simple DataFrame in replace mode"""
        csv_file = tmp_path / "test.csv"
        writer = CSVDataWriter(file_path=str(csv_file), if_exists='replace')

        # Create test dataframe
        df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'value': [1, 2, 3]
        })

        # Write data
        writer.write(df)

        # Verify file exists and content is correct
        assert os.path.exists(csv_file)
        result = pd.read_csv(csv_file)
        assert len(result) == 3
        assert list(result.columns) == ['date', 'value']
        assert list(result['value']) == [1, 2, 3]

    def test_write_with_append_mode_creates_file(self, tmp_path):
        """Test that append mode creates file if it doesn't exist"""
        csv_file = tmp_path / "test.csv"
        writer = CSVDataWriter(file_path=str(csv_file), if_exists='append')

        df = pd.DataFrame({
            'col1': [1, 2],
            'col2': [3, 4]
        })

        writer.write(df)

        # Verify file was created
        assert os.path.exists(csv_file)
        result = pd.read_csv(csv_file)
        assert len(result) == 2

    def test_write_with_append_mode_appends_data(self, tmp_path):
        """Test that append mode correctly appends to existing file"""
        csv_file = tmp_path / "test.csv"

        # First write
        writer1 = CSVDataWriter(file_path=str(csv_file), if_exists='replace')
        df1 = pd.DataFrame({
            'col1': [1, 2],
            'col2': [3, 4]
        })
        writer1.write(df1)

        # Second write in append mode
        writer2 = CSVDataWriter(file_path=str(csv_file), if_exists='append')
        df2 = pd.DataFrame({
            'col1': [5, 6],
            'col2': [7, 8]
        })
        writer2.write(df2)

        # Verify both sets of data are in file
        result = pd.read_csv(csv_file)
        assert len(result) == 4
        assert list(result['col1']) == [1, 2, 5, 6]
        assert list(result['col2']) == [3, 4, 7, 8]

    def test_write_with_replace_mode_overwrites_file(self, tmp_path):
        """Test that replace mode overwrites existing file"""
        csv_file = tmp_path / "test.csv"

        # First write
        writer1 = CSVDataWriter(file_path=str(csv_file), if_exists='replace')
        df1 = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': [4, 5, 6]
        })
        writer1.write(df1)

        # Second write with replace mode
        writer2 = CSVDataWriter(file_path=str(csv_file), if_exists='replace')
        df2 = pd.DataFrame({
            'col1': [7, 8],
            'col2': [9, 10]
        })
        writer2.write(df2)

        # Verify only second data is in file
        result = pd.read_csv(csv_file)
        assert len(result) == 2
        assert list(result['col1']) == [7, 8]


class TestCSVDataWriterValidation:
    """Tests for CSVDataWriter input validation"""

    def test_write_empty_dataframe_raises_error(self, tmp_path):
        """Test that writing empty DataFrame raises ValueError"""
        csv_file = tmp_path / "test.csv"
        writer = CSVDataWriter(file_path=str(csv_file))

        empty_df = pd.DataFrame()

        with pytest.raises(ValueError, match="Cannot write empty DataFrame"):
            writer.write(empty_df)

    def test_write_non_dataframe_raises_error(self, tmp_path):
        """Test that writing non-DataFrame raises TypeError"""
        csv_file = tmp_path / "test.csv"
        writer = CSVDataWriter(file_path=str(csv_file))

        with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            writer.write([1, 2, 3])

        with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            writer.write("not a dataframe")


class TestCSVDataWriterWithTransformers:
    """Tests for CSVDataWriter with transformers"""

    def test_write_with_before_transformer(self, tmp_path):
        """Test that 'before' transformers are applied correctly"""
        csv_file = tmp_path / "test.csv"

        # Create a simple transformer that filters rows
        def filter_transformer(df):
            return df[df['value'] > 1]

        writer = CSVDataWriter(
            file_path=str(csv_file),
            transformers={'before': [filter_transformer]}
        )

        df = pd.DataFrame({
            'value': [1, 2, 3, 4]
        })

        writer.write(df)

        # Verify only filtered data was written
        result = pd.read_csv(csv_file)
        assert len(result) == 3
        assert list(result['value']) == [2, 3, 4]


class TestCSVDataWriterKwargs:
    """Tests for CSVDataWriter with additional kwargs"""

    def test_write_with_custom_separator(self, tmp_path):
        """Test writing with custom separator"""
        csv_file = tmp_path / "test.csv"
        writer = CSVDataWriter(file_path=str(csv_file), sep=';')

        df = pd.DataFrame({
            'col1': [1, 2],
            'col2': [3, 4]
        })

        writer.write(df)

        # Read with custom separator
        result = pd.read_csv(csv_file, sep=';')
        assert len(result) == 2
        assert list(result.columns) == ['col1', 'col2']

    def test_write_with_encoding(self, tmp_path):
        """Test writing with specific encoding"""
        csv_file = tmp_path / "test.csv"
        writer = CSVDataWriter(file_path=str(csv_file), encoding='utf-8')

        df = pd.DataFrame({
            'text': ['Hello', 'World', 'Café']
        })

        writer.write(df)

        # Verify file can be read with same encoding
        result = pd.read_csv(csv_file, encoding='utf-8')
        assert len(result) == 3
        assert 'Café' in result['text'].values
