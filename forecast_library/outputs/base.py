"""
Base abstract class for output writers.
"""

from abc import ABC, abstractmethod
import pandas as pd


class OutputWriter(ABC):
    """
    Abstract base class for all output writer implementations.

    All output writer implementations must inherit from this class
    and implement the write() method.
    """

    @abstractmethod
    def write(self, dataframe: pd.DataFrame) -> None:
        """
        Write forecast results to the output destination.

        Args:
            dataframe: The forecast results as a pandas DataFrame
        """
        pass
