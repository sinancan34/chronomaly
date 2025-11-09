"""
Example: Complete Anomaly Detection Workflow

This example demonstrates how to use the AnomalyDetectionWorkflow to:
1. Load forecast and actual data from CSV files
2. Configure the anomaly detector with various options
3. Run the complete workflow
4. Save results to output file

Requirements:
    - pip install pandas

Usage:
    python examples/anomaly_detection_workflow_example.py
"""

import pandas as pd
from datetime import datetime
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.comparators import ForecastActualComparator
from chronomaly.infrastructure.transformers import DataTransformer


def create_sample_forecast_csv():
    """Create sample forecast data CSV file."""
    test_date = datetime(2024, 1, 15)

    forecast_data = {
        'date': [test_date],
        'desktop_organic': ['100|90|92|95|98|100|102|105|108|110'],
        'desktop_paid': ['50|45|46|47|48|50|52|53|55|60'],
        'mobile_organic': ['80|70|72|75|77|80|82|85|88|90'],
        'mobile_paid': ['30|25|26|27|28|30|32|33|35|40']
    }
    forecast_df = pd.DataFrame(forecast_data)
    forecast_df.to_csv('/tmp/forecast.csv', index=False)
    print("Created sample forecast file: /tmp/forecast.csv")


def create_sample_actual_csv():
    """Create sample actual data CSV file."""
    test_date = datetime(2024, 1, 15)

    actual_data = {
        'date': [test_date, test_date, test_date, test_date],
        'platform': ['desktop', 'desktop', 'mobile', 'mobile'],
        'channel': ['organic', 'paid', 'organic', 'paid'],
        'sessions': [95, 65, 60, 28]  # organic in range, paid above, organic below, paid in range
    }
    actual_df = pd.DataFrame(actual_data)
    actual_df.to_csv('/tmp/actual.csv', index=False)
    print("Created sample actual file: /tmp/actual.csv")


def example_basic_workflow():
    """
    Example 1: Basic workflow with minimal configuration.

    This example shows the simplest way to run anomaly detection:
    - Load data from CSV files
    - Detect anomalies
    - Save results to CSV
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Anomaly Detection Workflow")
    print("=" * 80)

    # Create sample data
    create_sample_forecast_csv()
    create_sample_actual_csv()

    # Configure data readers
    forecast_reader = CSVDataReader(file_path='/tmp/forecast.csv')
    actual_reader = CSVDataReader(file_path='/tmp/actual.csv')

    # Configure transformer (pivot actual data to match forecast format)
    transformer = DataTransformer(
        index='date',
        columns=['platform', 'channel'],
        values='sessions'
    )

    # Configure anomaly detector
    detector = ForecastActualComparator(
        transformer=transformer,
        date_column='date',
        exclude_columns=['date']
    )

    # Configure data writer
    writer = SQLiteDataWriter(
        database_path='/tmp/anomalies.db',
        table_name='anomaly_results'
    )

    # Create and run workflow
    workflow = AnomalyDetectionWorkflow(
        forecast_reader=forecast_reader,
        actual_reader=actual_reader,
        anomaly_detector=detector,
        data_writer=writer
    )

    results = workflow.run()

    print(f"\nDetection complete! Found {len(results)} metrics analyzed.")
    print(f"Results saved to: /tmp/anomalies.db (table: anomaly_results)")
    print("\nSample results:")
    print(results.head(10).to_string(index=False))


def example_advanced_workflow():
    """
    Example 2: Advanced workflow with filtering and dimension extraction.

    This example demonstrates:
    - Splitting metric names into separate dimension columns
    - Filtering to top 95% of metrics by forecast value
    - Returning only anomalies (BELOW_P10 and ABOVE_P90)
    - Formatting deviation as percentage string
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Advanced Workflow with Filtering")
    print("=" * 80)

    # Create sample data
    create_sample_forecast_csv()
    create_sample_actual_csv()

    # Configure data readers
    forecast_reader = CSVDataReader(file_path='/tmp/forecast.csv')
    actual_reader = CSVDataReader(file_path='/tmp/actual.csv')

    # Configure transformer
    transformer = DataTransformer(
        index='date',
        columns=['platform', 'channel'],
        values='sessions'
    )

    # Configure anomaly detector with advanced options
    detector = ForecastActualComparator(
        transformer=transformer,
        date_column='date',
        exclude_columns=['date'],
        dimension_names=['platform', 'channel'],  # Split metric into dimensions
        cumulative_threshold=0.95,  # Keep top 95% of metrics
        return_only_anomalies=True,  # Only return anomalies
        min_deviation_threshold=5.0,  # Minimum 5% deviation
        format_deviation_as_string=True  # Format as "15.3%"
    )

    # Configure data writer
    writer = SQLiteDataWriter(database_path='/tmp/anomalies_filtered.db', table_name='anomaly_results')

    # Create and run workflow
    workflow = AnomalyDetectionWorkflow(
        forecast_reader=forecast_reader,
        actual_reader=actual_reader,
        anomaly_detector=detector,
        data_writer=writer
    )

    results = workflow.run()

    print(f"\nDetection complete! Found {len(results)} anomalies.")
    print(f"Results saved to: /tmp/anomalies_filtered.db (table: anomaly_results)")

    if len(results) > 0:
        print("\nAnomaly details:")
        print(results.to_string(index=False))


