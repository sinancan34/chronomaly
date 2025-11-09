# Anomaly Detection Workflow

This guide explains how to use the `AnomalyDetectionWorkflow` to detect anomalies by comparing forecast predictions against actual values.

## Overview

The Anomaly Detection Workflow compares forecast data (with confidence intervals) against actual observed data to identify anomalies. It's particularly useful for:

- Detecting when actual metrics fall outside expected ranges
- Monitoring forecast accuracy
- Identifying unusual patterns in time series data
- Alerting on significant deviations

## How It Works

### 1. Data Format Requirements

**Forecast Data (Pivot Format)**
- Must be in wide/pivot format with one column per metric
- Each cell contains pipe-separated quantiles: `point|q10|q20|q30|q40|q50|q60|q70|q80|q90`
- The workflow uses q10 (index 1) and q90 (index 9) for the 80% confidence interval

Example:
```
date        | desktop_organic | mobile_paid
2024-01-15  | 100|90|95|98|100|102|105|108|110|115 | 50|45|47|48|50|52|53|55|57|60
```

**Actual Data (Raw Format)**
- Can be in long/raw format
- Will be automatically pivoted to match forecast format
- Should contain the same dimensions as forecast

Example:
```
date        | platform | channel  | sessions
2024-01-15  | desktop  | organic  | 95
2024-01-15  | mobile   | paid     | 65
```

### 2. Anomaly Detection Logic

For each metric, the workflow:

1. **Extracts confidence interval**: Gets q10 and q90 from forecast (80% confidence)
2. **Compares actual value**:
   - `IN_RANGE`: actual is between q10 and q90
   - `BELOW_P10`: actual is below q10 (lower than expected)
   - `ABOVE_P90`: actual is above q90 (higher than expected)
   - `NO_FORECAST`: no valid forecast available (q10=0 and q90=0)

3. **Calculates deviation**:
   - If below q10: `deviation_pct = ((q10 - actual) / q10) * 100`
   - If above q90: `deviation_pct = ((actual - q90) / q90) * 100`
   - If in range: `deviation_pct = 0`

### 3. Output Format

The workflow produces unpivoted results with columns:

| Column | Description |
|--------|-------------|
| date | Observation date (if available) |
| metric | Metric name (e.g., "desktop_organic") |
| actual | Actual observed value |
| forecast | Point forecast (q50) |
| q10 | Lower bound of 80% CI |
| q90 | Upper bound of 80% CI |
| status | IN_RANGE, BELOW_P10, ABOVE_P90, or NO_FORECAST |
| deviation_pct | Percentage deviation from boundary |

## Usage Examples

### Example 1: SQLite to SQLite

```python
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.databases import SQLiteDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.comparators import ForecastActualComparator
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter

# Read forecast data (already pivoted)
forecast_reader = SQLiteDataReader(
    database_path="data/forecasts.db",
    query="SELECT * FROM forecast WHERE date = '2024-01-15'",
    date_column="date"
)

# Read actual data (raw format)
actual_reader = SQLiteDataReader(
    database_path="data/actuals.db",
    query="""
        SELECT date, platform, channel, SUM(sessions) as sessions
        FROM traffic
        WHERE date = '2024-01-15'
        GROUP BY date, platform, channel
    """,
    date_column="date"
)

# Configure transformer to pivot actual data
transformer = DataTransformer(
    index="date",
    columns=["platform", "channel"],
    values="sessions"
)

# Configure anomaly detector
anomaly_detector = ForecastActualComparator(
    transformer=transformer,
    date_column="date"
)

# Configure output writer
data_writer = SQLiteDataWriter(
    database_path="output/anomalies.db",
    table_name="detected_anomalies",
    if_exists="append"
)

# Run workflow
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=anomaly_detector,
    data_writer=data_writer
)

results = workflow.run()
```

### Example 2: BigQuery to BigQuery

