"""
Example: Comprehensive Data Sources and Destinations for Anomaly Detection

This example demonstrates all available data reading and writing options:

DATA READERS:
1. CSVDataReader - Read from CSV files
2. SQLiteDataReader - Read from SQLite databases
3. BigQueryDataReader - Read from Google BigQuery (requires google-cloud-bigquery)

DATA WRITERS:
1. SQLiteDataWriter - Write to SQLite databases
2. BigQueryDataWriter - Write to Google BigQuery (requires google-cloud-bigquery)

ANOMALY DETECTORS:
1. ForecastActualComparator - Compare forecast vs actual with quantiles

WORKFLOWS:
1. AnomalyDetectionWorkflow - Complete anomaly detection pipeline

Requirements:
    - pip install pandas
    - pip install google-cloud-bigquery  # Optional, for BigQuery examples

Usage:
    python examples/data_sources_comprehensive_example.py
"""

import pandas as pd
import os
from datetime import datetime
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.readers.databases import SQLiteDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.comparators import ForecastActualComparator
from chronomaly.infrastructure.transformers import DataTransformer


# ============================================================================
# PART 1: DATA READERS - All Available Options
# ============================================================================

def example_csv_reader():
    """
    Example 1: Read data from CSV files.

    CSVDataReader is the simplest option for file-based data.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: CSV Data Reader")
    print("=" * 80)

    # Create sample CSV file
    sample_data = pd.DataFrame({
        'date': [datetime(2024, 1, 15)],
        'desktop_organic': ['100|90|92|95|98|100|102|105|108|110'],
        'mobile_organic': ['80|70|72|75|77|80|82|85|88|90']
    })
    sample_data.to_csv('/tmp/forecast_csv.csv', index=False)
    print("Created sample CSV file: /tmp/forecast_csv.csv")

    # Configure CSV reader
    csv_reader = CSVDataReader(
        file_path='/tmp/forecast_csv.csv',
        date_column='date'  # Optional: specify date column
    )

    # Load data
    data = csv_reader.load()
    print(f"\nLoaded {len(data)} rows from CSV:")
    print(data.to_string(index=False))

    return data


def example_sqlite_reader():
    """
    Example 2: Read data from SQLite database.

    SQLiteDataReader is ideal for local database storage.
    Supports custom SQL queries for flexible data retrieval.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: SQLite Data Reader")
    print("=" * 80)

    # Create sample SQLite database
    db_path = '/tmp/forecast_data.db'
    sample_data = pd.DataFrame({
        'date': [datetime(2024, 1, 15)],
        'desktop_organic': ['100|90|92|95|98|100|102|105|108|110'],
        'mobile_organic': ['80|70|72|75|77|80|82|85|88|90']
    })

    import sqlite3
    conn = sqlite3.connect(db_path)
    sample_data.to_sql('forecasts', conn, if_exists='replace', index=False)
    conn.close()
    print(f"Created sample SQLite database: {db_path}")

    # Option A: Read entire table
    sqlite_reader = SQLiteDataReader(
        database_path=db_path,
        table_name='forecasts'
    )

    data = sqlite_reader.load()
    print(f"\nLoaded {len(data)} rows from SQLite:")
    print(data.to_string(index=False))

    # Option B: Read with custom SQL query
    print("\n--- Using custom SQL query ---")
    sqlite_reader_with_query = SQLiteDataReader(
        database_path=db_path,
        query="SELECT * FROM forecasts WHERE date >= '2024-01-01'"
    )

    data_filtered = sqlite_reader_with_query.load()
    print(f"Loaded {len(data_filtered)} rows with custom query")

    return data


def example_bigquery_reader():
    """
    Example 3: Read data from Google BigQuery (Optional - Requires Credentials).

    BigQueryDataReader is ideal for cloud-based analytics at scale.
    Requires google-cloud-bigquery package and service account credentials.

    Note: This example is informational only and won't run without credentials.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: BigQuery Data Reader (Informational)")
    print("=" * 80)

    print("""
BigQuery reader configuration example:

from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader

