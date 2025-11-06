"""
Base abstract class for data sources.
"""

from abc import ABC, abstractmethod
import pandas as pd


class DataSource(ABC):
    """
    Abstract base class for all data sources.

    All data source implementations must inherit from this class
    and implement the load() method.
    """

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """
        Load data from the source and return as pandas DataFrame.

        Returns:
            pd.DataFrame: The loaded data as a pandas DataFrame
        """
        pass
