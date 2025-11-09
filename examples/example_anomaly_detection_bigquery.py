"""
Example: Anomaly Detection comparing Forecast vs Actual from BigQuery

This example demonstrates how to:
1. Read forecast data from BigQuery (pivot format with pipe-separated quantiles)
2. Read actual data from BigQuery (raw format)
3. Compare actual values against forecast confidence intervals (q10-q90)
4. Detect anomalies and calculate deviations
5. Write anomaly results to BigQuery
"""

from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.comparators import ForecastActualComparator
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter


def main():
    # Step 1: Configure forecast data reader
    # Forecast data is in pivot format with pipe-separated quantiles
    # Format: "point|q10|q20|q30|q40|q50|q60|q70|q80|q90"
    forecast_reader = BigQueryDataReader(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        query="""
            SELECT date,
                   desktop_organic_homepage,
                   mobile_paid_product
            FROM `your-project.dataset.forecast`
            WHERE date = '2024-01-15'
        """
    )

    # Step 2: Configure actual data reader
    # Actual data is in raw format (will be pivoted)
    actual_reader = BigQueryDataReader(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        query="""
            SELECT
                date,
                platform,
                default_channel_group,
                landing_page_group,
                SUM(sessions) AS sessions
            FROM `your-project.dataset.google_analytics_traffic_sources_*`
            WHERE date = '2024-01-15'
            GROUP BY date, platform, default_channel_group, landing_page_group
        """
    )

    # Step 3: Configure transformer for actual data pivot
    # This will convert raw actual data to match forecast format
    transformer = DataTransformer(
        index="date",
        columns=["platform", "default_channel_group", "landing_page_group"],
        values="sessions"
    )

    # Step 4: Configure anomaly detector
    # Compares actual values against q10-q90 confidence interval (80% CI)
    anomaly_detector = ForecastActualComparator(
        transformer=transformer,
        date_column="date",
        exclude_columns=["date"]
    )

    # Step 5: Configure output writer
    data_writer = BigQueryDataWriter(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        dataset="anomaly_detection",
        table="daily_anomalies",
        if_exists="append"  # Append to keep historical anomalies
    )

    # Step 6: Create and run workflow
    workflow = AnomalyDetectionWorkflow(
        forecast_reader=forecast_reader,
        actual_reader=actual_reader,
        anomaly_detector=anomaly_detector,
        data_writer=data_writer
    )

    # Detect anomalies
    anomaly_df = workflow.run()

    print("Anomaly detection completed!")
    print(f"\nTotal metrics analyzed: {len(anomaly_df)}")

    # Show summary by status
    print("\nStatus Summary:")
    print(anomaly_df['status'].value_counts())

    # Show significant anomalies
    significant_anomalies = anomaly_df[
        (anomaly_df['status'].isin(['BELOW_P10', 'ABOVE_P90'])) &
        (anomaly_df['deviation_pct'] > 10.0)  # More than 10% deviation
    ]

    print(f"\nSignificant anomalies (>10% deviation): {len(significant_anomalies)}")

    if len(significant_anomalies) > 0:
        print("\nTop 10 Significant Anomalies:")
        print(significant_anomalies.nlargest(10, 'deviation_pct')[
            ['date', 'metric', 'actual', 'forecast', 'q10', 'q90', 'status', 'deviation_pct']
        ].to_string(index=False))


def main_with_filter():
    """
    Alternative example using the detect_with_filter method
    for more control over what anomalies to report.
    """
    # Configure readers
    forecast_reader = BigQueryDataReader(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        query="SELECT * FROM `your-project.dataset.forecast` WHERE date = '2024-01-15'"
    )

    actual_reader = BigQueryDataReader(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        query="""
            SELECT date, platform, channel, SUM(sessions) as sessions
            FROM `your-project.dataset.traffic`
            WHERE date = '2024-01-15'
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

    # Load data manually
    forecast_df = forecast_reader.load()
    actual_df = actual_reader.load()

    # Use filtered detection
    anomaly_df = detector.detect_with_filter(
        forecast_df=forecast_df,
        actual_df=actual_df,
        min_deviation_pct=5.0,  # Only report deviations > 5%
        exclude_no_forecast=True  # Exclude metrics with no forecast
    )

    print(f"Filtered anomalies: {len(anomaly_df)}")
    print(anomaly_df)


if __name__ == "__main__":
    # Run main example
    main()

    # Uncomment to run alternative filtered example
    # main_with_filter()
