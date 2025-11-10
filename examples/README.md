# Chronomaly Examples

Complete workflow examples for time series forecasting and anomaly detection.

## 📁 Directory Structure

```
examples/
├── forecast/          # Forecasting workflow examples
├── anomaly/          # Anomaly detection workflow examples
└── advanced/         # Advanced usage patterns
```

## 🔮 Forecast Workflows

Learn how to create forecasts from different data sources:

| Example | Source | Destination | Description |
|---------|--------|-------------|-------------|
| `csv_to_csv_forecast.py` | CSV | CSV | Basic forecasting pipeline |
| `csv_to_sqlite_forecast.py` | CSV | SQLite | Forecast to database |
| `sqlite_to_sqlite_forecast.py` | SQLite | SQLite | Database-to-database |
| `bigquery_forecast.py` | BigQuery | BigQuery | Cloud forecasting (info) |

## 🔍 Anomaly Detection Workflows

Detect anomalies by comparing forecasts with actual values:

| Example | Forecast Source | Actual Source | Output | Description |
|---------|----------------|---------------|--------|-------------|
| `csv_to_sqlite_anomaly.py` | CSV | CSV | SQLite | CSV sources to DB |
| `sqlite_anomaly.py` | SQLite | SQLite | SQLite | All-database pipeline |
| `mixed_sources_anomaly.py` | SQLite | CSV | SQLite | Mixed data sources |
| `bigquery_anomaly.py` | BigQuery | BigQuery | BigQuery | Cloud anomaly (info) |

## 🚀 Advanced Workflows

Complex patterns and best practices:

| Example | Description |
|---------|-------------|
| `anomaly_with_filters.py` | General-purpose transformers (filters & formatters) |
| `custom_confidence_intervals.py` | Different quantile configurations |
| `end_to_end_pipeline.py` | Complete data → forecast → anomaly → report |

## 🏃 Quick Start

```bash
# Forecast example
python examples/forecast/csv_to_csv_forecast.py

# Anomaly detection example
python examples/anomaly/csv_to_sqlite_anomaly.py

# Advanced example
python examples/advanced/anomaly_with_filters.py
```

## 📚 Learning Path

1. **Start with forecasting**: `forecast/csv_to_csv_forecast.py`
2. **Try anomaly detection**: `anomaly/csv_to_sqlite_anomaly.py`
3. **Learn filtering**: `advanced/anomaly_with_filters.py`
4. **Build complete pipelines**: `advanced/end_to_end_pipeline.py`

## 💡 Common Patterns

### Pattern 1: Simple Forecast
```python
from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter

reader = CSVDataReader('data.csv')
forecaster = TimesFMForecaster()
writer = SQLiteDataWriter('forecasts.db', 'forecasts')

workflow = ForecastWorkflow(reader, forecaster, writer)
workflow.run()
```

### Pattern 2: Anomaly Detection
```python
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.anomaly_detectors import ForecastActualAnomalyDetector

detector = ForecastActualAnomalyDetector(transformer, lower_quantile_idx=1, upper_quantile_idx=9)

workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=writer
)
workflow.run()
```

### Pattern 3: With Transformers
```python
from chronomaly.infrastructure.transformers.filters import ValueFilter
from chronomaly.infrastructure.transformers.formatters import ColumnFormatter

workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=writer,
    transformers={
        'after_detection': [
            ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER']),
            ValueFilter('deviation_pct', min_value=10.0),
            ColumnFormatter.percentage('deviation_pct', decimal_places=1)
        ]
    }
)
workflow.run()
```

## 🔗 Related Documentation

- [API Documentation](https://docs.chronomaly.io)
- [User Guide](https://docs.chronomaly.io/guide)
- [Architecture](https://docs.chronomaly.io/architecture)
