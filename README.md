# Chronomaly

**Chronomaly** is a flexible and extensible Python library for time series forecasting and anomaly detection using Google TimesFM.

## Table of Contents

- [Problem / Motivation](#problem--motivation)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Forecast Workflow](#forecast-workflow)
  - [Anomaly Detection Workflow](#anomaly-detection-workflow)
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
- **Data Transformations**:
  - PivotTransformer: Pivots data into time series format
  - Filters: Value filtering, cumulative threshold filtering
  - Formatters: Column formatting with built-in percentage helper
- **Anomaly Detection**: Quantile-based anomaly detection (BELOW_LOWER, IN_RANGE, ABOVE_UPPER)
- **Modular Architecture**: Each component can be used independently and is easily extensible
- **Type Safety**: Safe code writing with type hints

---

## Installation

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/sinancan34/chronomaly.git
cd chronomaly

# Install core dependencies
pip install -r requirements.txt

# Install TimesFM from GitHub (required)
pip install git+https://github.com/google-research/timesfm.git

# Install Chronomaly in editable mode
pip install -e .
```

### Optional Dependencies

```bash
# For BigQuery support
pip install -e ".[bigquery]"

# For development tools (pytest, black, flake8)
pip install -e ".[dev]"

# All optional dependencies
pip install -e ".[all]"
```

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

# BigQuery reader
reader = BigQueryDataReader(
    service_account_file="path/to/service-account.json",
    project="my-gcp-project",
    query="""
        SELECT date, metric_name, value
        FROM `project.dataset.table`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    """,
    date_column="date"
)

# BigQuery writer
writer = BigQueryDataWriter(
    service_account_file="path/to/service-account.json",
    project="my-gcp-project",
    dataset="my_dataset",
    table="forecasts",
    write_disposition="WRITE_APPEND"
)

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

### Data Sources

Chronomaly supports various data sources:

#### CSV Files

```python
from chronomaly.infrastructure.data.readers.files import CSVDataReader

# CSV reader (for reading data)
reader = CSVDataReader(
    file_path="data/input.csv",
    date_column="date"
)

# Note: CSV writer is not yet implemented. Use SQLite or BigQuery writers for output.
```

#### SQLite

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

#### BigQuery

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
│       └── anomaly_detection_workflow.py
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
│   │   └── formatters/
│   ├── data/             # Data reading/writing
│   │   ├── readers/
│   │   │   ├── files/    # CSV, etc.
│   │   │   ├── databases/  # SQLite, BigQuery
│   │   │   └── apis/     # API integrations
│   │   └── writers/
│   │       ├── files/
│   │       └── databases/
│   └── notifiers/        # Notification system (extensible)
└── shared/               # Shared utilities
```

### Core Components

- **Workflows**: Orchestrate business workflows (ForecastWorkflow, AnomalyDetectionWorkflow)
- **Forecasters**: Forecasting models (TimesFMForecaster)
- **AnomalyDetectors**: Anomaly detection algorithms (ForecastActualAnomalyDetector)
- **Transformers**: Data transformations (PivotTransformer, Filters, Formatters)
- **DataReaders**: Data reading (CSV, SQLite, BigQuery)
- **DataWriters**: Data writing (SQLite, BigQuery)

---

## Contributing

We welcome contributions! Here's how you can contribute:

### Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit your changes: `git commit -m 'feat: Add new feature'`
4. Push your branch: `git push origin feature/new-feature`
5. Open a Pull Request

### Coding Standards

- **Type Hints**: Use type hints in all functions
- **Docstrings**: Add docstrings for every class and function
- **Testing**: Write tests for new features
- **Code Style**: Format code with Black and flake8

```bash
# Run tests
pytest

# Code formatting
black chronomaly/

# Linting
flake8 chronomaly/
```

### Commit Messages

Use Conventional Commits format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Add/fix tests
- `chore:` Maintenance tasks

### Adding New Data Sources

To add a new data source:

1. Inherit from `DataReader` or `DataWriter` base class
2. Implement the `load()` or `write()` method
3. Write tests
4. Add documentation

Example:

```python
from chronomaly.infrastructure.data.readers.base import DataReader
import pandas as pd

class MyCustomReader(DataReader):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def load(self) -> pd.DataFrame:
        # Your implementation
        pass
```

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

## Roadmap

Features planned for future releases:

- [ ] **Additional Forecaster Models**: Prophet, ARIMA, LSTM support
- [ ] **Advanced Anomaly Detection**: ML-based anomaly detection
- [ ] **Visualization**: Forecast and anomaly visualization tools
- [ ] **API Server**: Forecasting service via REST API
- [ ] **Notifier Integrations**: Slack, Email, PagerDuty notifications
- [ ] **AutoML**: Automatic model selection and hyperparameter optimization
- [ ] **Multi-variate Forecasting**: Multi-variable time series support
- [ ] **Real-time Streaming**: Real-time forecasting on streaming data

---

**Build powerful time series forecasts and anomaly detection with Chronomaly!**
