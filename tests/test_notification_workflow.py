"""
Tests for notification workflow and components.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from chronomaly.infrastructure.data.readers import DataFrameDataReader
from chronomaly.infrastructure.notifiers import Notifier, EmailNotifier
from chronomaly.application.workflows import NotificationWorkflow
from chronomaly.infrastructure.transformers.filters import ValueFilter


class TestDataFrameDataReader:
    """Tests for DataFrameDataReader"""

    def test_load_returns_dataframe(self):
        """Test that load() returns a DataFrame"""
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        reader = DataFrameDataReader(dataframe=df)
        result = reader.load()

        assert isinstance(result, pd.DataFrame)
        assert result.equals(df)

    def test_dataframe_is_copied(self):
        """Test that DataFrame is copied to avoid mutations"""
        df = pd.DataFrame({'a': [1, 2, 3]})
        reader = DataFrameDataReader(dataframe=df)

        # Mutate original
        df['a'] = [10, 20, 30]

        # Load should return original values (copy)
        result = reader.load()
        assert result['a'].tolist() == [1, 2, 3]

    def test_load_returns_copy(self):
        """Test that each load() call returns a new copy"""
        df = pd.DataFrame({'a': [1, 2, 3]})
        reader = DataFrameDataReader(dataframe=df)

        result1 = reader.load()
        result2 = reader.load()

        # Mutate result1
        result1['a'] = [10, 20, 30]

        # result2 should be unchanged
        assert result2['a'].tolist() == [1, 2, 3]

    def test_invalid_input_raises_error(self):
        """Test that non-DataFrame input raises TypeError"""
        with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            DataFrameDataReader(dataframe=[1, 2, 3])

    def test_transformers_are_applied(self):
        """Test that transformers are applied after loading"""
        df = pd.DataFrame({
            'status': ['ABOVE_UPPER', 'IN_RANGE', 'BELOW_LOWER'],
            'value': [100, 50, 10]
        })

        reader = DataFrameDataReader(
            dataframe=df,
            transformers={
                'after': [
                    ValueFilter('status', values=['ABOVE_UPPER', 'BELOW_LOWER'], mode='include')
                ]
            }
        )

        result = reader.load()
        assert len(result) == 2
        assert 'IN_RANGE' not in result['status'].values


class TestEmailNotifier:
    """Tests for EmailNotifier"""

    def test_initialization_with_single_recipient(self):
        """Test EmailNotifier with single recipient"""
        notifier = EmailNotifier(to="test@example.com")
        assert notifier.to == ["test@example.com"]

    def test_initialization_with_multiple_recipients(self):
        """Test EmailNotifier with multiple recipients"""
        recipients = ["user1@example.com", "user2@example.com"]
        notifier = EmailNotifier(to=recipients)
        assert notifier.to == recipients

    def test_empty_recipient_list_raises_error(self):
        """Test that empty recipient list raises ValueError"""
        with pytest.raises(ValueError, match="Recipient list cannot be empty"):
            EmailNotifier(to=[])

    def test_invalid_recipient_type_raises_error(self):
        """Test that invalid recipient type raises TypeError"""
        with pytest.raises(TypeError, match="must be a string or list"):
            EmailNotifier(to=123)

    def test_payload_without_anomalies_raises_error(self):
        """Test that payload without 'anomalies' key raises ValueError"""
        notifier = EmailNotifier(to="test@example.com")

        with pytest.raises(ValueError, match="must contain 'anomalies' key"):
            notifier.notify({})

    def test_payload_with_invalid_anomalies_type_raises_error(self):
        """Test that payload with non-DataFrame anomalies raises TypeError"""
        notifier = EmailNotifier(to="test@example.com")

        with pytest.raises(TypeError, match="must be a DataFrame"):
            notifier.notify({'anomalies': [1, 2, 3]})

    def test_empty_dataframe_skips_notification(self):
        """Test that empty DataFrame skips sending email"""
        notifier = EmailNotifier(to="test@example.com")
        empty_df = pd.DataFrame()

        # Mock SMTP to ensure it's not called
        with patch('smtplib.SMTP') as mock_smtp:
            notifier.notify({'anomalies': empty_df})
            mock_smtp.assert_not_called()

    def test_transformers_filter_before_notification(self):
        """Test that transformers are applied before notification"""
        df = pd.DataFrame({
            'status': ['ABOVE_UPPER', 'IN_RANGE', 'BELOW_LOWER'],
            'value': [100, 50, 10]
        })

        notifier = EmailNotifier(
            to="test@example.com",
            transformers={
                'before': [
                    ValueFilter('status', values=['IN_RANGE'], mode='include')
                ]
            }
        )

        # Mock SMTP
        with patch('smtplib.SMTP') as mock_smtp:
            # All anomalies will be filtered out by transformer (only IN_RANGE passes)
            # But we then filter to only anomalies, so result is empty
            # Actually, this keeps IN_RANGE, so email should be sent
            notifier.notify({'anomalies': df})

            # Since we kept IN_RANGE, email should be sent
            mock_smtp.assert_called_once()

    def test_filtered_to_empty_skips_notification(self):
        """Test that filtering to empty DataFrame skips notification"""
        df = pd.DataFrame({
            'status': ['IN_RANGE', 'IN_RANGE'],
            'value': [50, 60]
        })

        # Filter to only anomalies (ABOVE_UPPER, BELOW_LOWER)
        notifier = EmailNotifier(
            to="test@example.com",
            transformers={
                'before': [
                    ValueFilter('status', values=['ABOVE_UPPER', 'BELOW_LOWER'], mode='include')
                ]
            }
        )

        # Mock SMTP to ensure it's not called
        with patch('smtplib.SMTP') as mock_smtp:
            notifier.notify({'anomalies': df})
            mock_smtp.assert_not_called()

    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending"""
        df = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['sales'],
            'status': ['ABOVE_UPPER'],
            'actual': [100],
            'forecast': [50],
            'deviation_pct': [100.0]
        })

        notifier = EmailNotifier(to="test@example.com")

        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Send notification
        notifier.notify({'anomalies': df})

        # Verify SMTP was called
        mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

    @patch('smtplib.SMTP')
    def test_html_generation(self, mock_smtp):
        """Test HTML email content generation"""
        df = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['sales'],
            'status': ['ABOVE_UPPER'],
            'actual': [100.5],
            'forecast': [50.2]
        })

        notifier = EmailNotifier(to="test@example.com")

        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        notifier.notify({'anomalies': df})

        # Get the message that was sent
        call_args = mock_server.send_message.call_args[0]
        message = call_args[0]

        # Verify HTML content
        html_part = message.get_payload()[0]
        html_content = html_part.get_payload(decode=True).decode('utf-8')

        assert 'Anomaly Detection Alert' in html_content
        assert 'ABOVE_UPPER' in html_content
        assert '100.50' in html_content  # Numeric formatting
        assert 'sales' in html_content


