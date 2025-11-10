"""
Base class for general DataFrame formatters.
"""

from abc import ABC, abstractmethod
import pandas as pd


class DataFrameFormatter(ABC):
    """
    Abstract base class for DataFrame formatters.

    Formatters transform column values without filtering rows.
    Can be applied at ANY stage of the pipeline.
    """

    @abstractmethod
    def format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Format a DataFrame.

        Args:
            df: Input DataFrame

        Returns:
            pd.DataFrame: Formatted DataFrame
        """
        pass
