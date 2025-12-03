"""
In-memory DataFrame data reader implementation.
"""

import pandas as pd
from typing import Optional, Dict, List, Callable
from .base import DataReader
from chronomaly.shared import TransformableMixin


class DataFrameDataReader(DataReader, TransformableMixin):
    """
    Data reader implementation for in-memory pandas DataFrame.

    This reader is useful when you already have data in memory and want to
    use it with workflows that expect a DataReader interface.

    Args:
        dataframe: The pandas DataFrame to wrap
        transformers: Optional dict of transformer lists to apply after loading data
                     Example: {'after': [Filter1(), Filter2()]}
                     Note: 'before' stage not supported for readers

    Example:
        from chronomaly.infrastructure.data.readers import DataFrameDataReader

        # You already have a DataFrame (e.g., from anomaly detection)
        anomalies_df = anomaly_workflow.run()

        # Wrap it in a DataReader
        reader = DataFrameDataReader(dataframe=anomalies_df)

        # Use it like any other DataReader
        df = reader.load()
    """

    def __init__(
        self,
        dataframe: pd.DataFrame,
        transformers: Optional[Dict[str, List[Callable]]] = None
    ):
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame, got {type(dataframe).__name__}"
            )

        self._dataframe: pd.DataFrame = dataframe.copy()  # Store a copy to avoid mutations
        self.transformers: dict[str, list[Callable]] = transformers or {}

    def load(self) -> pd.DataFrame:
        """
        Return the stored DataFrame.

        Returns:
            pd.DataFrame: The stored data
        """
        # Return a copy and apply transformers
        df = self._dataframe.copy()
        df = self._apply_transformers(df, 'after')
        return df
