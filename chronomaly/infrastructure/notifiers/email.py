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
from jinja2 import Template, TemplateSyntaxError
from .base import Notifier
from chronomaly.shared import TransformableMixin


class EmailNotifier(Notifier, TransformableMixin):
    """
    Email notifier for sending anomaly alerts via SMTP.

    Sends HTML-formatted emails with anomaly data presented as a styled table.
    Optionally includes line charts for anomalous metrics when
    chart_data_reader is provided.
    Supports multiple recipients and filtering via transformers.

    SMTP credentials are read from environment variables.
    Email subject can be customized with support for date formatting.

    Args:
        to: Recipient email address(es). Can be a single email or list of emails.
        template_path: Path to HTML email template file (Jinja2 format). The template
                      must contain the required {{ table }} placeholder. Optional
                      built-in placeholders are {{ count }} and {{ plural }}.
        subject: Optional custom email subject. Supports date template variables:
                - {date} - Date from anomaly data in YYYY-MM-DD format
                - {date:FORMAT} - Anomaly date with custom strftime format
                If not specified, defaults to "Anomaly Detection Alert".
        template_variables: Optional dict of custom variables to pass to the template.
                           These can be used in the template with Jinja2 syntax.
                           Reserved names (table, count, plural) are silently ignored.
        transformers: Optional transformers to apply before notification
        chart_data_reader: Optional DataReader for loading historical
                          time series data. Metric names from anomalies must
                          match column names in the chart data. Charts are
                          generated as line plots and embedded in the email.

    Note:
        SMTP configuration is read from environment variables.
        Email subject can be customized via the subject parameter.

        For charts to work correctly, group_key names in anomalies_df['group_key'] must
        exactly match column names in the pivoted chart data.
    """

    def __init__(
        self,
        to: list[str] | str,
        template_path: str,
        subject: Optional[str] = None,
        template_variables: Optional[Dict[str, Any]] = None,
        transformers: Optional[Dict[str, list[Callable]]] = None,
        chart_data_reader: Optional[Any] = None,
    ):
        # Validate and normalize recipients
        if isinstance(to, str):
            self.to: list[str] = [to]
        elif isinstance(to, list):
            if not to:
                raise ValueError("Recipient list cannot be empty")
            if not all(isinstance(email, str) for email in to):
                raise TypeError("All recipients must be strings")
            self.to: list[str] = to
        else:
            raise TypeError("'to' must be a string or list of strings")

        self.transformers: dict[str, list[Callable]] = transformers or {}
        self.chart_data_reader: Any | None = chart_data_reader
        self._subject_template: str | None = subject
        self._template_variables: dict[str, Any] = template_variables or {}

        # Load and validate template (fail fast)
        import os

        self._template_content = self._load_and_validate_template(template_path)
        self._template_path = os.path.abspath(template_path)

        # Get SMTP configuration from internal method
        smtp_config = self._get_smtp_config()
        self.smtp_host: str = smtp_config["host"]
        self.smtp_port: int = smtp_config["port"]
        self.smtp_user: str = smtp_config["user"]
        self.smtp_password: str = smtp_config["password"]
        self.from_email: str = smtp_config["from_email"]
        self.use_tls: bool = smtp_config["use_tls"]

        # Validate SMTP credentials
        self._validate_smtp_config()

    def _get_smtp_config(self) -> Dict[str, Any]:
        """
        Get SMTP configuration from environment variables.

        Environment variables are loaded from .env file automatically.
        See .env.example for a template.

        Returns:
            dict: SMTP configuration parameters
        """
        import os

        return {
            "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
            "port": int(os.getenv("SMTP_PORT", "587")),
            "user": os.getenv("SMTP_USER", ""),
            "password": os.getenv("SMTP_PASSWORD", ""),
            "from_email": os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USER", "")),
            "use_tls": os.getenv("SMTP_USE_TLS", "True").lower()
            in ("true", "1", "yes"),
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
                f"SMTP port must be a valid port number (1-65535), "
                f"got: {self.smtp_port}"
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

    def _load_and_validate_template(self, template_path: str) -> str:
        """
        Load and validate HTML email template from file.

        Validates that:
        - File path is not empty
        - File exists at the provided path
        - File is readable
        - File contains valid content
        - Required {table} placeholder is present

        Args:
            template_path: Path to the HTML template file

        Returns:
            str: The loaded template content

        Raises:
            ValueError: If template_path is empty or missing {table} placeholder
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
            raise FileNotFoundError(f"Email template file not found: {abs_path}")

        # Check if file is readable
        if not os.access(abs_path, os.R_OK):
            raise PermissionError(
                f"Email template file is not readable: {abs_path}"
            )

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
            raise ValueError(f"Email template file is empty: {abs_path}")

        # Validate Jinja2 syntax
        try:
            Template(template_content)
        except TemplateSyntaxError as e:
            raise ValueError(
                f"Invalid Jinja2 template syntax: {str(e)}. "
                f"Template file: {abs_path}"
            ) from e

        # Validate required placeholders are present
        # Only {{ table }} is required - {{ count }} and {{ plural }} are optional
        # Check for Jinja2 syntax: {{ table }} or {{table}}
        import re
        if not re.search(r"\{\{\s*table\s*\}\}", template_content):
            raise ValueError(
                "Email template is missing required placeholder: {{ table }}. "
                "This placeholder is required to display anomaly data."
            )

        return template_content

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
        """
        # Use default subject if not specified
        subject = self._subject_template or "Anomaly Detection Alert"

        # Replace {date} placeholders if anomaly_date is provided
        if anomaly_date is not None:
            # Replace {date:FORMAT} placeholders with custom format
            date_format_pattern = r"\{date:([^}]+)\}"
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
            subject = subject.replace("{date}", anomaly_date.strftime("%Y-%m-%d"))

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

        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.dates
        from matplotlib.ticker import EngFormatter
        import io
        import base64

        # Create figure
        plt.figure(figsize=(8, 4.5))

        # Plot line chart with markers
        plt.plot(
            data.index,
            data.values,
            marker="o",
            linewidth=2,
            markersize=6,
            color="#2E86AB",
        )

        # Grid
        plt.grid(True, alpha=0.3)

        # Format x-axis dates
        ax = plt.gca()
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(matplotlib.dates.DayLocator(interval=2))
        plt.xticks(rotation=45, ha="right")

        # Format y-axis with k, M, G suffixes for large numbers
        ax.yaxis.set_major_formatter(EngFormatter())

        # Tight layout
        plt.tight_layout()

        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=75, bbox_inches="tight")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        plt.close()

        return image_base64

    def _generate_charts(self, anomalies_df: pd.DataFrame) -> Dict[str, str]:
        """
        Generate line charts for anomalous metrics.

        Args:
            anomalies_df: DataFrame containing anomaly data with 'group_key' column

        Returns:
            dict: Mapping of metric names to base64-encoded chart images
        """
        if self.chart_data_reader is None:
            return {}

        # Load chart data
        try:
            chart_data = self.chart_data_reader.load()
        except Exception:
            # If chart data loading fails, skip charts
            return {}

        # Get unique group_keys from anomalies
        anomalous_metrics = anomalies_df["group_key"].unique()

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
        if "anomalies" not in payload:
            raise ValueError("Payload must contain 'anomalies' key with DataFrame")

        anomalies_df = payload["anomalies"]

        if not isinstance(anomalies_df, pd.DataFrame):
            raise TypeError(
                f"'anomalies' must be a DataFrame, got {type(anomalies_df).__name__}"
            )

        # Extract anomaly date from the DataFrame if a 'date' column exists
        anomaly_date = None
        if "date" in anomalies_df.columns:
            try:
                # Try to get the most recent (max) date from the data
                date_series = pd.to_datetime(anomalies_df["date"])
                anomaly_date = date_series.max()
                # Check if result is NaT (happens when all dates are NaT)
                if pd.isna(anomaly_date):
                    anomaly_date = None
                # Convert to Python datetime if it's a Timestamp
                elif hasattr(anomaly_date, "to_pydatetime"):
                    anomaly_date = anomaly_date.to_pydatetime()
            except (ValueError, TypeError) as e:
                import warnings

                warnings.warn(
                    f"Failed to extract date from anomalies DataFrame: {str(e)}"
                )
                anomaly_date = None

        # Store anomaly_date for use in _send_email
        self._current_anomaly_date = anomaly_date

        # Generate charts BEFORE applying transformers (need group_key column)
        # Charts are generated using original anomalies_df with all columns
        charts = self._generate_charts(anomalies_df)

        # Apply transformers (e.g., filter only significant anomalies, select columns)
        filtered_df = self._apply_transformers(anomalies_df, "before")

        # Skip notification if no data after filtering
        if filtered_df.empty:
            return

        # Create a mapping of row data to charts
        # If group_key column exists in filtered_df, use it; otherwise use row index
        if "group_key" in filtered_df.columns:
            # Standard case: group_key column present
            chart_mapping = charts
        else:
            # group_key column removed by transformer: map by row index using original df
            chart_mapping = {}
            for idx, row in filtered_df.iterrows():
                # Find corresponding group_key in original df
                if idx in anomalies_df.index and "group_key" in anomalies_df.columns:
                    group_key = anomalies_df.loc[idx, "group_key"]
                    if group_key in charts:
                        chart_mapping[idx] = charts[group_key]

        # Generate HTML email content
        html_body = self._generate_html_body(filtered_df, chart_mapping)

        # Send email
        self._send_email(html_body)

    def _generate_html_body(
        self, df: pd.DataFrame, charts: Optional[Dict[str, str]] = None
    ) -> str:
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
        def format_value(val: Any) -> str:
            if pd.isna(val):
                return "-"
            if isinstance(val, (int, float)):
                return f"{val:.2f}"
            return str(val)

        # Helper function to get status color
        def get_status_style(status: Any) -> str:
            if pd.isna(status):
                return ""
            status_upper = str(status).upper()
            if "BELOW" in status_upper:
                return "color: #2196F3; font-weight: bold;"
            elif "ABOVE" in status_upper:
                return "color: #f44336; font-weight: bold;"
            elif "IN_RANGE" in status_upper or "IN RANGE" in status_upper:
                return "color: #4CAF50;"
            elif "NO_FORECAST" in status_upper or "NO FORECAST" in status_upper:
                return "color: #9E9E9E;"
            return ""

        # Build table HTML manually
        table_html = '<table class="anomaly-table">'

        # Table header
        table_html += "<thead><tr>"
        for col in df.columns:
            table_html += f"<th>{col}</th>"
        if charts:
            table_html += "<th>Chart</th>"
        table_html += "</tr></thead>"

        # Table body
        table_html += "<tbody>"
        for idx, row in df.iterrows():
            table_html += "<tr>"
            for col in df.columns:
                val = row[col]
                formatted_val = format_value(val)

                # Apply alert_type styling
                if col == "alert_type":
                    style = get_status_style(val)
                    table_html += f'<td style="{style}">{formatted_val}</td>'
                else:
                    table_html += f"<td>{formatted_val}</td>"

            # Add chart column if charts exist
            if charts:
                # Try to get chart by group_key name first, then by index
                chart_base64 = None
                chart_key = None

                if "group_key" in df.columns:
                    # Standard case: use group_key column
                    group_key_name = row.get("group_key", "")
                    if group_key_name in charts:
                        chart_base64 = charts[group_key_name]
                        chart_key = group_key_name
                else:
                    # group_key column removed: use row index
                    if idx in charts:
                        chart_base64 = charts[idx]
                        chart_key = str(idx)

                if chart_base64:
                    table_html += (
                        f'<td class="chart-cell">'
                        f'<img src="data:image/png;base64,{chart_base64}" '
                        f'alt="{chart_key}" class="chart-img" /></td>'
                    )
                else:
                    table_html += '<td class="chart-cell">-</td>'

            table_html += "</tr>"
        table_html += "</tbody></table>"

        # Render Jinja2 template
        try:
            template = Template(self._template_content)
            # Build context: start with custom variables, then override with built-ins
            # This ensures reserved names (table, count, plural) cannot be overridden
            context = dict(self._template_variables)
            context.update({
                "count": len(df),
                "plural": "ies" if len(df) != 1 else "y",
                "table": table_html,
            })
            html = template.render(**context)
        except Exception as e:
            raise RuntimeError(
                f"Failed to render Jinja2 template: {str(e)}. "
                f"Template file: {self._template_path}"
            ) from e

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
            msg = MIMEMultipart("alternative")
            msg["Subject"] = self._get_email_subject(
                getattr(self, "_current_anomaly_date", None)
            )
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to)

            # Attach HTML content
            html_part = MIMEText(html_body, "html")
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
            raise RuntimeError(f"Failed to send email via SMTP: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error while sending email: {str(e)}") from e
