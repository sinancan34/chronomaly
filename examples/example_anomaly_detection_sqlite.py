"""
Example: Anomaly Detection comparing Forecast vs Actual from SQLite

This example demonstrates how to:
1. Read forecast data from SQLite (pivot format with pipe-separated quantiles)
2. Read actual data from SQLite (raw format)
3. Compare actual values against forecast confidence intervals (q10-q90)
4. Detect anomalies and calculate deviations
5. Write anomaly results to SQLite
"""

from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.databases import SQLiteDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.comparators import ForecastActualComparator
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter


def main():
    # Step 1: Configure forecast data reader
    # Forecast data is in pivot format with pipe-separated quantiles
    # Format: "point|q10|q20|q30|q40|q50|q60|q70|q80|q90"
    forecast_reader = SQLiteDataReader(
        database_path="data/forecasts.db",
        query="""
            SELECT date, platform_direct_homepage, platform_mobile_product
            FROM sales_forecast
            WHERE date = '2024-01-15'
        """,
        date_column="date"
    )

    # Step 2: Configure actual data reader
    # Actual data is in raw format (will be pivoted)
    actual_reader = SQLiteDataReader(
        database_path="data/sales.db",
        query="""
            SELECT date, platform, landing_page, SUM(sessions) as sessions
            FROM traffic_data
            WHERE date = '2024-01-15'
            GROUP BY date, platform, landing_page
        """,
        date_column="date"
    )

    # Step 3: Configure transformer for actual data pivot
    # This will convert raw actual data to match forecast format
    transformer = DataTransformer(
        index="date",
        columns=["platform", "landing_page"],  # Multiple columns create combined IDs
        values="sessions"
    )

    # Step 4: Configure anomaly detector
    # Compares actual values against q10-q90 confidence interval
    anomaly_detector = ForecastActualComparator(
        transformer=transformer,
        date_column="date",
        exclude_columns=["date"]  # Don't compare these columns
    )

    # Step 5: Configure output writer
    data_writer = SQLiteDataWriter(
        database_path="output/anomalies.db",
        table_name="anomaly_detection_results",
        if_exists="replace"
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

    # Show anomalies (outside confidence interval)
    anomalies = anomaly_df[anomaly_df['status'].isin(['BELOW_P10', 'ABOVE_P90'])]
    print(f"\nAnomalies detected: {len(anomalies)}")

    if len(anomalies) > 0:
        print("\nTop 5 Anomalies by Deviation:")
        print(anomalies.nlargest(5, 'deviation_pct')[
            ['metric', 'actual', 'q10', 'q90', 'status', 'deviation_pct']
        ])


if __name__ == "__main__":
    main()