# Option A: Read from table
bq_reader = BigQueryDataReader(
    project_id='your-gcp-project',
    dataset_id='analytics',
    table_id='forecasts',
    credentials_path='/path/to/service-account.json'  # Optional
)

# Option B: Read with custom SQL query
bq_reader = BigQueryDataReader(
    project_id='your-gcp-project',
    query='''
        SELECT *
        FROM `project.dataset.forecasts`
        WHERE date >= '2024-01-01'
        AND metric_type = 'sessions'
    ''',
    credentials_path='/path/to/service-account.json'
)

data = bq_reader.load()
    """)

    print("\nSkipping BigQuery example (requires credentials)")
    print("See documentation for setup instructions")


# ============================================================================
# PART 2: DATA WRITERS - All Available Options
# ============================================================================

def example_sqlite_writer():
    """
    Example 4: Write data to SQLite database.

    SQLiteDataWriter provides local persistence with SQL query capabilities.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: SQLite Data Writer")
    print("=" * 80)

    # Create sample results
    results = pd.DataFrame({
        'date': [datetime(2024, 1, 15)],
        'metric': ['desktop_organic'],
        'actual': [95],
        'forecast': [100],
        'q10': [90],
        'q90': [110],
        'status': ['IN_RANGE'],
        'deviation_pct': [0.0]
    })

    # Configure SQLite writer
    sqlite_writer = SQLiteDataWriter(
        database_path='/tmp/anomaly_results.db',
        table_name='detection_results',
        if_exists='replace'  # Options: 'fail', 'replace', 'append'
    )

    # Write data
    sqlite_writer.write(results)
    print(f"Written {len(results)} rows to SQLite database")
    print(f"Location: /tmp/anomaly_results.db")
    print(f"Table: detection_results")

    # Verify the write
    import sqlite3
    conn = sqlite3.connect('/tmp/anomaly_results.db')
    verify_data = pd.read_sql('SELECT * FROM detection_results', conn)
    conn.close()

    print(f"\nVerified {len(verify_data)} rows in database:")
    print(verify_data.to_string(index=False))


def example_bigquery_writer():
    """
    Example 5: Write data to Google BigQuery (Optional - Requires Credentials).

    BigQueryDataWriter enables cloud-based result storage and analytics.
    Requires google-cloud-bigquery package and service account credentials.

    Note: This example is informational only and won't run without credentials.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 5: BigQuery Data Writer (Informational)")
    print("=" * 80)

    print("""
BigQuery writer configuration example:

from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter

# Configure writer
bq_writer = BigQueryDataWriter(
    project_id='your-gcp-project',
    dataset_id='analytics',
    table_id='anomaly_detection_results',
    credentials_path='/path/to/service-account.json',  # Optional
    if_exists='append'  # Options: 'fail', 'replace', 'append'
)

# Write results
bq_writer.write(results_dataframe)

# Data is now available in BigQuery for further analysis!
    """)

    print("\nSkipping BigQuery example (requires credentials)")
    print("See documentation for setup instructions")


# ============================================================================
# PART 3: ANOMALY DETECTORS - Configuration Options
# ============================================================================

def example_detector_basic():
    """
    Example 6: Basic Anomaly Detector Configuration.

    Minimal configuration for ForecastActualComparator.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Basic Anomaly Detector")
    print("=" * 80)

    transformer = DataTransformer(
        index='date',
        columns=['platform', 'channel'],
        values='sessions'
    )

    # Basic detector - compares all metrics, returns all statuses
    detector = ForecastActualComparator(
        transformer=transformer,
        date_column='date',
        exclude_columns=['date']
    )

    print("Basic detector configured:")
    print("- Compares all metrics")
    print("- Returns all statuses (IN_RANGE, BELOW_P10, ABOVE_P90, NO_FORECAST)")
    print("- No filtering applied")

    return detector


