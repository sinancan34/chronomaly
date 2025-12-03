"""
Email notifier implementation.
"""

import smtplib
import re
from datetime import datetime
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, Callable
from .base import Notifier
from chronomaly.shared import TransformableMixin


class EmailNotifier(Notifier, TransformableMixin):
    """
    Email notifier for sending anomaly alerts via SMTP.

    Sends HTML-formatted emails with anomaly data presented as a styled table.
    Optionally includes line charts for anomalous metrics when chart_data_reader is provided.
    Supports multiple recipients and filtering via transformers.

    SMTP credentials are read from environment variables.
    Email subject can be customized with support for date formatting.

    Args:
        to: Recipient email address(es). Can be a single email or list of emails.
        subject: Optional custom email subject. Supports date template variables:
                - {date} - Date from anomaly data in YYYY-MM-DD format
                - {date:FORMAT} - Anomaly date with custom strftime format
                If not specified, defaults to "Anomaly Detection Alert".
        transformers: Optional transformers to apply before notification
                     Example: {'before': [ValueFilter(...)]} to filter anomalies
        chart_data_reader: Optional DataReader for loading historical time series data.
                          Metric names from anomalies must match column names in the chart data.
                          Charts are generated as line plots and embedded in the email.

    Example:
        from chronomaly.infrastructure.notifiers import EmailNotifier
        from chronomaly.infrastructure.transformers.filters import ValueFilter
        from chronomaly.infrastructure.transformers.formatters import ColumnSelector
        from chronomaly.infrastructure.data.readers import BigQueryDataReader
        from chronomaly.infrastructure.transformers import PivotTransformer

        # Basic usage with default subject
        notifier = EmailNotifier(
            to=["team@example.com", "manager@example.com"]
        )

        # Custom subject with anomaly date
        notifier = EmailNotifier(
            to=["team@example.com"],
            subject="Daily Anomaly Report - {date}"
        )

        # Custom subject with formatted anomaly date
        notifier = EmailNotifier(
            to=["team@example.com"],
            subject="Anomalies for {date:%d %B %Y}"
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

        # With charts - show historical trends for anomalous metrics
        chart_reader = BigQueryDataReader(
            service_account_file="/path/to/service-account.json",
            project="my-project",
            query=\"\"\"
                SELECT date, platform, channel, metric_name, SUM(value) AS value
                FROM `my-project.dataset.table_*`
                WHERE _TABLE_SUFFIX BETWEEN '20251020' AND '20251116'
                GROUP BY date, platform, channel, metric_name
                ORDER BY date
            \"\"\",
            date_column="date",
            transformers={
                'after': [
                    PivotTransformer(
                        index=['date'],
                        columns=['platform', 'channel', 'metric_name'],
                        values='value'
                    )
                ]
            }
        )

        notifier = EmailNotifier(
            to=["team@example.com"],
            transformers={
                'before': [
                    ColumnSelector(['date', 'metric'], mode='drop')
                ]
            },
            chart_data_reader=chart_reader
        )

        # Send notification
        payload = {'anomalies': anomalies_df}
        notifier.notify(payload)

    Note:
        SMTP configuration is read from environment variables.
        Email subject can be customized via the subject parameter.

        For charts to work correctly, metric names in anomalies_df['metric'] must
        exactly match column names in the pivoted chart data.
    """

    def __init__(
        self,
        to: list[str] | str,
        subject: Optional[str] = None,
        transformers: Optional[Dict[str, list[Callable]]] = None,
        chart_data_reader: Optional[Any] = None
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
        self.chart_data_reader = chart_data_reader
        self._subject_template = subject

        # Get SMTP configuration from internal method
        smtp_config = self._get_smtp_config()
        self.smtp_host = smtp_config['host']
        self.smtp_port = smtp_config['port']
        self.smtp_user = smtp_config['user']
        self.smtp_password = smtp_config['password']
        self.from_email = smtp_config['from_email']
        self.use_tls = smtp_config['use_tls']

        # Validate SMTP credentials
        self._validate_smtp_config()

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

    def _validate_smtp_config(self) -> None:
        """
        Validate SMTP configuration.

        Raises:
            ValueError: If required SMTP credentials are missing or invalid
        """
        if not self.smtp_host:
            raise ValueError(
                "SMTP host is required. Set SMTP_HOST environment variable."
            )

        if not isinstance(self.smtp_port, int) or not (1 <= self.smtp_port <= 65535):
            raise ValueError(
                f"SMTP port must be a valid port number (1-65535), got: {self.smtp_port}"
            )

        if not self.smtp_user:
            raise ValueError(
                "SMTP username is required. Set SMTP_USER environment variable."
            )

        if not self.smtp_password:
            raise ValueError(
                "SMTP password is required. Set SMTP_PASSWORD environment variable."
            )

        if not self.from_email:
            raise ValueError(
                "From email address is required. "
                "Set SMTP_FROM_EMAIL or SMTP_USER environment variable."
            )

    def _get_email_subject(self, anomaly_date: Optional[datetime] = None) -> str:
        """
        Get email subject line with processed date templates.

        Processes template variables in the subject:
        - {date} -> Date from anomaly data in YYYY-MM-DD format
        - {date:FORMAT} -> Anomaly date with custom strftime format

        Args:
            anomaly_date: Optional datetime extracted from anomaly data

        Returns:
            str: Processed email subject line

        Examples:
            Template: "Daily Report - {date}"
            Result: "Daily Report - 2025-12-02"

            Template: "Report {date:%d.%m.%Y}"
            Result: "Report 02.12.2025"
        """
        # Use default subject if not specified
        subject = self._subject_template or "Anomaly Detection Alert"

        # Replace {date} placeholders if anomaly_date is provided
        if anomaly_date is not None:
            # Replace {date:FORMAT} placeholders with custom format
            date_format_pattern = r'\{date:([^}]+)\}'
            matches = re.finditer(date_format_pattern, subject)
            for match in matches:
                format_string = match.group(1)
                try:
                    formatted_date = anomaly_date.strftime(format_string)
                    subject = subject.replace(match.group(0), formatted_date)
                except (ValueError, TypeError) as e:
                    import warnings
                    warnings.warn(
                        f"Invalid date format '{format_string}' in email subject. "
                        f"Error: {str(e)}"
                    )

            # Replace simple {date} placeholder (must be done after custom formats)
            subject = subject.replace('{date}', anomaly_date.strftime('%Y-%m-%d'))

        return subject

    def _create_line_chart(self, metric_name: str, data: pd.Series) -> str:
        """
        Create a line chart for a single metric and return as base64 string.

        Args:
            metric_name: Name of the metric
            data: Time series data (Series with DatetimeIndex)

        Returns:
            str: Base64-encoded PNG image
        """
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.dates
        import io
        import base64

        # Create figure
        plt.figure(figsize=(8, 4.5))

        # Plot line chart with markers
        plt.plot(data.index, data.values, marker='o', linewidth=2, markersize=6, color='#2E86AB')

        # Grid
        plt.grid(True, alpha=0.3)

        # Format x-axis dates
        ax = plt.gca()
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(matplotlib.dates.DayLocator(interval=2))
        plt.xticks(rotation=45, ha='right')

        # Tight layout
        plt.tight_layout()

        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()

        return image_base64

    def _generate_charts(self, anomalies_df: pd.DataFrame) -> Dict[str, str]:
        """
        Generate line charts for anomalous metrics.

        Args:
            anomalies_df: DataFrame containing anomaly data with 'metric' column

        Returns:
            dict: Mapping of metric names to base64-encoded chart images
        """
        if self.chart_data_reader is None:
            return {}

        # Load chart data
        try:
            chart_data = self.chart_data_reader.load()
        except Exception as e:
            # If chart data loading fails, skip charts
            return {}

        # Get unique metrics from anomalies
        anomalous_metrics = anomalies_df['metric'].unique()

        # Generate charts for each metric
        charts = {}
        for metric in anomalous_metrics:
            # Check if metric exists in chart data columns
            if metric in chart_data.columns:
                metric_data = chart_data[metric]

                # Skip if all NaN
                if metric_data.notna().any():
                    try:
                        chart_base64 = self._create_line_chart(metric, metric_data)
                        charts[metric] = chart_base64
                    except (ValueError, TypeError, RuntimeError) as e:
                        import warnings
                        warnings.warn(
                            f"Failed to generate chart for metric '{metric}': {str(e)}"
                        )
                        continue

        return charts

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

        # Extract anomaly date from the DataFrame if a 'date' column exists
        anomaly_date = None
        if 'date' in anomalies_df.columns:
            try:
                # Try to get the most recent (max) date from the data
                date_series = pd.to_datetime(anomalies_df['date'])
                anomaly_date = date_series.max()
                # Convert to Python datetime if it's a Timestamp
                if hasattr(anomaly_date, 'to_pydatetime'):
                    anomaly_date = anomaly_date.to_pydatetime()
            except (ValueError, TypeError) as e:
                import warnings
                warnings.warn(
                    f"Failed to extract date from anomalies DataFrame: {str(e)}"
                )
                anomaly_date = None

        # Store anomaly_date for use in _send_email
        self._current_anomaly_date = anomaly_date

        # Generate charts BEFORE applying transformers (need metric column)
        # Charts are generated using original anomalies_df with all columns
        charts = self._generate_charts(anomalies_df)

        # Apply transformers (e.g., filter only significant anomalies, select columns)
        filtered_df = self._apply_transformers(anomalies_df, 'before')

        # Skip notification if no data after filtering
        if filtered_df.empty:
            return

        # Create a mapping of row data to charts
        # If metric column exists in filtered_df, use it; otherwise use row index
        if 'metric' in filtered_df.columns:
            # Standard case: metric column present
            chart_mapping = charts
        else:
            # Metric column removed by transformer: map by row index using original df
            chart_mapping = {}
            for idx, row in filtered_df.iterrows():
                # Find corresponding metric in original df
                if idx in anomalies_df.index and 'metric' in anomalies_df.columns:
                    metric = anomalies_df.loc[idx, 'metric']
                    if metric in charts:
                        chart_mapping[idx] = charts[metric]

        # Generate HTML email content
        html_body = self._generate_html_body(filtered_df, chart_mapping)

        # Send email
        self._send_email(html_body)

    def _generate_html_body(self, df: pd.DataFrame, charts: Optional[Dict[str, str]] = None) -> str:
        """
        Generate HTML email body with styled table and optional charts.

        Args:
            df: DataFrame with anomaly data
            charts: Optional dict mapping metric names to base64-encoded chart images

        Returns:
            str: HTML content
        """
        charts = charts or {}

        # Helper function to format numeric values
        def format_value(val):
            if pd.isna(val):
                return '-'
            if isinstance(val, (int, float)):
                return f'{val:.2f}'
            return str(val)

        # Helper function to get status color
        def get_status_style(status):
            if pd.isna(status):
                return ''
            status_upper = str(status).upper()
            if 'BELOW' in status_upper:
                return 'color: #2196F3; font-weight: bold;'
            elif 'ABOVE' in status_upper:
                return 'color: #f44336; font-weight: bold;'
            elif 'IN_RANGE' in status_upper or 'IN RANGE' in status_upper:
                return 'color: #4CAF50;'
            elif 'NO_FORECAST' in status_upper or 'NO FORECAST' in status_upper:
                return 'color: #9E9E9E;'
            return ''

        # Build table HTML manually
        table_html = '<table class="anomaly-table">'

        # Table header
        table_html += '<thead><tr>'
        for col in df.columns:
            table_html += f'<th>{col}</th>'
        if charts:
            table_html += '<th>Chart</th>'
        table_html += '</tr></thead>'

        # Table body
        table_html += '<tbody>'
        for idx, row in df.iterrows():
            table_html += '<tr>'
            for col in df.columns:
                val = row[col]
                formatted_val = format_value(val)

                # Apply status styling
                if col == 'status':
                    style = get_status_style(val)
                    table_html += f'<td style="{style}">{formatted_val}</td>'
                else:
                    table_html += f'<td>{formatted_val}</td>'

            # Add chart column if charts exist
            if charts:
                # Try to get chart by metric name first, then by index
                chart_base64 = None
                chart_key = None

                if 'metric' in df.columns:
                    # Standard case: use metric column
                    metric_name = row.get('metric', '')
                    if metric_name in charts:
                        chart_base64 = charts[metric_name]
                        chart_key = metric_name
                else:
                    # Metric column removed: use row index
                    if idx in charts:
                        chart_base64 = charts[idx]
                        chart_key = str(idx)

                if chart_base64:
                    table_html += f'<td class="chart-cell"><img src="data:image/png;base64,{chart_base64}" alt="{chart_key}" class="chart-img" /></td>'
                else:
                    table_html += '<td class="chart-cell">-</td>'

            table_html += '</tr>'
        table_html += '</tbody></table>'

        # Email header with CSS
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
                    overflow-x: auto;
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
                .anomaly-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                .anomaly-table th {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-weight: bold;
                    white-space: nowrap;
                }}
                .anomaly-table td {{
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                    vertical-align: middle;
                }}
                .anomaly-table tr:hover {{
                    background-color: #f5f5f5;
                }}
                .chart-cell {{
                    text-align: center;
                    padding: 5px;
                    width: 320px;
                }}
                .chart-img {{
                    max-width: 300px;
                    height: auto;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
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
                {table}
                <div class="footer">
                    This is an automated alert from Chronomaly anomaly detection system.
                </div>
            </div>
        </body>
        </html>
        """.format(
            count=len(df),
            plural="ies" if len(df) != 1 else "y",
            table=table_html
        )

        return html

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
            msg['Subject'] = self._get_email_subject(getattr(self, '_current_anomaly_date', None))
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