class TestNotificationWorkflow:
    """Tests for NotificationWorkflow"""

    def test_initialization_with_valid_inputs(self):
        """Test workflow initialization with valid inputs"""
        df = pd.DataFrame({'a': [1, 2, 3]})
        notifier = Mock(spec=Notifier)

        workflow = NotificationWorkflow(
            anomalies_data=df,
            notifiers=[notifier]
        )

        assert workflow.anomalies_data.equals(df)
        assert workflow.notifiers == [notifier]

    def test_invalid_anomalies_data_type_raises_error(self):
        """Test that non-DataFrame anomalies_data raises TypeError"""
        notifier = Mock(spec=Notifier)

        with pytest.raises(TypeError, match="must be a DataFrame"):
            NotificationWorkflow(
                anomalies_data=[1, 2, 3],
                notifiers=[notifier]
            )

    def test_empty_anomalies_data_raises_error(self):
        """Test that empty DataFrame raises ValueError"""
        notifier = Mock(spec=Notifier)

        with pytest.raises(ValueError, match="cannot be empty"):
            NotificationWorkflow(
                anomalies_data=pd.DataFrame(),
                notifiers=[notifier]
            )

    def test_invalid_notifiers_type_raises_error(self):
        """Test that non-list notifiers raises TypeError"""
        df = pd.DataFrame({'a': [1, 2, 3]})

        with pytest.raises(TypeError, match="must be a list"):
            NotificationWorkflow(
                anomalies_data=df,
                notifiers="not a list"
            )

    def test_empty_notifiers_list_raises_error(self):
        """Test that empty notifiers list raises ValueError"""
        df = pd.DataFrame({'a': [1, 2, 3]})

        with pytest.raises(ValueError, match="cannot be empty"):
            NotificationWorkflow(
                anomalies_data=df,
                notifiers=[]
            )

    def test_invalid_notifier_instance_raises_error(self):
        """Test that non-Notifier instances raise TypeError"""
        df = pd.DataFrame({'a': [1, 2, 3]})

        with pytest.raises(TypeError, match="must be a Notifier instance"):
            NotificationWorkflow(
                anomalies_data=df,
                notifiers=["not a notifier"]
            )

    def test_run_calls_all_notifiers(self):
        """Test that run() calls notify() on all notifiers"""
        df = pd.DataFrame({'a': [1, 2, 3]})

        notifier1 = Mock(spec=Notifier)
        notifier2 = Mock(spec=Notifier)

        workflow = NotificationWorkflow(
            anomalies_data=df,
            notifiers=[notifier1, notifier2]
        )

        workflow.run()

        # Verify both notifiers were called
        notifier1.notify.assert_called_once()
        notifier2.notify.assert_called_once()

        # Verify they received correct payload
        expected_payload = {'anomalies': df}
        call_args1 = notifier1.notify.call_args[0][0]
        call_args2 = notifier2.notify.call_args[0][0]

        assert 'anomalies' in call_args1
        assert call_args1['anomalies'].equals(df)
        assert 'anomalies' in call_args2
        assert call_args2['anomalies'].equals(df)

    def test_run_handles_notifier_failure(self):
        """Test that run() raises RuntimeError with context when notifier fails"""
        df = pd.DataFrame({'a': [1, 2, 3]})

        notifier = Mock(spec=Notifier)
        notifier.notify.side_effect = Exception("SMTP connection failed")

        workflow = NotificationWorkflow(
            anomalies_data=df,
            notifiers=[notifier]
        )

        with pytest.raises(RuntimeError, match="Failed to send notification via Mock"):
            workflow.run()

    def test_integration_with_email_notifier(self):
        """Integration test with actual EmailNotifier"""
        df = pd.DataFrame({
            'date': ['2024-01-01'],
            'metric': ['sales'],
            'status': ['ABOVE_UPPER'],
            'actual': [100],
            'forecast': [50]
        })

        email_notifier = EmailNotifier(to="test@example.com")

        workflow = NotificationWorkflow(
            anomalies_data=df,
            notifiers=[email_notifier]
        )

        # Mock SMTP
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            workflow.run()

            # Verify email was sent
            mock_smtp.assert_called_once()
            mock_server.send_message.assert_called_once()
