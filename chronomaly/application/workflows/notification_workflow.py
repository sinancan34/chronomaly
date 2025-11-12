"""
Notification workflow orchestrator.
"""

import pandas as pd
from typing import List
from ...infrastructure.notifiers.base import Notifier


class NotificationWorkflow:
    """
    Main orchestrator class for the notification workflow.

    This workflow orchestrates the notification process:
    1. Receive anomaly data (as DataFrame)
    2. Prepare notification payload
    3. Send notifications via all configured notifiers

    Args:
        anomalies_data: DataFrame containing anomaly detection results
        notifiers: List of notifier instances (email, Slack, etc.)

    Example:
        from chronomaly.application.workflows import NotificationWorkflow
        from chronomaly.infrastructure.notifiers import EmailNotifier
        from chronomaly.infrastructure.transformers.filters import ValueFilter

        # Run anomaly detection first
        anomalies_df = anomaly_workflow.run()

        # Configure email notifier with filters
        email_notifier = EmailNotifier(
            to=["team@example.com", "manager@example.com"],
            smtp_user="alerts@example.com",
            smtp_password="app_password",
            transformers={
                'before': [
                    # Only email significant anomalies
                    ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER'], mode='include'),
                    ValueFilter('deviation_pct', min_value=0.1)  # 10%+ deviation
                ]
            }
        )

        # Create and run notification workflow
        notification_workflow = NotificationWorkflow(
            anomalies_data=anomalies_df,
            notifiers=[email_notifier]
        )
        notification_workflow.run()

    Multiple Notifiers Example:
        # Configure multiple notification channels
        email_notifier = EmailNotifier(to=["team@example.com"], ...)
        slack_notifier = SlackNotifier(channel="#alerts", ...)  # Future

        notification_workflow = NotificationWorkflow(
            anomalies_data=anomalies_df,
            notifiers=[email_notifier, slack_notifier]
        )
        notification_workflow.run()  # Sends to all channels
    """

    def __init__(
        self,
        anomalies_data: pd.DataFrame,
        notifiers: List[Notifier]
    ):
        # Validate anomalies_data
        if not isinstance(anomalies_data, pd.DataFrame):
            raise TypeError(
                f"anomalies_data must be a DataFrame, got {type(anomalies_data).__name__}"
            )

        if anomalies_data.empty:
            raise ValueError("anomalies_data cannot be empty")

        self.anomalies_data = anomalies_data

        # Validate notifiers
        if not isinstance(notifiers, list):
            raise TypeError(
                f"notifiers must be a list, got {type(notifiers).__name__}"
            )

        if not notifiers:
            raise ValueError("notifiers list cannot be empty")

        # Validate all items are Notifier instances
        for i, notifier in enumerate(notifiers):
            if not isinstance(notifier, Notifier):
                raise TypeError(
                    f"notifiers[{i}] must be a Notifier instance, "
                    f"got {type(notifier).__name__}"
                )

        self.notifiers = notifiers

    def run(self) -> None:
        """
        Execute the complete notification workflow.

        This method:
        1. Prepares notification payload from anomaly data
        2. Sends notifications via all configured notifiers

        Each notifier may apply its own transformers (e.g., filters)
        before sending, so different notifiers may receive different
        subsets of the data based on their configuration.

        Raises:
            RuntimeError: If notification fails
        """
        # Prepare payload
        payload = {
            'anomalies': self.anomalies_data
        }

        # Send notifications via all notifiers
        for notifier in self.notifiers:
            try:
                notifier.notify(payload)
            except Exception as e:
                # Re-raise with context about which notifier failed
                notifier_name = type(notifier).__name__
                raise RuntimeError(
                    f"Failed to send notification via {notifier_name}: {str(e)}"
                ) from e
