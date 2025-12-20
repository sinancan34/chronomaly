"""
Slack notifier implementation.
"""

import json
import re
from typing import Dict, Any, Optional, Callable
import pandas as pd
from jinja2 import Template, TemplateSyntaxError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from .base import Notifier
from chronomaly.shared import TransformableMixin


class SlackNotifier(Notifier, TransformableMixin):
    """
    Slack notifier for sending anomaly alerts via Slack Bot API.

    Sends Block Kit-formatted messages to Slack channels or users with
    anomaly data. Supports filtering via transformers and templated message
    formatting.

    The Slack Bot Token is read from environment variables.
    Messages are formatted using Jinja2 templates that output Slack
    Block Kit JSON.

    Args:
        recipient: Slack channel ID (e.g., "C01234ABCD") or user ID
                  (e.g., "U01234ABCD", "W01234ABCD"). Only direct IDs are
                  supported - channel/user names are not resolved.
        template_path: Path to Slack message template file (Jinja2 format).
                      The template should output valid Slack Block Kit JSON.
                      The template receives the 'anomalies' DataFrame and
                      custom variables.
        template_variables: Optional dict of custom variables to pass to the
                           template. These can be used in the template with
                           Jinja2 syntax. Reserved names (anomalies, count, df)
                           are silently ignored.
        transformers: Optional transformers to apply before notification

    Note:
        SLACK_BOT_TOKEN must be set in environment variables.
        The bot must have chat:write permission.

    Example:
        notifier = SlackNotifier(
            recipient="C01234ABCD",  # Channel ID from Slack
            template_path="templates/slack/default.json",
            template_variables={"company": "Acme Corp"}
        )
    """

    def __init__(
        self,
        recipient: str,
        template_path: str,
        template_variables: Optional[Dict[str, Any]] = None,
        transformers: Optional[Dict[str, list[Callable]]] = None,
    ):
        # Validate recipient
        if not isinstance(recipient, str):
            raise TypeError("'recipient' must be a string")

        if not recipient.strip():
            raise ValueError("'recipient' cannot be empty")

        self.recipient: str = recipient.strip()
        self.transformers: dict[str, list[Callable]] = transformers or {}
        self._template_variables: dict[str, Any] = template_variables or {}

        # Validate recipient ID format
        self._validate_recipient_id(self.recipient)

        # Load and validate template (fail fast)
        import os

        self._template_content = self._load_and_validate_template(template_path)
        self._template_path = os.path.abspath(template_path)

        # Get Slack configuration from environment
        slack_config = self._get_slack_config()
        self.bot_token: str = slack_config["bot_token"]

        # Validate Slack configuration
        self._validate_slack_config()

        # Initialize Slack client (fail fast if token is invalid)
        self.client = WebClient(token=self.bot_token)

    def _validate_recipient_id(self, recipient: str) -> None:
        """
        Validate that recipient is a valid Slack ID.

        Valid formats:
            - Channel ID: starts with 'C' followed by alphanumeric
            - User ID: starts with 'U' or 'W' followed by alphanumeric

        Args:
            recipient: Recipient string (must be a Slack ID)

        Raises:
            ValueError: If recipient is not a valid Slack ID format
        """
        if re.match(r"^C[A-Z0-9]+$", recipient):
            return  # Valid channel ID
        elif re.match(r"^[UW][A-Z0-9]+$", recipient):
            return  # Valid user ID
        else:
            raise ValueError(
                f"Invalid recipient format: '{recipient}'. "
                f"Expected channel ID (C...) or user ID (U.../W...). "
                f"Channel/user names (#channel, @user) are not supported. "
                f"Use the ID from Slack instead."
            )

    def _get_slack_config(self) -> Dict[str, Any]:
        """
        Get Slack configuration from environment variables.

        Environment variables are loaded from .env file automatically.
        See .env.example for a template.

        Returns:
            dict: Slack configuration parameters
        """
        import os

        return {
            "bot_token": os.getenv("SLACK_BOT_TOKEN", ""),
        }

    def _validate_slack_config(self) -> None:
        """
        Validate Slack configuration.

        Raises:
            ValueError: If required Slack credentials are missing or invalid
        """
        if not self.bot_token:
            raise ValueError(
                "Slack bot token is required. Set SLACK_BOT_TOKEN "
                "environment variable."
            )

        if not self.bot_token.startswith("xoxb-"):
            raise ValueError(
                "Invalid Slack bot token format. Bot tokens must start with "
                "'xoxb-'. Set SLACK_BOT_TOKEN environment variable."
            )

    def _load_and_validate_template(self, template_path: str) -> str:
        """
        Load and validate Slack message template from file.

        Validates that:
        - File path is not empty
        - File exists at the provided path
        - File is readable
        - File contains valid content
        - File contains valid Jinja2 syntax
        - Template renders to valid JSON

        Args:
            template_path: Path to the Slack template file

        Returns:
            str: The loaded template content

        Raises:
            ValueError: If template_path is empty or template is invalid
            FileNotFoundError: If template file does not exist
            PermissionError: If template file is not readable
            RuntimeError: If template file read fails
        """
        import os

        # Validate path is not empty
        if not template_path:
            raise ValueError("template_path cannot be empty")

        # Resolve to absolute path
        abs_path = os.path.abspath(template_path)

        # Check if file exists
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(f"Slack template file not found: {abs_path}")

        # Check if file is readable
        if not os.access(abs_path, os.R_OK):
            raise PermissionError(f"Slack template file is not readable: {abs_path}")

        # Load template content
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                template_content = f.read()
        except Exception as e:
            raise RuntimeError(
                f"Failed to read template file '{abs_path}': {str(e)}"
            ) from e

        # Validate template is not empty
        if not template_content.strip():
            raise ValueError(f"Slack template file is empty: {abs_path}")

        # Validate Jinja2 syntax
        try:
            Template(template_content)
        except TemplateSyntaxError as e:
            raise ValueError(
                f"Invalid Jinja2 template syntax: {str(e)}. "
                f"Template file: {abs_path}"
            ) from e

        # Validate that template renders to valid JSON with sample data
        try:
            template = Template(template_content)
            sample_df = pd.DataFrame()
            rendered = template.render(anomalies=[], count=0, df=sample_df)
            json.loads(rendered)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Slack template does not render to valid JSON: {str(e)}. "
                f"Template file: {abs_path}"
            ) from e
        except Exception as e:
            raise ValueError(
                f"Failed to validate Slack template: {str(e)}. "
                f"Template file: {abs_path}"
            ) from e

        return template_content



    def notify(self, payload: Dict[str, Any]) -> None:
        """
        Send Slack notification with anomaly data.

        Args:
            payload: Dictionary containing notification data.
                    Required keys:
                    - 'anomalies': pd.DataFrame with anomaly data

        Raises:
            ValueError: If payload doesn't contain required data
            RuntimeError: If Slack message sending fails
        """
        # Extract anomalies DataFrame
        if "anomalies" not in payload:
            raise ValueError("Payload must contain 'anomalies' key with DataFrame")

        anomalies_df = payload["anomalies"]

        if not isinstance(anomalies_df, pd.DataFrame):
            raise TypeError(
                f"'anomalies' must be a DataFrame, got "
                f"{type(anomalies_df).__name__}"
            )

        # Apply transformers (e.g., filter only significant anomalies)
        filtered_df = self._apply_transformers(anomalies_df, "before")

        # Skip notification if no data after filtering
        if filtered_df.empty:
            return

        # Generate Slack message blocks
        blocks = self._generate_message_blocks(filtered_df)

        # Use recipient ID directly (already validated in __init__)
        recipient_id = self.recipient

        # Send Slack message
        self._send_message(recipient_id, blocks)

    def _generate_message_blocks(self, df: pd.DataFrame) -> list:
        """
        Generate Slack Block Kit message blocks from DataFrame.

        Args:
            df: DataFrame with anomaly data

        Returns:
            list: Slack Block Kit blocks (parsed from JSON template)

        Raises:
            RuntimeError: If template rendering or JSON parsing fails
        """
        try:
            # Convert DataFrame to dict for template
            anomalies_list = df.to_dict("records")

            # Render Jinja2 template
            template = Template(self._template_content)

            # Build context: start with custom variables, then override
            # with built-ins
            context = dict(self._template_variables)
            context.update(
                {
                    "anomalies": anomalies_list,
                    "count": len(df),
                    "df": df,  # Also provide DataFrame for flexibility
                }
            )

            rendered_json = template.render(**context)

            # Parse JSON to get blocks
            message_data = json.loads(rendered_json)

            # Extract blocks (template should have a "blocks" key)
            if "blocks" not in message_data:
                raise ValueError(
                    "Rendered template must contain a 'blocks' key with Slack "
                    "Block Kit blocks"
                )

            return message_data["blocks"]

        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse rendered template as JSON: {str(e)}. "
                f"Template file: {self._template_path}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Failed to render Slack template: {str(e)}. "
                f"Template file: {self._template_path}"
            ) from e

    def _send_message(self, recipient_id: str, blocks: list) -> None:
        """
        Send message to Slack via Bot API.

        Args:
            recipient_id: Slack channel ID or user ID
            blocks: Slack Block Kit blocks

        Raises:
            RuntimeError: If message sending fails
        """
        try:
            # Send message
            response = self.client.chat_postMessage(
                channel=recipient_id,
                blocks=blocks,
                text="Anomaly Detection Alert",  # Fallback text for notifications
            )

            if not response["ok"]:
                raise RuntimeError(
                    f"Slack API returned error: "
                    f"{response.get('error', 'Unknown error')}"
                )

        except SlackApiError as e:
            error_msg = e.response["error"]

            # Provide helpful error messages
            if error_msg == "channel_not_found":
                raise RuntimeError(
                    f"Channel not found: '{self.recipient}'. "
                    f"Ensure the bot is invited to the channel."
                ) from e
            elif error_msg == "not_in_channel":
                raise RuntimeError(
                    f"Bot is not in channel: '{self.recipient}'. "
                    f"Invite the bot to the channel first."
                ) from e
            elif error_msg == "invalid_auth":
                raise RuntimeError(
                    "Invalid Slack bot token. Check SLACK_BOT_TOKEN "
                    "environment variable."
                ) from e
            else:
                raise RuntimeError(f"Failed to send Slack message: {error_msg}") from e
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error while sending Slack message: {str(e)}"
            ) from e