def example_detector_advanced():
    """
    Example 7: Advanced Anomaly Detector with Filtering.

    Demonstrates all available configuration options.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Advanced Anomaly Detector with Filtering")
    print("=" * 80)

    transformer = DataTransformer(
        index='date',
        columns=['platform', 'channel', 'landing_page'],
        values='sessions'
    )

    # Advanced detector with all options
    detector = ForecastActualComparator(
        transformer=transformer,
        date_column='date',
        exclude_columns=['date', 'company'],

        # Split metric names into separate columns
        dimension_names=['platform', 'channel', 'landing_page'],

        # Filter to top 95% of metrics by forecast value
        cumulative_threshold=0.95,

        # Return only anomalies (BELOW_P10 and ABOVE_P90)
        return_only_anomalies=True,

        # Minimum 10% deviation required
        min_deviation_threshold=10.0,

        # Format deviation as "15.3%" instead of 15.3
        format_deviation_as_string=True
    )

    print("Advanced detector configured:")
    print("- Splits metrics into dimensions: platform, channel, landing_page")
    print("- Filters to top 95% of metrics by forecast value")
    print("- Returns only anomalies (BELOW_P10, ABOVE_P90)")
    print("- Minimum deviation threshold: 10%")
    print("- Formats deviation as percentage string")

    return detector


# ============================================================================
# PART 4: COMPLETE WORKFLOWS - End-to-End Examples
# ============================================================================

def example_complete_workflow_csv_to_sqlite():
    """
    Example 8: Complete Workflow - CSV to SQLite.

    Most common workflow: Read CSV files, detect anomalies, save to SQLite.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Complete Workflow - CSV to SQLite")
    print("=" * 80)

    # Create sample data
    forecast_data = pd.DataFrame({
        'date': [datetime(2024, 1, 15)],
        'desktop_organic': ['100|90|92|95|98|100|102|105|108|110'],
        'desktop_paid': ['50|45|46|47|48|50|52|53|55|60'],
        'mobile_organic': ['80|70|72|75|77|80|82|85|88|90']
    })
    forecast_data.to_csv('/tmp/workflow_forecast.csv', index=False)

    actual_data = pd.DataFrame({
        'date': [datetime(2024, 1, 15), datetime(2024, 1, 15), datetime(2024, 1, 15)],
        'platform': ['desktop', 'desktop', 'mobile'],
        'channel': ['organic', 'paid', 'organic'],
        'sessions': [95, 70, 60]  # organic in range, paid above, mobile below
    })
    actual_data.to_csv('/tmp/workflow_actual.csv', index=False)

    # Configure pipeline
    forecast_reader = CSVDataReader(file_path='/tmp/workflow_forecast.csv')
    actual_reader = CSVDataReader(file_path='/tmp/workflow_actual.csv')

    transformer = DataTransformer(
        index='date',
        columns=['platform', 'channel'],
        values='sessions'
    )

    detector = ForecastActualComparator(
        transformer=transformer,
        dimension_names=['platform', 'channel']
    )

    writer = SQLiteDataWriter(
        database_path='/tmp/workflow_results.db',
        table_name='anomalies'
    )

    # Create and run workflow
    workflow = AnomalyDetectionWorkflow(
        forecast_reader=forecast_reader,
        actual_reader=actual_reader,
        anomaly_detector=detector,
        data_writer=writer
    )

    results = workflow.run()

    print(f"\n✓ Workflow complete!")
    print(f"  Input: CSV files (/tmp/workflow_forecast.csv, /tmp/workflow_actual.csv)")
    print(f"  Output: SQLite database (/tmp/workflow_results.db)")
    print(f"  Detected: {len(results)} metrics analyzed")

    print("\nResults:")
    print(results.to_string(index=False))

    # Show anomalies only
    anomalies = results[results['status'].isin(['BELOW_P10', 'ABOVE_P90'])]
    print(f"\n{len(anomalies)} anomalies found:")
    if len(anomalies) > 0:
        print(anomalies[['platform', 'channel', 'actual', 'q10', 'q90', 'status']].to_string(index=False))


