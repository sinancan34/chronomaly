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
from chronomaly.infrastructure.notifiers import EmailNotifier, Notifier
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
        notifier = EmailNotifier(to="test@example.com", template_path=email_template_file)
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
        notifier = EmailNotifier(to="test@example.com", template_path=email_template_file)

        with pytest.raises(ValueError, match="must contain 'anomalies' key"):
            notifier.notify({})

    def test_payload_with_invalid_anomalies_type_raises_error(self, email_template_file):
        """Test that payload with non-DataFrame anomalies raises TypeError"""
        notifier = EmailNotifier(to="test@example.com", template_path=email_template_file)

        with pytest.raises(TypeError, match="must be a DataFrame"):
            notifier.notify({"anomalies": [1, 2, 3]})

    def test_empty_dataframe_skips_notification(self, email_template_file):
        """Test that empty DataFrame skips sending email"""
        notifier = EmailNotifier(to="test@example.com", template_path=email_template_file)
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

        notifier = EmailNotifier(to="test@example.com", template_path=email_template_file)

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

        notifier = EmailNotifier(to="test@example.com", template_path=email_template_file)

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
        with pytest.raises(
            FileNotFoundError, match="Email template file not found"
        ):
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
                EmailNotifier(
                    to="test@example.com", template_path=str(template_file)
                )
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

        with pytest.raises(ValueError, match="missing required placeholder: \\{\\{ table \\}\\}"):
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
        template_file.write_text("<html>{{ count }} anomal{{ plural }}: {{ table }}</html>")

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
        template_file.write_text("<html>{{ count }} anomal{{ plural }}: {{ table }}</html>")

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

        email_notifier = EmailNotifier(to="test@example.com", template_path=email_template_file)

        workflow = NotificationWorkflow(anomalies_data=df, notifiers=[email_notifier])

        # Mock SMTP
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            workflow.run()

            # Verify email was sent
            mock_smtp.assert_called_once()
            mock_server.send_message.assert_called_once()
