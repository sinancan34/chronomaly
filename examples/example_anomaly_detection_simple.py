"""
Example: Simple Anomaly Detection without mapping logic

This example demonstrates the core anomaly detection functionality:
- Reading forecast and actual data
- Pivoting actual data to match forecast format
- Comparing with confidence intervals (q10-q90)
- Splitting metrics into dimension columns
- Filtering by cumulative threshold and deviation
"""

from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.comparators import ForecastActualComparator
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter
from datetime import datetime, timedelta


def main():
    """
    Run anomaly detection with core features.
    """

    # Calculate dates (yesterday)
    days_ago_1 = datetime.now() - timedelta(days=1)
    target_date = days_ago_1.strftime('%Y-%m-%d')

    print(f"Running anomaly detection for date: {target_date}")
    print("=" * 80)

    # Step 1: Configure forecast data reader
    forecast_reader = BigQueryDataReader(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        query=f"""
            SELECT *
            FROM `your-project.dataset.forecast`
            WHERE date = '{target_date}'
        """
    )

    # Step 2: Configure actual data reader
    actual_reader = BigQueryDataReader(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        query=f"""
            SELECT
                date,
                platform,
                default_channel_group,
                landing_page_group,
                SUM(sessions) AS sessions
            FROM `your-project.dataset.traffic_data`
            WHERE date = '{target_date}'
            GROUP BY date, platform, default_channel_group, landing_page_group
        """
    )

    # Step 3: Configure transformer for actual data pivot
    transformer = DataTransformer(
        index="date",
        columns=["platform", "default_channel_group", "landing_page_group"],
        values="sessions"
    )

    # Step 4: Configure anomaly detector
    detector = ForecastActualComparator(
        transformer=transformer,
        date_column="date",
        exclude_columns=["date"],
        # Split metrics into separate dimension columns
        dimension_names=["platform", "default_channel_group", "landing_page_group"],
        # Filter to top 95% of metrics by forecast value
        cumulative_threshold=0.95,
        # Return only anomalies (BELOW_P10, ABOVE_P90)
        return_only_anomalies=True,
        # Minimum 5% deviation to report
        min_deviation_threshold=5.0,
        # Format deviation as "15.3%" string
        format_deviation_as_string=True
    )

    # Step 5: Configure output writer
    writer = BigQueryDataWriter(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        dataset="anomaly_detection",
        table="daily_anomalies",
        if_exists="append"
    )

    # Step 6: Create and run workflow
    workflow = AnomalyDetectionWorkflow(
        forecast_reader=forecast_reader,
        actual_reader=actual_reader,
        anomaly_detector=detector,
        data_writer=writer
    )

    # Run detection
    anomaly_df = workflow.run()

    # Display results
    print("\n" + "=" * 80)
    print("ANOMALY DETECTION COMPLETED")
    print("=" * 80)

    if anomaly_df.empty:
        print("\n✓ No anomalies detected - all metrics within expected range!")
    else:
        print(f"\n⚠ {len(anomaly_df)} anomalies detected")

        print("\nStatus breakdown:")
        print(anomaly_df['status'].value_counts())

        print("\nTop 10 anomalies by deviation:")
        print(anomaly_df.nlargest(10, 'deviation_pct')[[
            'date', 'platform', 'default_channel_group', 'landing_page_group',
            'actual', 'forecast', 'q10', 'q90', 'status', 'deviation_pct'
        ]].to_string(index=False))


def example_sqlite():
    """
    SQLite example for local testing.
    """
    from chronomaly.infrastructure.data.readers.databases import SQLiteDataReader
    from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter

    # Configure readers
    forecast_reader = SQLiteDataReader(
        database_path="data/forecasts.db",
        query="SELECT * FROM forecast WHERE date = '2024-01-15'",
        date_column="date"
    )

    actual_reader = SQLiteDataReader(
        database_path="data/actuals.db",
        query="""
            SELECT date, platform, channel, landing_page, SUM(sessions) as sessions
            FROM traffic WHERE date = '2024-01-15'
            GROUP BY date, platform, channel, landing_page
        """,
        date_column="date"
    )

    # Configure transformer
    transformer = DataTransformer(
        index="date",
        columns=["platform", "channel", "landing_page"],
        values="sessions"
    )

    # Configure detector
    detector = ForecastActualComparator(
        transformer=transformer,
        date_column="date",
        dimension_names=["platform", "channel", "landing_page"],
        cumulative_threshold=0.95,
        return_only_anomalies=True,
        min_deviation_threshold=5.0,
        format_deviation_as_string=True
    )

    # Configure writer
    writer = SQLiteDataWriter(
        database_path="output/anomalies.db",
        table_name="detected_anomalies",
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
    print(f"Detected {len(results)} anomalies")
    print(results)


if __name__ == "__main__":
    # Run BigQuery example
    main()

    # Uncomment to run SQLite example
    # example_sqlite()
