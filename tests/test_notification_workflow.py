"""
Tests for notification workflow and components.
"""

import os
import pytest
import pandas as pd
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from chronomaly.infrastructure.data.readers import DataFrameDataReader
from chronomaly.infrastructure.notifiers import EmailNotifier, SlackNotifier, Notifier
from chronomaly.application.workflows import NotificationWorkflow
from chronomaly.infrastructure.transformers.filters import ValueFilter


@pytest.fixture(autouse=True)
def smtp_env_vars():
    """Set up SMTP environment variables for all tests in this module."""
    os.environ["SMTP_HOST"] = "smtp.test.com"
    os.environ["SMTP_USER"] = "test@example.com"
    os.environ["SMTP_PASSWORD"] = "testpassword"
    os.environ["SMTP_FROM_EMAIL"] = "test@example.com"
    yield
    # Cleanup
    os.environ.pop("SMTP_HOST", None)
    os.environ.pop("SMTP_USER", None)
    os.environ.pop("SMTP_PASSWORD", None)
    os.environ.pop("SMTP_FROM_EMAIL", None)


@pytest.fixture
def email_template_file():
    """Create a temporary email template file for testing."""
    template_content = """<html>
<head>
    <style>
{% raw %}
        body {
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .summary {
            color: #666;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .anomaly-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .anomaly-table th {
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
            white-space: nowrap;
        }
        .anomaly-table td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
            vertical-align: middle;
        }
        .anomaly-table tr:hover {
            background-color: #f5f5f5;
        }
        .chart-cell {
            text-align: center;
            padding: 5px;
            width: 320px;
        }
        .chart-img {
            max-width: 300px;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 12px;
        }
{% endraw %}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚨 Anomaly Detection Alert</h1>
        <div class="summary">
            <strong>{{ count }}</strong> anomal{{ plural }} detected
        </div>
        {{ table }}
        <div class="footer">
            This is an automated alert from Chronomaly anomaly detection system.
        </div>
    </div>
</body>
</html>"""

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        f.write(template_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestDataFrameDataReader:
    """Tests for DataFrameDataReader"""

    def test_load_returns_dataframe(self):
        """Test that load() returns a DataFrame"""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        reader = DataFrameDataReader(dataframe=df)
        result = reader.load()

        assert isinstance(result, pd.DataFrame)
        assert result.equals(df)

    def test_dataframe_is_copied(self):
        """Test that DataFrame is copied to avoid mutations"""
        df = pd.DataFrame({"a": [1, 2, 3]})
        reader = DataFrameDataReader(dataframe=df)

        # Mutate original
        df["a"] = [10, 20, 30]

        # Load should return original values (copy)
        result = reader.load()
        assert result["a"].tolist() == [1, 2, 3]

    def test_load_returns_copy(self):
        """Test that each load() call returns a new copy"""
        df = pd.DataFrame({"a": [1, 2, 3]})
        reader = DataFrameDataReader(dataframe=df)

        result1 = reader.load()
        result2 = reader.load()

        # Mutate result1
        result1["a"] = [10, 20, 30]

        # result2 should be unchanged
        assert result2["a"].tolist() == [1, 2, 3]

    def test_invalid_input_raises_error(self):
        """Test that non-DataFrame input raises TypeError"""
        with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            DataFrameDataReader(dataframe=[1, 2, 3])

    def test_transformers_are_applied(self):
        """Test that transformers are applied after loading"""
        df = pd.DataFrame(
            {
                "status": ["ABOVE_UPPER", "IN_RANGE", "BELOW_LOWER"],
                "value": [100, 50, 10],
            }
        )

        reader = DataFrameDataReader(
            dataframe=df,
            transformers={
                "after": [
                    ValueFilter(
                        "status", values=["ABOVE_UPPER", "BELOW_LOWER"], mode="include"
                    )
                ]
            },
        )

        result = reader.load()
        assert len(result) == 2
        assert "IN_RANGE" not in result["status"].values


class TestEmailNotifier:
    """Tests for EmailNotifier"""

    def test_initialization_with_single_recipient(self, email_template_file):
        """Test EmailNotifier with single recipient"""
        notifier = EmailNotifier(
            to="test@example.com", template_path=email_template_file
        )
        assert notifier.to == ["test@example.com"]

    def test_initialization_with_multiple_recipients(self, email_template_file):
        """Test EmailNotifier with multiple recipients"""
        recipients = ["user1@example.com", "user2@example.com"]
        notifier = EmailNotifier(to=recipients, template_path=email_template_file)
        assert notifier.to == recipients

    def test_empty_recipient_list_raises_error(self, email_template_file):
        """Test that empty recipient list raises ValueError"""
        with pytest.raises(ValueError, match="Recipient list cannot be empty"):
            EmailNotifier(to=[], template_path=email_template_file)

    def test_invalid_recipient_type_raises_error(self, email_template_file):
        """Test that invalid recipient type raises TypeError"""
        with pytest.raises(TypeError, match="must be a string or list"):
            EmailNotifier(to=123, template_path=email_template_file)

    def test_missing_smtp_user_raises_error(self, email_template_file):
        """Test that missing SMTP_USER raises ValueError"""
        # Temporarily clear SMTP_USER
        original_user = os.environ.pop("SMTP_USER", None)
        try:
            with pytest.raises(ValueError, match="SMTP username is required"):
                EmailNotifier(to="test@example.com", template_path=email_template_file)
        finally:
            if original_user:
                os.environ["SMTP_USER"] = original_user

    def test_missing_smtp_password_raises_error(self, email_template_file):
        """Test that missing SMTP_PASSWORD raises ValueError"""
        # Temporarily clear SMTP_PASSWORD
        original_password = os.environ.pop("SMTP_PASSWORD", None)
        try:
            with pytest.raises(ValueError, match="SMTP password is required"):
                EmailNotifier(to="test@example.com", template_path=email_template_file)
        finally:
            if original_password:
                os.environ["SMTP_PASSWORD"] = original_password

    def test_missing_smtp_host_raises_error(self, email_template_file):
        """Test that missing SMTP_HOST raises ValueError"""
        # Temporarily set empty SMTP_HOST
        original_host = os.environ.get("SMTP_HOST")
        os.environ["SMTP_HOST"] = ""
        try:
            with pytest.raises(ValueError, match="SMTP host is required"):
                EmailNotifier(to="test@example.com", template_path=email_template_file)
        finally:
            if original_host:
                os.environ["SMTP_HOST"] = original_host

    def test_payload_without_anomalies_raises_error(self, email_template_file):
        """Test that payload without 'anomalies' key raises ValueError"""
        notifier = EmailNotifier(
            to="test@example.com", template_path=email_template_file
        )

        with pytest.raises(ValueError, match="must contain 'anomalies' key"):
            notifier.notify({})

    def test_payload_with_invalid_anomalies_type_raises_error(
        self, email_template_file
    ):
        """Test that payload with non-DataFrame anomalies raises TypeError"""
        notifier = EmailNotifier(
            to="test@example.com", template_path=email_template_file
        )

        with pytest.raises(TypeError, match="must be a DataFrame"):
            notifier.notify({"anomalies": [1, 2, 3]})

    def test_empty_dataframe_skips_notification(self, email_template_file):
        """Test that empty DataFrame skips sending email"""
        notifier = EmailNotifier(
            to="test@example.com", template_path=email_template_file
        )
        empty_df = pd.DataFrame()

        # Mock SMTP to ensure it's not called
        with patch("smtplib.SMTP") as mock_smtp:
            notifier.notify({"anomalies": empty_df})
            mock_smtp.assert_not_called()

    def test_transformers_filter_before_notification(self, email_template_file):
        """Test that transformers are applied before notification"""
        df = pd.DataFrame(
            {
                "status": ["ABOVE_UPPER", "IN_RANGE", "BELOW_LOWER"],
                "value": [100, 50, 10],
            }
        )

        notifier = EmailNotifier(
            to="test@example.com",
            template_path=email_template_file,
            transformers={
                "before": [ValueFilter("status", values=["IN_RANGE"], mode="include")]
            },
        )

        # Mock SMTP
        with patch("smtplib.SMTP") as mock_smtp:
            # All anomalies will be filtered out by transformer (only IN_RANGE passes)
            # But we then filter to only anomalies, so result is empty
            # Actually, this keeps IN_RANGE, so email should be sent
            notifier.notify({"anomalies": df})

            # Since we kept IN_RANGE, email should be sent
            mock_smtp.assert_called_once()

    def test_filtered_to_empty_skips_notification(self, email_template_file):
        """Test that filtering to empty DataFrame skips notification"""
        df = pd.DataFrame({"status": ["IN_RANGE", "IN_RANGE"], "value": [50, 60]})

        # Filter to only anomalies (ABOVE_UPPER, BELOW_LOWER)
        notifier = EmailNotifier(
            to="test@example.com",
            template_path=email_template_file,
            transformers={
                "before": [
                    ValueFilter(
                        "status", values=["ABOVE_UPPER", "BELOW_LOWER"], mode="include"
                    )
                ]
            },
        )

        # Mock SMTP to ensure it's not called
        with patch("smtplib.SMTP") as mock_smtp:
            notifier.notify({"anomalies": df})
            mock_smtp.assert_not_called()

    @patch("smtplib.SMTP")
    def test_send_email_success(self, mock_smtp, email_template_file):
        """Test successful email sending"""
        df = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric": ["sales"],
                "status": ["ABOVE_UPPER"],
                "actual": [100],
                "forecast": [50],
                "deviation_pct": [100.0],
            }
        )

        notifier = EmailNotifier(
            to="test@example.com", template_path=email_template_file
        )

        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Send notification
        notifier.notify({"anomalies": df})

        # Verify SMTP was called (with config from environment or defaults)
        assert mock_smtp.call_count == 1
        # Check port is correct
        call_args = mock_smtp.call_args
        assert call_args[0][1] == 587  # Port
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_html_generation(self, mock_smtp, email_template_file):
        """Test HTML email content generation"""
        df = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric": ["sales"],
                "status": ["ABOVE_UPPER"],
                "actual": [100.5],
                "forecast": [50.2],
            }
        )

        notifier = EmailNotifier(
            to="test@example.com", template_path=email_template_file
        )

        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        notifier.notify({"anomalies": df})

        # Get the message that was sent
        call_args = mock_server.send_message.call_args[0]
        message = call_args[0]

        # Verify HTML content
        html_part = message.get_payload()[0]
        html_content = html_part.get_payload(decode=True).decode("utf-8")

        assert "Anomaly Detection Alert" in html_content
        assert "ABOVE_UPPER" in html_content
        assert "100.5" in html_content  # Pandas native output
        assert "sales" in html_content

    def test_missing_template_path_raises_error(self):
        """Test that missing template_path raises ValueError"""
        with pytest.raises(ValueError, match="template_path cannot be empty"):
            EmailNotifier(to="test@example.com", template_path="")

    def test_nonexistent_template_file_raises_error(self):
        """Test that nonexistent template file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="Email template file not found"):
            EmailNotifier(
                to="test@example.com", template_path="/nonexistent/template.html"
            )

    def test_unreadable_template_file_raises_error(self, tmp_path):
        """Test that unreadable template file raises PermissionError"""
        template_file = tmp_path / "template.html"
        template_file.write_text("<html>{{ count }}{{ plural }}{{ table }}</html>")
        template_file.chmod(0o000)  # Make unreadable

        try:
            with pytest.raises(PermissionError, match="not readable"):
                EmailNotifier(to="test@example.com", template_path=str(template_file))
        finally:
            template_file.chmod(0o644)  # Restore permissions for cleanup

    def test_empty_template_file_raises_error(self, tmp_path):
        """Test that empty template file raises ValueError"""
        template_file = tmp_path / "template.html"
        template_file.write_text("")

        with pytest.raises(ValueError, match="Email template file is empty"):
            EmailNotifier(to="test@example.com", template_path=str(template_file))

    def test_template_missing_placeholders_raises_error(self, tmp_path):
        """Test that template missing required {table} placeholder raises ValueError"""
        template_file = tmp_path / "template.html"
        template_file.write_text("<html><body>No table placeholder here</body></html>")

        with pytest.raises(
            ValueError, match="missing required placeholder: \\{\\{ table \\}\\}"
        ):
            EmailNotifier(to="test@example.com", template_path=str(template_file))

    def test_template_with_all_placeholders_succeeds(self, tmp_path):
        """Test that template with required {table} placeholder succeeds"""
        template_file = tmp_path / "template.html"
        template_file.write_text("<html>{{ table }}</html>")

        # Should not raise
        notifier = EmailNotifier(
            to="test@example.com", template_path=str(template_file)
        )
        assert notifier._template_content == "<html>{{ table }}</html>"
        assert notifier._template_path == str(template_file.resolve())

    def test_template_with_optional_placeholders_succeeds(self, tmp_path):
        """Test that template with optional {count} and {plural} placeholders works"""
        template_file = tmp_path / "template.html"
        template_file.write_text(
            "<html>{{ count }} anomal{{ plural }}: {{ table }}</html>"
        )

        # Should not raise - count and plural are optional
        notifier = EmailNotifier(
            to="test@example.com", template_path=str(template_file)
        )
        assert "{{ count }}" in notifier._template_content
        assert "{{ plural }}" in notifier._template_content
        assert "{{ table }}" in notifier._template_content

    @patch("smtplib.SMTP")
    def test_template_variables_are_passed_to_template(self, mock_smtp, tmp_path):
        """Test that custom template_variables are passed to the Jinja2 template"""
        template_file = tmp_path / "template.html"
        template_file.write_text(
            "<html><h1>{{ company }}</h1><p>{{ report_type }}</p>{{ table }}</html>"
        )

        notifier = EmailNotifier(
            to="test@example.com",
            template_path=str(template_file),
            template_variables={
                "company": "emlakjet.com",
                "report_type": "Google Search Console",
            },
        )

        df = pd.DataFrame({"status": ["ABOVE_UPPER"], "value": [100]})

        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        notifier.notify({"anomalies": df})

        # Get the message that was sent
        call_args = mock_server.send_message.call_args[0]
        message = call_args[0]
        html_part = message.get_payload()[0]
        html_content = html_part.get_payload(decode=True).decode("utf-8")

        assert "emlakjet.com" in html_content
        assert "Google Search Console" in html_content

    def test_reserved_template_variables_are_ignored(self, tmp_path):
        """Test that reserved names (table, count, plural) cannot be overridden"""
        template_file = tmp_path / "template.html"
        template_file.write_text(
            "<html>{{ count }} anomal{{ plural }}: {{ table }}</html>"
        )

        # Try to override reserved names
        notifier = EmailNotifier(
            to="test@example.com",
            template_path=str(template_file),
            template_variables={
                "table": "CUSTOM_TABLE",
                "count": 999,
                "plural": "CUSTOM_PLURAL",
            },
        )

        # Should not raise - reserved names silently ignored
        assert notifier._template_variables == {
            "table": "CUSTOM_TABLE",
            "count": 999,
            "plural": "CUSTOM_PLURAL",
        }


@pytest.fixture(autouse=True)
def slack_env_vars():
    """Set up Slack environment variables for all tests in this module."""
    os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token-123456"
    yield
    # Cleanup
    os.environ.pop("SLACK_BOT_TOKEN", None)


@pytest.fixture
def slack_template_file():
    """Create a temporary Slack template file for testing."""
    template_content = """{
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "Anomaly Alert"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*{{ count }}* anomalies detected"
      }
    }
  ]
}"""

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(template_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestSlackNotifier:
    """Tests for SlackNotifier"""

    # ===== INITIALIZATION TESTS =====

    def test_initialization_with_channel_name(self, slack_template_file):
        """Test SlackNotifier with channel name (#channel)"""
        notifier = SlackNotifier(recipient="#alerts", template_path=slack_template_file)
        assert notifier.recipient == "#alerts"
        assert notifier._recipient_type == "channel"

    def test_initialization_with_channel_id(self, slack_template_file):
        """Test SlackNotifier with channel ID (C...)"""
        notifier = SlackNotifier(
            recipient="C01234ABCD", template_path=slack_template_file
        )
        assert notifier.recipient == "C01234ABCD"
        assert notifier._recipient_type == "channel"

    def test_initialization_with_user_name(self, slack_template_file):
        """Test SlackNotifier with user name (@user)"""
        notifier = SlackNotifier(recipient="@john", template_path=slack_template_file)
        assert notifier.recipient == "@john"
        assert notifier._recipient_type == "user"

    def test_initialization_with_user_id(self, slack_template_file):
        """Test SlackNotifier with user ID (U...)"""
        notifier = SlackNotifier(
            recipient="U01234ABCD", template_path=slack_template_file
        )
        assert notifier.recipient == "U01234ABCD"
        assert notifier._recipient_type == "user"

    # ===== VALIDATION TESTS =====

    def test_empty_recipient_raises_error(self, slack_template_file):
        """Test that empty recipient raises ValueError"""
        with pytest.raises(ValueError, match="'recipient' cannot be empty"):
            SlackNotifier(recipient="", template_path=slack_template_file)

    def test_invalid_recipient_type_raises_error(self, slack_template_file):
        """Test that non-string recipient raises TypeError"""
        with pytest.raises(TypeError, match="must be a string"):
            SlackNotifier(recipient=123, template_path=slack_template_file)

    def test_invalid_recipient_format_raises_error(self, slack_template_file):
        """Test that invalid recipient format raises ValueError"""
        with pytest.raises(ValueError, match="Invalid recipient format"):
            SlackNotifier(recipient="invalid-format", template_path=slack_template_file)

    def test_missing_slack_token_raises_error(self, slack_template_file):
        """Test that missing SLACK_BOT_TOKEN raises ValueError"""
        original_token = os.environ.pop("SLACK_BOT_TOKEN", None)
        try:
            with pytest.raises(ValueError, match="Slack bot token is required"):
                SlackNotifier(recipient="#alerts", template_path=slack_template_file)
        finally:
            if original_token:
                os.environ["SLACK_BOT_TOKEN"] = original_token

    def test_invalid_token_format_raises_error(self, slack_template_file):
        """Test that invalid token format raises ValueError"""
        original_token = os.environ.get("SLACK_BOT_TOKEN")
        os.environ["SLACK_BOT_TOKEN"] = "invalid-token"
        try:
            with pytest.raises(ValueError, match="Bot tokens must start with 'xoxb-'"):
                SlackNotifier(recipient="#alerts", template_path=slack_template_file)
        finally:
            if original_token:
                os.environ["SLACK_BOT_TOKEN"] = original_token

    def test_missing_template_path_raises_error(self):
        """Test that missing template_path raises ValueError"""
        with pytest.raises(ValueError, match="template_path cannot be empty"):
            SlackNotifier(recipient="#alerts", template_path="")

    def test_nonexistent_template_file_raises_error(self):
        """Test that nonexistent template file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="Slack template file not found"):
            SlackNotifier(
                recipient="#alerts", template_path="/nonexistent/template.json"
            )

    def test_empty_template_file_raises_error(self, tmp_path):
        """Test that empty template file raises ValueError"""
        template_file = tmp_path / "template.json"
        template_file.write_text("")

        with pytest.raises(ValueError, match="Slack template file is empty"):
            SlackNotifier(recipient="#alerts", template_path=str(template_file))

    def test_invalid_json_template_raises_error(self, tmp_path):
        """Test that template with invalid JSON raises ValueError"""
        template_file = tmp_path / "template.json"
        template_file.write_text('{"blocks": [')  # Invalid JSON

        with pytest.raises(ValueError, match="does not render to valid JSON"):
            SlackNotifier(recipient="#alerts", template_path=str(template_file))

    def test_template_missing_blocks_key_raises_error(self, tmp_path):
        """Test that template without 'blocks' key raises ValueError"""
        template_file = tmp_path / "template.json"
        template_file.write_text('{"text": "Hello"}')  # Missing 'blocks'

        # This will pass validation but fail during _generate_message_blocks
        notifier = SlackNotifier(recipient="#alerts", template_path=str(template_file))

        df = pd.DataFrame({"status": ["ABOVE_UPPER"]})

        with pytest.raises(RuntimeError, match="must contain a 'blocks' key"):
            notifier._generate_message_blocks(df)

    # ===== PAYLOAD VALIDATION TESTS =====

    def test_payload_without_anomalies_raises_error(self, slack_template_file):
        """Test that payload without 'anomalies' key raises ValueError"""
        notifier = SlackNotifier(recipient="#alerts", template_path=slack_template_file)

        with pytest.raises(ValueError, match="must contain 'anomalies' key"):
            notifier.notify({})

    def test_payload_with_invalid_anomalies_type_raises_error(
        self, slack_template_file
    ):
        """Test that payload with non-DataFrame anomalies raises TypeError"""
        notifier = SlackNotifier(recipient="#alerts", template_path=slack_template_file)

        with pytest.raises(TypeError, match="must be a DataFrame"):
            notifier.notify({"anomalies": [1, 2, 3]})

    # ===== BEHAVIOR TESTS =====

    def test_empty_dataframe_skips_notification(self, slack_template_file):
        """Test that empty DataFrame skips sending message"""
        notifier = SlackNotifier(recipient="#alerts", template_path=slack_template_file)
        empty_df = pd.DataFrame()

        # Mock Slack client to ensure it's not called
        with patch.object(notifier.client, "chat_postMessage") as mock_post:
            notifier.notify({"anomalies": empty_df})
            mock_post.assert_not_called()

    def test_transformers_filter_before_notification(self, slack_template_file):
        """Test that transformers are applied before notification"""
        df = pd.DataFrame(
            {
                "status": ["ABOVE_UPPER", "IN_RANGE", "BELOW_LOWER"],
                "value": [100, 50, 10],
            }
        )

        notifier = SlackNotifier(
            recipient="#alerts",
            template_path=slack_template_file,
            transformers={
                "before": [ValueFilter("status", values=["IN_RANGE"], mode="include")]
            },
        )

        # Mock Slack client
        with patch.object(notifier, "_resolve_recipient_id", return_value="C123"):
            with patch.object(notifier.client, "chat_postMessage") as mock_post:
                mock_post.return_value = {"ok": True}
                notifier.notify({"anomalies": df})

                # Should be called since we kept IN_RANGE
                mock_post.assert_called_once()

    def test_filtered_to_empty_skips_notification(self, slack_template_file):
        """Test that filtering to empty DataFrame skips notification"""
        df = pd.DataFrame({"status": ["IN_RANGE", "IN_RANGE"], "value": [50, 60]})

        notifier = SlackNotifier(
            recipient="#alerts",
            template_path=slack_template_file,
            transformers={
                "before": [
                    ValueFilter(
                        "status",
                        values=["ABOVE_UPPER", "BELOW_LOWER"],
                        mode="include",
                    )
                ]
            },
        )

        # Mock Slack client to ensure it's not called
        with patch.object(notifier.client, "chat_postMessage") as mock_post:
            notifier.notify({"anomalies": df})
            mock_post.assert_not_called()

    # ===== MESSAGE SENDING TESTS =====

    @patch("chronomaly.infrastructure.notifiers.slack.WebClient")
    def test_send_message_success(self, mock_webclient_class, slack_template_file):
        """Test successful message sending to channel"""
        df = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric": ["sales"],
                "status": ["ABOVE_UPPER"],
                "actual": [100],
                "forecast": [50],
                "deviation_pct": [100.0],
            }
        )

        # Mock WebClient instance
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        notifier = SlackNotifier(
            recipient="C01234ABCD",  # Channel ID (no resolution needed)
            template_path=slack_template_file,
        )

        # Send notification
        notifier.notify({"anomalies": df})

        # Verify message was sent
        mock_client.chat_postMessage.assert_called_once()
        call_args = mock_client.chat_postMessage.call_args

        assert call_args[1]["channel"] == "C01234ABCD"
        assert "blocks" in call_args[1]
        assert call_args[1]["text"] == "Anomaly Detection Alert"

    @patch("chronomaly.infrastructure.notifiers.slack.WebClient")
    def test_channel_name_resolution(self, mock_webclient_class, slack_template_file):
        """Test channel name resolution to ID"""
        # Mock WebClient instance
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client

        # Mock conversations_list response
        mock_client.conversations_list.return_value = {
            "channels": [
                {"id": "C111", "name": "general"},
                {"id": "C222", "name": "alerts"},
                {"id": "C333", "name": "random"},
            ]
        }
        mock_client.chat_postMessage.return_value = {"ok": True}

        notifier = SlackNotifier(recipient="#alerts", template_path=slack_template_file)

        df = pd.DataFrame({"status": ["ABOVE_UPPER"]})
        notifier.notify({"anomalies": df})

        # Verify channel was resolved correctly
        mock_client.conversations_list.assert_called_once()
        call_args = mock_client.chat_postMessage.call_args
        assert call_args[1]["channel"] == "C222"

    @patch("chronomaly.infrastructure.notifiers.slack.WebClient")
    def test_user_name_resolution(self, mock_webclient_class, slack_template_file):
        """Test user name resolution to ID"""
        # Mock WebClient instance
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client

        # Mock users_list response
        mock_client.users_list.return_value = {
            "members": [
                {"id": "U111", "name": "alice", "real_name": "Alice Smith"},
                {"id": "U222", "name": "john", "real_name": "John Doe"},
                {"id": "U333", "name": "bob", "real_name": "Bob Johnson"},
            ]
        }
        mock_client.chat_postMessage.return_value = {"ok": True}

        notifier = SlackNotifier(recipient="@john", template_path=slack_template_file)

        df = pd.DataFrame({"status": ["ABOVE_UPPER"]})
        notifier.notify({"anomalies": df})

        # Verify user was resolved correctly
        mock_client.users_list.assert_called_once()
        call_args = mock_client.chat_postMessage.call_args
        assert call_args[1]["channel"] == "U222"

    @patch("chronomaly.infrastructure.notifiers.slack.WebClient")
    def test_channel_not_found_error(self, mock_webclient_class, slack_template_file):
        """Test error when channel is not found"""
        # Mock WebClient instance
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client

        # Mock empty channel list
        mock_client.conversations_list.return_value = {"channels": []}

        notifier = SlackNotifier(
            recipient="#nonexistent", template_path=slack_template_file
        )

        df = pd.DataFrame({"status": ["ABOVE_UPPER"]})

        with pytest.raises(ValueError, match="Channel not found"):
            notifier.notify({"anomalies": df})

    @patch("chronomaly.infrastructure.notifiers.slack.WebClient")
    def test_user_not_found_error(self, mock_webclient_class, slack_template_file):
        """Test error when user is not found"""
        # Mock WebClient instance
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client

        # Mock empty user list
        mock_client.users_list.return_value = {"members": []}

        notifier = SlackNotifier(
            recipient="@nonexistent", template_path=slack_template_file
        )

        df = pd.DataFrame({"status": ["ABOVE_UPPER"]})

        with pytest.raises(ValueError, match="User not found"):
            notifier.notify({"anomalies": df})

    @patch("chronomaly.infrastructure.notifiers.slack.WebClient")
    def test_slack_api_error_handling(self, mock_webclient_class, slack_template_file):
        """Test handling of Slack API errors"""
        from slack_sdk.errors import SlackApiError

        # Mock WebClient instance
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client

        # Mock API error
        mock_response = {"error": "not_in_channel", "ok": False}
        mock_client.chat_postMessage.side_effect = SlackApiError(
            message="Error", response=mock_response
        )

        notifier = SlackNotifier(
            recipient="C01234ABCD", template_path=slack_template_file
        )

        df = pd.DataFrame({"status": ["ABOVE_UPPER"]})

        with pytest.raises(RuntimeError, match="Bot is not in channel"):
            notifier.notify({"anomalies": df})

    def test_template_variables_are_passed(self, tmp_path):
        """Test that custom template_variables are passed to template"""
        template_file = tmp_path / "template.json"
        template_file.write_text(
            """{
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "{{ company }} - {{ count }} anomalies"
      }
    }
  ]
}"""
        )

        with patch(
            "chronomaly.infrastructure.notifiers.slack.WebClient"
        ) as mock_webclient_class:
            mock_client = MagicMock()
            mock_webclient_class.return_value = mock_client
            mock_client.chat_postMessage.return_value = {"ok": True}

            notifier = SlackNotifier(
                recipient="C01234ABCD",
                template_path=str(template_file),
                template_variables={"company": "Acme Corp"},
            )

            df = pd.DataFrame({"status": ["ABOVE_UPPER"]})
            notifier.notify({"anomalies": df})

            # Get blocks from call
            call_args = mock_client.chat_postMessage.call_args
            blocks = call_args[1]["blocks"]

            # Verify custom variable was rendered
            assert "Acme Corp" in blocks[0]["text"]["text"]
            assert "1 anomalies" in blocks[0]["text"]["text"]

    # ===== INTEGRATION TESTS =====

    @patch("chronomaly.infrastructure.notifiers.slack.WebClient")
    def test_integration_with_notification_workflow(
        self, mock_webclient_class, slack_template_file
    ):
        """Integration test with NotificationWorkflow"""
        df = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric": ["sales"],
                "status": ["ABOVE_UPPER"],
                "actual": [100],
                "forecast": [50],
            }
        )

        # Mock WebClient
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        slack_notifier = SlackNotifier(
            recipient="C01234ABCD", template_path=slack_template_file
        )

        workflow = NotificationWorkflow(anomalies_data=df, notifiers=[slack_notifier])

        workflow.run()

        # Verify message was sent
        mock_client.chat_postMessage.assert_called_once()


class TestNotificationWorkflow:
    """Tests for NotificationWorkflow"""

    def test_initialization_with_valid_inputs(self):
        """Test workflow initialization with valid inputs"""
        df = pd.DataFrame({"a": [1, 2, 3]})
        notifier = Mock(spec=Notifier)

        workflow = NotificationWorkflow(anomalies_data=df, notifiers=[notifier])

        assert workflow.anomalies_data.equals(df)
        assert workflow.notifiers == [notifier]

    def test_invalid_anomalies_data_type_raises_error(self):
        """Test that non-DataFrame anomalies_data raises TypeError"""
        notifier = Mock(spec=Notifier)

        with pytest.raises(TypeError, match="must be a DataFrame"):
            NotificationWorkflow(anomalies_data=[1, 2, 3], notifiers=[notifier])

    def test_empty_anomalies_data_raises_error(self):
        """Test that empty DataFrame raises ValueError"""
        notifier = Mock(spec=Notifier)

        with pytest.raises(ValueError, match="cannot be empty"):
            NotificationWorkflow(anomalies_data=pd.DataFrame(), notifiers=[notifier])

    def test_invalid_notifiers_type_raises_error(self):
        """Test that non-list notifiers raises TypeError"""
        df = pd.DataFrame({"a": [1, 2, 3]})

        with pytest.raises(TypeError, match="must be a list"):
            NotificationWorkflow(anomalies_data=df, notifiers="not a list")

    def test_empty_notifiers_list_raises_error(self):
        """Test that empty notifiers list raises ValueError"""
        df = pd.DataFrame({"a": [1, 2, 3]})

        with pytest.raises(ValueError, match="cannot be empty"):
            NotificationWorkflow(anomalies_data=df, notifiers=[])

    def test_invalid_notifier_instance_raises_error(self):
        """Test that non-Notifier instances raise TypeError"""
        df = pd.DataFrame({"a": [1, 2, 3]})

        with pytest.raises(TypeError, match="must be a Notifier instance"):
            NotificationWorkflow(anomalies_data=df, notifiers=["not a notifier"])

    def test_run_calls_all_notifiers(self):
        """Test that run() calls notify() on all notifiers"""
        df = pd.DataFrame({"a": [1, 2, 3]})

        notifier1 = Mock(spec=Notifier)
        notifier2 = Mock(spec=Notifier)

        workflow = NotificationWorkflow(
            anomalies_data=df, notifiers=[notifier1, notifier2]
        )

        workflow.run()

        # Verify both notifiers were called
        notifier1.notify.assert_called_once()
        notifier2.notify.assert_called_once()

        # Verify they received correct payload
        call_args1 = notifier1.notify.call_args[0][0]
        call_args2 = notifier2.notify.call_args[0][0]

        assert "anomalies" in call_args1
        assert call_args1["anomalies"].equals(df)
        assert "anomalies" in call_args2
        assert call_args2["anomalies"].equals(df)

    def test_run_handles_notifier_failure(self):
        """Test that run() raises RuntimeError with context when notifier fails"""
        df = pd.DataFrame({"a": [1, 2, 3]})

        notifier = Mock(spec=Notifier)
        notifier.notify.side_effect = Exception("SMTP connection failed")

        workflow = NotificationWorkflow(anomalies_data=df, notifiers=[notifier])

        with pytest.raises(RuntimeError, match="Failed to send notification via Mock"):
            workflow.run()

    def test_integration_with_email_notifier(self, email_template_file):
        """Integration test with actual EmailNotifier"""
        df = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric": ["sales"],
                "status": ["ABOVE_UPPER"],
                "actual": [100],
                "forecast": [50],
            }
        )

        email_notifier = EmailNotifier(
            to="test@example.com", template_path=email_template_file
        )

        workflow = NotificationWorkflow(anomalies_data=df, notifiers=[email_notifier])

        # Mock SMTP
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            workflow.run()

            # Verify email was sent
            mock_smtp.assert_called_once()
            mock_server.send_message.assert_called_once()
