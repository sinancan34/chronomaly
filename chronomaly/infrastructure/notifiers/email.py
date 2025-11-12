"""
Email notifier implementation.
"""

import smtplib
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional, Callable
from .base import Notifier
from chronomaly.shared import TransformableMixin


class EmailNotifier(Notifier, TransformableMixin):
    """
    Email notifier for sending anomaly alerts via SMTP.

    Sends HTML-formatted emails with anomaly data presented as a styled table.
    Supports multiple recipients and filtering via transformers.

    SMTP credentials and email subject are configured within the code.

    Args:
        to: Recipient email address(es). Can be a single email or list of emails.
        transformers: Optional transformers to apply before notification
                     Example: {'before': [ValueFilter(...)]} to filter anomalies

    Example:
        from chronomaly.infrastructure.notifiers import EmailNotifier
        from chronomaly.infrastructure.transformers.filters import ValueFilter

        # Basic usage
        notifier = EmailNotifier(
            to=["team@example.com", "manager@example.com"]
        )

        # With filtering - only notify for significant anomalies
        notifier = EmailNotifier(
            to=["team@example.com"],
            transformers={
                'before': [
                    ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER'], mode='include'),
                    ValueFilter('deviation_pct', min_value=0.1)  # 10%+ deviation only
                ]
            }
        )

        # Send notification
        payload = {'anomalies': anomalies_df}
        notifier.notify(payload)

    Note:
        SMTP configuration and email subject are hardcoded in the class.
        Update _get_smtp_config() and _get_email_subject() methods to change settings.
    """

    def __init__(
        self,
        to: List[str] | str,
        transformers: Optional[Dict[str, List[Callable]]] = None
    ):
        # Validate and normalize recipients
        if isinstance(to, str):
            self.to = [to]
        elif isinstance(to, list):
            if not to:
                raise ValueError("Recipient list cannot be empty")
            if not all(isinstance(email, str) for email in to):
                raise TypeError("All recipients must be strings")
            self.to = to
        else:
            raise TypeError("'to' must be a string or list of strings")

        self.transformers = transformers or {}

        # Get SMTP configuration from internal method
        smtp_config = self._get_smtp_config()
        self.smtp_host = smtp_config['host']
        self.smtp_port = smtp_config['port']
        self.smtp_user = smtp_config['user']
        self.smtp_password = smtp_config['password']
        self.from_email = smtp_config['from_email']
        self.use_tls = smtp_config['use_tls']

        # Get email subject
        self.subject = self._get_email_subject()

    def _get_smtp_config(self) -> Dict[str, Any]:
        """
        Get SMTP configuration from environment variables.

        Environment variables are loaded from .env file automatically.
        See .env.example for a template.

        Environment Variables:
            SMTP_HOST: SMTP server hostname (default: smtp.gmail.com)
            SMTP_PORT: SMTP server port (default: 587)
            SMTP_USER: SMTP username/email
            SMTP_PASSWORD: SMTP password or app password
            SMTP_FROM_EMAIL: From email address (default: SMTP_USER)
            SMTP_USE_TLS: Use TLS encryption (default: True)

        Returns:
            dict: SMTP configuration parameters
        """
        import os

        return {
            'host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'user': os.getenv('SMTP_USER', ''),
            'password': os.getenv('SMTP_PASSWORD', ''),
            'from_email': os.getenv('SMTP_FROM_EMAIL', os.getenv('SMTP_USER', '')),
            'use_tls': os.getenv('SMTP_USE_TLS', 'True').lower() in ('true', '1', 'yes')
        }

    def _get_email_subject(self) -> str:
        """
        Get email subject line.

        Update this value to change the email subject.

        Returns:
            str: Email subject line
        """
        return "Anomaly Detection Alert"

    def notify(self, payload: Dict[str, Any]) -> None:
        """
        Send email notification with anomaly data.

        Args:
            payload: Dictionary containing notification data.
                    Required keys:
                    - 'anomalies': pd.DataFrame with anomaly data

        Raises:
            ValueError: If payload doesn't contain required data
            RuntimeError: If email sending fails
        """
        # Extract anomalies DataFrame
        if 'anomalies' not in payload:
            raise ValueError("Payload must contain 'anomalies' key with DataFrame")

        anomalies_df = payload['anomalies']

        if not isinstance(anomalies_df, pd.DataFrame):
            raise TypeError(
                f"'anomalies' must be a DataFrame, got {type(anomalies_df).__name__}"
            )

        # Apply transformers (e.g., filter only significant anomalies)
        filtered_df = self._apply_transformers(anomalies_df, 'before')

        # Skip notification if no data after filtering
        if filtered_df.empty:
            return

        # Generate HTML email content
        html_body = self._generate_html_body(filtered_df)

        # Send email
        self._send_email(html_body)

    def _generate_html_body(self, df: pd.DataFrame) -> str:
        """
        Generate HTML email body with styled table.

        Args:
            df: DataFrame with anomaly data

        Returns:
            str: HTML content
        """
        # Email header
        html = """
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f5f5f5;
                    padding: 20px;
                }}
                .container {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 10px;
                }}
                .summary {{
                    color: #666;
                    margin-bottom: 20px;
                    font-size: 14px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-weight: bold;
                }}
                td {{
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .status-below {{
                    color: #2196F3;
                    font-weight: bold;
                }}
                .status-above {{
                    color: #f44336;
                    font-weight: bold;
                }}
                .status-in-range {{
                    color: #4CAF50;
                }}
                .status-no-forecast {{
                    color: #9E9E9E;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚨 Anomaly Detection Alert</h1>
                <div class="summary">
                    <strong>{count}</strong> anomal{plural} detected
                </div>
        """.format(
            count=len(df),
            plural="ies" if len(df) != 1 else "y"
        )

        # Generate table
        html += "<table>\n<thead>\n<tr>\n"

        # Table headers
        for col in df.columns:
            html += f"<th>{col.replace('_', ' ').title()}</th>\n"

        html += "</tr>\n</thead>\n<tbody>\n"

        # Table rows
        for _, row in df.iterrows():
            html += "<tr>\n"
            for col in df.columns:
                value = row[col]

                # Apply styling for status column
                if col == 'status':
                    status_class = self._get_status_class(str(value))
                    html += f'<td class="{status_class}">{value}</td>\n'
                # Format numeric columns
                elif pd.api.types.is_numeric_dtype(type(value)):
                    if pd.notna(value):
                        # Format with 2 decimal places
                        html += f"<td>{value:.2f}</td>\n"
                    else:
                        html += "<td>-</td>\n"
                else:
                    html += f"<td>{value}</td>\n"

            html += "</tr>\n"

        html += """
                </tbody>
            </table>
            <div class="footer">
                This is an automated alert from Chronomaly anomaly detection system.
            </div>
            </div>
        </body>
        </html>
        """

        return html

    def _get_status_class(self, status: str) -> str:
        """
        Get CSS class name for anomaly status.

        Args:
            status: Anomaly status string

        Returns:
            str: CSS class name
        """
        status_upper = status.upper()
        if 'BELOW' in status_upper:
            return 'status-below'
        elif 'ABOVE' in status_upper:
            return 'status-above'
        elif 'IN_RANGE' in status_upper or 'IN RANGE' in status_upper:
            return 'status-in-range'
        elif 'NO_FORECAST' in status_upper or 'NO FORECAST' in status_upper:
            return 'status-no-forecast'
        else:
            return ''

    def _send_email(self, html_body: str) -> None:
        """
        Send email via SMTP.

        Args:
            html_body: HTML content for email body

        Raises:
            RuntimeError: If email sending fails
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = self.subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to)

            # Attach HTML content
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()

                # Authenticate if credentials provided
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)

                # Send email
                server.send_message(msg)

        except smtplib.SMTPAuthenticationError as e:
            raise RuntimeError(
                f"SMTP authentication failed. Check username and password: {str(e)}"
            ) from e
        except smtplib.SMTPException as e:
            raise RuntimeError(
                f"Failed to send email via SMTP: {str(e)}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error while sending email: {str(e)}"
            ) from e