def example_workflow_without_output():
    """
    Example 3: Run workflow without writing to file.

    This is useful for testing or when you want to inspect results
    before deciding whether to save them.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Workflow Without Output")
    print("=" * 80)

    # Create sample data
    create_sample_forecast_csv()
    create_sample_actual_csv()

    # Configure readers, transformer, and detector
    forecast_reader = CSVDataReader(file_path='/tmp/forecast.csv')
    actual_reader = CSVDataReader(file_path='/tmp/actual.csv')

    transformer = DataTransformer(
        index='date',
        columns=['platform', 'channel'],
        values='sessions'
    )

    detector = ForecastActualComparator(
        transformer=transformer,
        date_column='date',
        exclude_columns=['date']
    )

    # Writer is still required for workflow initialization, but won't be used
    writer = SQLiteDataWriter(database_path='/tmp/unused.db', table_name='anomaly_results')

    # Create workflow
    workflow = AnomalyDetectionWorkflow(
        forecast_reader=forecast_reader,
        actual_reader=actual_reader,
        anomaly_detector=detector,
        data_writer=writer
    )

    # Run without output
    results = workflow.run_without_output()

    print(f"\nDetection complete! Found {len(results)} metrics analyzed.")
    print("No file was written (used run_without_output).")

    # Inspect results
    anomalies = results[results['status'].isin(['BELOW_P10', 'ABOVE_P90'])]
    print(f"\nFound {len(anomalies)} anomalies:")
    if len(anomalies) > 0:
        print(anomalies[['metric', 'actual', 'q10', 'q90', 'status', 'deviation_pct']].to_string(index=False))

    # Now you can decide whether to save the results
    if len(anomalies) >= 2:
        print("\nSignificant anomalies detected! Saving to database...")
        writer.write(anomalies)
        print("Saved to /tmp/unused.db (table: anomaly_results)")


def example_error_handling():
    """
    Example 4: Error handling and validation.

    This example demonstrates how the workflow handles invalid data.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Error Handling")
    print("=" * 80)

    # Create empty forecast file
    empty_df = pd.DataFrame()
    empty_df.to_csv('/tmp/empty_forecast.csv', index=False)

    forecast_reader = CSVDataReader(file_path='/tmp/empty_forecast.csv')
    actual_reader = CSVDataReader(file_path='/tmp/actual.csv')

    transformer = DataTransformer(
        index='date',
        columns=['platform', 'channel'],
        values='sessions'
    )

    detector = ForecastActualComparator(
        transformer=transformer,
        date_column='date'
    )

    writer = SQLiteDataWriter(database_path='/tmp/output.db', table_name='anomaly_results')

    workflow = AnomalyDetectionWorkflow(
        forecast_reader=forecast_reader,
        actual_reader=actual_reader,
        anomaly_detector=detector,
        data_writer=writer
    )

    try:
        results = workflow.run()
    except ValueError as e:
        print(f"\nExpected error caught: {e}")
        print("The workflow properly validates input data!")


if __name__ == "__main__":
    # Run all examples
    example_basic_workflow()
    example_advanced_workflow()
    example_workflow_without_output()
    example_error_handling()

    print("\n" + "=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)
