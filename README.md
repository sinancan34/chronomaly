# Chronomaly

**Chronomaly** is a flexible and extensible Python library for time series forecasting and anomaly detection using Google TimesFM.

## Table of Contents

- [Problem / Motivation](#problem--motivation)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Forecast Workflow](#forecast-workflow)
  - [Anomaly Detection Workflow](#anomaly-detection-workflow)
  - [Notification Workflow](#notification-workflow)
- [Data Sources](#data-sources)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)
- [Contact / Support](#contact--support)
- [Roadmap](#roadmap)

---

## Problem / Motivation

Time series forecasting and anomaly detection are critical needs in modern data analytics. However:

- **Complexity**: Setting up and managing powerful forecasting models (e.g., Google TimesFM) is technically challenging
- **Data Integration**: Reading from and writing to different sources (BigQuery, SQLite, CSV, APIs) requires repetitive code
- **Lack of Flexibility**: Most solutions are not flexible enough for data transformations, filtering, and formatting
- **Anomaly Detection**: Comparing forecasted values with actual values to detect anomalies is a manual process

**Chronomaly** is designed to solve these problems:

- Provides powerful forecasts using Google's state-of-the-art TimesFM model
- Offers ready-to-use reader/writer implementations for multiple data sources
- Supports flexible data transformations with a pipeline-based architecture
- Automatically detects anomalies by comparing forecast and actual data
- Easily extensible thanks to its modular design

---

## Features

- **Google TimesFM Integration**: State-of-the-art time series forecasting model support
- **Multiple Data Sources**:
  - Readers: CSV, SQLite, BigQuery
  - Writers: SQLite, BigQuery
  - API reader support (extensible)
- **Flexible Workflow Orchestration**:
  - ForecastWorkflow: Data reading, transformation, forecasting, writing
  - AnomalyDetectionWorkflow: Forecast vs actual comparison
  - NotificationWorkflow: Multi-channel anomaly alerting (email, Slack, etc.)
- **Data Transformations**:
  - PivotTransformer: Pivots data into time series format
  - Filters: Value filtering, cumulative threshold filtering
  - Formatters: Column formatting with built-in percentage helper
- **Anomaly Detection**: Quantile-based anomaly detection (BELOW_LOWER, IN_RANGE, ABOVE_UPPER)
- **Alert Notifications**: Email notifications with HTML formatting and filtering support
- **Modular Architecture**: Each component can be used independently and is easily extensible
- **Type Safety**: Safe code writing with type hints

---

## Installation

### Prerequisites

- Python 3.11, 3.12 or 3.13
- pip package manager

### Installation

```bash
pip install git+https://github.com/sinancan34/chronomaly.git
```

### Development Installation

For contributors who want to modify the source code:

```bash
git clone https://github.com/sinancan34/chronomaly.git
cd chronomaly
pip install -e .
```

### Optional Dependencies

```bash
# For TimesFM Flax backend (alternative to default PyTorch backend)
pip install -e ".[flax]"

# For exogenous regressors support in TimesFM
pip install -e ".[xreg]"
```

> **Note**: BigQuery support is included in the base installation.

---

## Configuration

Before using workflows that require external services (email notifications, BigQuery, etc.), configure environment variables:

```python
import chronomaly

# Load environment variables from .env file in current directory
chronomaly.configure()

# Or specify a custom path
chronomaly.configure(env_file_path='/path/to/your/.env')
```

Create a `.env` file with your settings (see [SMTP Configuration](#smtp-configuration) for email setup).

---

## Usage

### Forecast Workflow

ForecastWorkflow orchestrates data reading, transformation, forecast generation, and writing.

#### Example: Reading from CSV and Pivot Transformation

```python
from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.transformers import PivotTransformer

# CSV reader with pivot transformation applied after loading
reader = CSVDataReader(
    file_path="data/raw_data.csv",
    date_column="date",
    transformers={
        'after': [
            PivotTransformer(
                index='date',
                columns=['platform', 'channel'],  # Dimensions
                values='sessions'  # Value column
            )
        ]
    }
)

# SQLite writer
writer = SQLiteDataWriter(
    db_path="output/forecasts.db",
    table_name="forecasts"
)

# Forecaster
forecaster = TimesFMForecaster(frequency='D')

# Workflow (no transformer parameter - transformations are at component level)
workflow = ForecastWorkflow(
    data_reader=reader,
    forecaster=forecaster,
    data_writer=writer
)

# 7-day forecast
forecast_df = workflow.run(horizon=7)
```

#### Example: Reading from BigQuery

```python
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter
from chronomaly.infrastructure.transformers import PivotTransformer

# BigQuery reader with pivot transformation
reader = BigQueryDataReader(
    service_account_file="path/to/service-account.json",
    project="my-gcp-project",
    query="""
        SELECT date, platform, channel, sessions
        FROM `project.dataset.table`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    """,
    date_column="date",
    transformers={
        'after': [
            PivotTransformer(
                index='date',
                columns=['platform', 'channel'],
                values='sessions'
            )
        ]
    }
)

# BigQuery writer
writer = BigQueryDataWriter(
    service_account_file="path/to/service-account.json",
    project="my-gcp-project",
    dataset="my_dataset",
    table="forecasts",
    write_disposition="WRITE_APPEND"
)

# Forecaster
forecaster = TimesFMForecaster(frequency='D')

# Create and run workflow
workflow = ForecastWorkflow(
    data_reader=reader,
    forecaster=forecaster,
    data_writer=writer
)

forecast_df = workflow.run(horizon=14)
```

### Anomaly Detection Workflow

AnomalyDetectionWorkflow detects anomalies by comparing forecasted values with actual values.

#### Example: Basic Anomaly Detection

```python
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter
from chronomaly.infrastructure.anomaly_detectors import ForecastActualAnomalyDetector
from chronomaly.infrastructure.transformers import PivotTransformer

# Forecast data reader (reads forecast results from previous workflow run)
forecast_reader = BigQueryDataReader(
    service_account_file="path/to/service-account.json",
    project="my-project",
    query="SELECT * FROM `project.dataset.forecasts` WHERE date = CURRENT_DATE()",
    date_column="date"
)

# Actual data reader (reads real/observed values to compare against forecasts)
# Note: Pivot transformation is applied after loading the data
actual_reader = BigQueryDataReader(
    service_account_file="path/to/service-account.json",
    project="my-project",
    query="""
        SELECT date, platform, channel, sessions
        FROM `project.dataset.actuals`
        WHERE date = CURRENT_DATE()
    """,
    date_column="date",
    transformers={
        'after': [
            PivotTransformer(
                index='date',
                columns=['platform', 'channel'],
                values='sessions'
            )
        ]
    }
)

# Anomaly writer
anomaly_writer = BigQueryDataWriter(
    service_account_file="path/to/service-account.json",
    project="my-project",
    dataset="analytics",
    table="anomalies"
)

# Anomaly detector (no transformer parameter - data is already pivoted by reader)
detector = ForecastActualAnomalyDetector(
    date_column='date',
    dimension_names=['platform', 'channel'],  # Split metric into these dimensions
    lower_quantile_idx=1,  # q10
    upper_quantile_idx=9   # q90
)

# Workflow
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=anomaly_writer
)

# Detect anomalies
anomalies_df = workflow.run()
print(anomalies_df[anomalies_df['status'] != 'IN_RANGE'])
```

#### Example: Anomaly Detection with Filtering and Formatting

```python
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.transformers.filters import (
    ValueFilter,
    CumulativeThresholdFilter
)
from chronomaly.infrastructure.transformers.formatters import ColumnFormatter

# Configure transformations at detector level (not workflow level)
detector = ForecastActualAnomalyDetector(
    date_column='date',
    dimension_names=['platform', 'channel'],
    lower_quantile_idx=1,
    upper_quantile_idx=9,
    transformers={
        'after': [
            # Filter only significant anomalies
            CumulativeThresholdFilter('forecast', threshold_pct=0.95),
            # Filter only anomalies (exclude IN_RANGE)
            ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER'], mode='include'),
            # Filter minimum deviation
            ValueFilter('deviation_pct', min_value=0.05),  # 5% minimum deviation
            # Percentage formatting using helper method
            ColumnFormatter.percentage(
                columns='deviation_pct',
                decimal_places=1,
                multiply_by_100=True  # Convert 0.05 → "5.0%"
            )
        ]
    }
)

# Workflow (transformations are handled by detector)
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=anomaly_writer
)

anomalies_df = workflow.run()
```

### Notification Workflow

NotificationWorkflow sends alerts about detected anomalies via multiple channels (email, Slack, etc.). It integrates seamlessly with AnomalyDetectionWorkflow to notify teams about significant anomalies.

#### Example: Email Notifications with Environment Variables

```python
from chronomaly.application.workflows import NotificationWorkflow
from chronomaly.infrastructure.notifiers import EmailNotifier
from chronomaly.infrastructure.transformers.filters import ValueFilter

# First, run anomaly detection
anomalies_df = anomaly_workflow.run()

# Configure email notifier (reads SMTP settings from environment variables)
# Set these in your .env file:
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your-email@gmail.com
# SMTP_PASSWORD=your-app-password
# SMTP_FROM_EMAIL=alerts@example.com (optional, defaults to SMTP_USER)

email_notifier = EmailNotifier(
    to=["team@example.com", "manager@example.com"]
)

# Create and run notification workflow
notification_workflow = NotificationWorkflow(
    anomalies_data=anomalies_df,
    notifiers=[email_notifier]
)

notification_workflow.run()
```

#### Example: Email Notifications with Filters

Only notify for significant anomalies:

```python
from chronomaly.infrastructure.transformers.filters import ValueFilter

# Configure email notifier with filters
email_notifier = EmailNotifier(
    to=["team@example.com"],
    transformers={
        'before': [
            # Only email actual anomalies (not IN_RANGE)
            ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER'], mode='include'),
            # Only notify for deviations > 10%
            ValueFilter('deviation_pct', min_value=0.1)
        ]
    }
)

notification_workflow = NotificationWorkflow(
    anomalies_data=anomalies_df,
    notifiers=[email_notifier]
)

notification_workflow.run()
```

#### Example: Multiple Notification Channels

Send notifications to multiple channels simultaneously:

```python
# Configure multiple notifiers
critical_email = EmailNotifier(
    to=["oncall@example.com"],
    transformers={
        'before': [
            # Only critical anomalies (>20% deviation)
            ValueFilter('deviation_pct', min_value=0.2),
            ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER'], mode='include')
        ]
    }
)

team_email = EmailNotifier(
    to=["analytics-team@example.com"],
    transformers={
        'before': [
            # All anomalies (>5% deviation)
            ValueFilter('deviation_pct', min_value=0.05),
            ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER'], mode='include')
        ]
    }
)

# Send to multiple channels
notification_workflow = NotificationWorkflow(
    anomalies_data=anomalies_df,
    notifiers=[critical_email, team_email]  # Both will receive filtered data
)

notification_workflow.run()
```

#### SMTP Configuration

EmailNotifier reads SMTP settings from environment variables. Create a `.env` file in your project root:

```bash
# .env file
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=alerts@example.com  # Optional, defaults to SMTP_USER
SMTP_USE_TLS=True  # Optional, defaults to True
```

**Gmail Users**: For Gmail, you need to:
1. Enable 2-factor authentication
2. Generate an [App Password](https://support.google.com/accounts/answer/185833)
3. Use the app password as `SMTP_PASSWORD`

---

## Data Sources

Chronomaly supports various data sources:

### CSV Files

```python
from chronomaly.infrastructure.data.readers.files import CSVDataReader

# CSV reader (for reading data)
reader = CSVDataReader(
    file_path="data/input.csv",
    date_column="date"
)

# Note: CSV writer is not yet implemented. Use SQLite or BigQuery writers for output.
```

### SQLite

```python
from chronomaly.infrastructure.data.readers.databases import SQLiteDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter

reader = SQLiteDataReader(
    db_path="data/mydb.sqlite",
    table_name="time_series",
    date_column="date"
)

writer = SQLiteDataWriter(
    db_path="output/forecasts.db",
    table_name="forecasts"
)
```

### BigQuery

```python
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter

reader = BigQueryDataReader(
    service_account_file="path/to/credentials.json",
    project="my-gcp-project",
    query="SELECT * FROM `dataset.table` WHERE date > '2024-01-01'",
    date_column="date"
)

writer = BigQueryDataWriter(
    service_account_file="path/to/credentials.json",
    project="my-gcp-project",
    dataset="analytics",
    table="forecasts"
)
```

---

## Architecture

Chronomaly follows Clean Architecture principles with a layered structure:

```
chronomaly/
├── application/          # Application layer (workflows)
│   └── workflows/
│       ├── forecast_workflow.py
│       ├── anomaly_detection_workflow.py
│       └── notification_workflow.py
├── infrastructure/       # Infrastructure layer (implementations)
│   ├── forecasters/      # Forecasting models
│   │   ├── base.py
│   │   └── timesfm.py
│   ├── anomaly_detectors/  # Anomaly detection algorithms
│   │   ├── base.py
│   │   └── forecast_actual.py
│   ├── transformers/     # Data transformations
│   │   ├── pivot.py
│   │   ├── filters/
│   │   │   ├── value_filter.py
│   │   │   └── cumulative_threshold.py
│   │   └── formatters/
│   │       ├── column_formatter.py
│   │       └── column_selector.py
│   ├── data/             # Data reading/writing
│   │   ├── readers/
│   │   │   ├── base.py
│   │   │   ├── dataframe_reader.py  # In-memory DataFrame
│   │   │   ├── files/    # CSV, etc.
│   │   │   ├── databases/  # SQLite, BigQuery
│   │   │   └── apis/     # API integrations
│   │   └── writers/
│   │       ├── files/
│   │       └── databases/
│   ├── notifiers/        # Notification system
│   │   ├── base.py
│   │   └── email.py      # Email notifier (SMTP)
│   └── visualizers/      # Visualization components
└── shared/               # Shared utilities
    └── mixins.py         # TransformableMixin
```

### Core Components

- **Workflows**: Orchestrate business workflows (ForecastWorkflow, AnomalyDetectionWorkflow, NotificationWorkflow)
- **Forecasters**: Forecasting models (TimesFMForecaster)
- **AnomalyDetectors**: Anomaly detection algorithms (ForecastActualAnomalyDetector)
- **Transformers**: Data transformations (PivotTransformer, Filters, Formatters, ColumnSelector)
- **DataReaders**: Data reading (CSV, SQLite, BigQuery, DataFrame)
- **DataWriters**: Data writing (SQLite, BigQuery)
- **Notifiers**: Alert notifications (EmailNotifier with SMTP support)

---

## Contributing

We welcome contributions! Please read our [Contributing Guidelines](CONTRIBUTING.md) for detailed information on how to contribute to this project.

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes following our [coding standards](CONTRIBUTING.md#coding-standards)
4. Write tests for your changes
5. Commit using [Conventional Commits](https://www.conventionalcommits.org/) format
6. Push your branch: `git push origin feature/new-feature`
7. Open a Pull Request

For more details, see:
- [Contributing Guidelines](CONTRIBUTING.md) - Detailed contribution instructions
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community guidelines
- [Security Policy](SECURITY.md) - How to report security vulnerabilities

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).

---

## Contact / Support

### Issue Reporting

If you found a bug or have a suggestion:

- **GitHub Issues**: [https://github.com/sinancan34/chronomaly/issues](https://github.com/sinancan34/chronomaly/issues)
- When opening an issue, please:
  - Clearly describe the problem
  - Include steps to reproduce the error
  - Specify expected and actual behavior
  - Provide Python version and OS information

### Questions and Discussions

- **GitHub Discussions**: For general questions and discussions
- **Pull Requests**: For code contributions

### Documentation

- **GitHub Repository**: [https://github.com/sinancan34/chronomaly](https://github.com/sinancan34/chronomaly)
- In-code docstrings and type hints provide detailed usage information

---

**Build powerful time series forecasts and anomaly detection with Chronomaly!**