```python
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.comparators import ForecastActualComparator
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter

# Read forecast from BigQuery
forecast_reader = BigQueryDataReader(
    service_account_file="credentials.json",
    project="my-project",
    query="SELECT * FROM `my-project.forecasts.daily` WHERE date = CURRENT_DATE() - 1"
)

# Read actual from BigQuery
actual_reader = BigQueryDataReader(
    service_account_file="credentials.json",
    project="my-project",
    query="""
        SELECT date, platform, channel, SUM(sessions) as sessions
        FROM `my-project.analytics.traffic`
        WHERE date = CURRENT_DATE() - 1
        GROUP BY date, platform, channel
    """
)

# Configure transformer
transformer = DataTransformer(
    index="date",
    columns=["platform", "channel"],
    values="sessions"
)

# Configure detector
detector = ForecastActualComparator(
    transformer=transformer,
    date_column="date"
)

# Write to BigQuery
writer = BigQueryDataWriter(
    service_account_file="credentials.json",
    project="my-project",
    dataset="anomalies",
    table="daily_detections",
    if_exists="append"
)

# Run workflow
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=writer
)

results = workflow.run()
```

### Example 3: Filtered Detection (Without Writing)

```python
# Same setup as above, then:

# Run without writing to output
results = workflow.run_without_output()

# Filter significant anomalies
significant = results[
    (results['status'].isin(['BELOW_P10', 'ABOVE_P90'])) &
    (results['deviation_pct'] > 10.0)  # More than 10% deviation
]

print(f"Found {len(significant)} significant anomalies")
print(significant)
```

### Example 4: Using detect_with_filter

```python
# Load data manually
forecast_df = forecast_reader.load()
actual_df = actual_reader.load()

# Use built-in filter method
filtered_results = detector.detect_with_filter(
    forecast_df=forecast_df,
    actual_df=actual_df,
    min_deviation_pct=5.0,  # Only deviations > 5%
    exclude_no_forecast=True  # Skip metrics without forecast
)
```

## Configuration Options

### ForecastActualComparator Parameters

- `transformer` (required): DataTransformer to pivot actual data
- `date_column` (optional): Name of date column (default: 'date')
- `exclude_columns` (optional): List of columns to exclude from comparison

### DataTransformer Parameters

- `index`: Column(s) to use as index (typically 'date')
- `columns`: Column(s) to use as pivot columns (creates metric names)
- `values`: Column to use as values (typically a numeric metric)

## Best Practices

1. **Confidence Intervals**: The workflow uses q10 and q90 (80% confidence). This means ~20% of normal observations will be flagged as anomalies. Adjust your filtering accordingly.

2. **Deviation Thresholds**: Use `detect_with_filter()` with a reasonable `min_deviation_pct` (e.g., 5-10%) to focus on significant anomalies.

3. **Multiple Dimensions**: When pivoting with multiple columns (e.g., platform, channel, landing_page), the transformer automatically creates combined metric names like `platform_channel_landingpage`.

4. **Historical Tracking**: Use `if_exists="append"` in writers to build a historical anomaly database for trend analysis.

5. **Data Validation**: Always check that forecast and actual data cover the same date range and metrics before comparison.

## Troubleshooting

**Problem**: "Forecast DataFrame is empty"
- Check that your forecast query returns data
- Verify the date filter matches your actual data

**Problem**: "Required columns not found in DataFrame"
- Ensure actual data contains all columns specified in transformer
- Check column names match exactly (case-sensitive)

**Problem**: "All results show NO_FORECAST"
- Verify forecast data is in correct pipe-separated format
- Check that forecast values are not all zeros

**Problem**: "Metrics don't match between forecast and actual"
- Ensure the pivot columns in transformer match the forecast column naming
- Check for case sensitivity and special characters in column names

## See Also

- Full SQLite example: `examples/example_anomaly_detection_sqlite.py`
- Full BigQuery example: `examples/example_anomaly_detection_bigquery.py`
- ForecastWorkflow documentation for generating forecasts
