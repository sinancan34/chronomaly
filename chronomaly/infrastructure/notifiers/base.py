"""
Base abstract class for notifiers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class Notifier(ABC):
    """
    Abstract base class for all notifiers.

    All notifier implementations must inherit from this class
    and implement the notify() method.

    Notifiers are responsible for sending notifications (email, Slack, etc.)
    based on the provided payload data.
    """

    @abstractmethod
    def notify(self, payload: Dict[str, Any]) -> None:
        """
        Send notification based on the provided payload.

        Args:
            payload: Dictionary containing notification data.
                    Common keys:
                    - 'anomalies': pd.DataFrame with anomaly data
                    - 'charts': Dict[str, str] with chart images (optional)
                    - 'metadata': Dict with additional metadata (optional)

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        pass