def example_complete_workflow_sqlite_to_sqlite():
    """
    Example 9: Complete Workflow - SQLite to SQLite.

    Database-to-database workflow for production systems.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 9: Complete Workflow - SQLite to SQLite")
    print("=" * 80)

    # Create sample databases
    forecast_db = '/tmp/source_forecasts.db'
    actual_db = '/tmp/source_actuals.db'
    output_db = '/tmp/output_anomalies.db'

    import sqlite3

    # Create forecast database
    forecast_data = pd.DataFrame({
        'date': [datetime(2024, 1, 15)],
        'desktop_organic': ['100|90|92|95|98|100|102|105|108|110'],
        'mobile_paid': ['30|25|26|27|28|30|32|33|35|40']
    })
    conn = sqlite3.connect(forecast_db)
    forecast_data.to_sql('forecasts', conn, if_exists='replace', index=False)
    conn.close()

    # Create actual database
    actual_data = pd.DataFrame({
        'date': [datetime(2024, 1, 15), datetime(2024, 1, 15)],
        'platform': ['desktop', 'mobile'],
        'channel': ['organic', 'paid'],
        'sessions': [95, 45]
    })
    conn = sqlite3.connect(actual_db)
    actual_data.to_sql('actuals', conn, if_exists='replace', index=False)
    conn.close()

    # Configure pipeline
    forecast_reader = SQLiteDataReader(
        database_path=forecast_db,
        table_name='forecasts'
    )

    actual_reader = SQLiteDataReader(
        database_path=actual_db,
        table_name='actuals'
    )

    transformer = DataTransformer(
        index='date',
        columns=['platform', 'channel'],
        values='sessions'
    )

    detector = ForecastActualComparator(
        transformer=transformer,
        return_only_anomalies=True  # Only save anomalies
    )

    writer = SQLiteDataWriter(
        database_path=output_db,
        table_name='detected_anomalies',
        if_exists='replace'
    )

    # Create and run workflow
    workflow = AnomalyDetectionWorkflow(
        forecast_reader=forecast_reader,
        actual_reader=actual_reader,
        anomaly_detector=detector,
        data_writer=writer
    )

    results = workflow.run()

    print(f"\n✓ Database workflow complete!")
    print(f"  Forecast source: {forecast_db} (forecasts table)")
    print(f"  Actual source: {actual_db} (actuals table)")
    print(f"  Output: {output_db} (detected_anomalies table)")
    print(f"  Anomalies detected: {len(results)}")

    if len(results) > 0:
        print("\nAnomalies:")
        print(results.to_string(index=False))


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("COMPREHENSIVE DATA SOURCES EXAMPLE")
    print("Demonstrating all readers, writers, detectors, and workflows")
    print("=" * 80)

    # Part 1: Data Readers
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " PART 1: DATA READERS ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")

    example_csv_reader()
    example_sqlite_reader()
    example_bigquery_reader()

    # Part 2: Data Writers
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " PART 2: DATA WRITERS ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")

    example_sqlite_writer()
    example_bigquery_writer()

    # Part 3: Anomaly Detectors
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " PART 3: ANOMALY DETECTORS ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")

    example_detector_basic()
    example_detector_advanced()

    # Part 4: Complete Workflows
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " PART 4: COMPLETE WORKFLOWS ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")

    example_complete_workflow_csv_to_sqlite()
    example_complete_workflow_sqlite_to_sqlite()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
✓ Data Readers Available:
  - CSVDataReader: Simple file-based reading
  - SQLiteDataReader: Local database with SQL queries
  - BigQueryDataReader: Cloud-based analytics (requires credentials)

✓ Data Writers Available:
  - SQLiteDataWriter: Local database persistence
  - BigQueryDataWriter: Cloud-based storage (requires credentials)

✓ Anomaly Detectors:
  - ForecastActualComparator: Quantile-based anomaly detection
    * Configurable filtering and thresholds
    * Dimension extraction
    * Multiple output formats

✓ Workflows:
  - AnomalyDetectionWorkflow: Complete end-to-end pipeline
    * Flexible reader/writer combinations
    * Built-in validation
    * Error handling

All examples completed successfully!
See /tmp/ directory for generated files.
    """)
    print("=" * 80)
