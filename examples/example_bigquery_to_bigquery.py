"""
Example: Full BigQuery Integration - Read from BigQuery, Forecast, Write to BigQuery
"""

from forecast_library import (
    ForecastPipeline,
    BigQueryDataSource,
    DataTransformer,
    TimesFMForecaster,
    BigQueryOutputWriter
)


def main():
    # Step 1: Configure BigQuery data source (INPUT)
    data_source = BigQueryDataSource(
        service_account_file="path/to/service_account.json",
        project="your-gcp-project-id",
        query="""
            SELECT
                DATE(timestamp) as date,
                product_id,
                SUM(sales_amount) as sales
            FROM `your-project.dataset.sales_table`
            WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
            GROUP BY date, product_id
            ORDER BY date
        """,
        date_column="date"
    )

    # Step 2: Configure transformer for pivot
    transformer = DataTransformer(
        index="date",
        columns="product_id",
        values="sales"
    )

    # Step 3: Configure forecaster with custom settings
    forecaster = TimesFMForecaster(
        max_context=1024,
        max_horizon=256,
        normalize_inputs=True
    )

    # Step 4: Configure BigQuery output writer (OUTPUT)
    # This will write forecast results back to BigQuery
    output_writer = BigQueryOutputWriter(
        service_account_file="path/to/service_account.json",
        project="your-gcp-project-id",
        dataset="overview_report",
        table="forecast",
        write_disposition="WRITE_TRUNCATE"  # Replace existing data
    )

    # Step 5: Create and run pipeline
    pipeline = ForecastPipeline(
        data_source=data_source,
        forecaster=forecaster,
        output_writer=output_writer,
        transformer=transformer
    )

    # Generate 60-day forecast and write to BigQuery
    forecast_df = pipeline.run(horizon=60)

    print("Forecast completed and written to BigQuery!")
    print(f"Dataset: overview_report")
    print(f"Table: forecast")
    print("\nFirst few rows of forecast:")
    print(forecast_df.head())


def example_with_point_forecast():
    """
    Alternative example using point forecasts instead of quantiles.
    Point forecasts return a single value per time period instead of multiple quantiles.
    """
    data_source = BigQueryDataSource(
        service_account_file="path/to/service_account.json",
        project="your-gcp-project-id",
        query="SELECT date, product_id, sales FROM `project.dataset.table`",
        date_column="date"
    )

    transformer = DataTransformer(
        index="date",
        columns="product_id",
        values="sales"
    )

    forecaster = TimesFMForecaster()

    output_writer = BigQueryOutputWriter(
        service_account_file="path/to/service_account.json",
        project="your-gcp-project-id",
        dataset="overview_report",
        table="forecast_point",
        write_disposition="WRITE_TRUNCATE"
    )

    pipeline = ForecastPipeline(
        data_source=data_source,
        forecaster=forecaster,
        output_writer=output_writer,
        transformer=transformer
    )

    # Generate point forecast (return_point=True)
    forecast_df = pipeline.run(horizon=60, return_point=True)

    print("Point forecast completed!")
    print(forecast_df.head())


def example_append_mode():
    """
    Example using WRITE_APPEND mode to add forecasts incrementally.
    Useful for time-series forecasting where you want to keep historical predictions.
    """
    data_source = BigQueryDataSource(
        service_account_file="path/to/service_account.json",
        project="your-gcp-project-id",
        query="SELECT date, product_id, sales FROM `project.dataset.table`",
        date_column="date"
    )

    transformer = DataTransformer(
        index="date",
        columns="product_id",
        values="sales"
    )

    forecaster = TimesFMForecaster()

    # Use WRITE_APPEND to add new forecasts without deleting old ones
    output_writer = BigQueryOutputWriter(
        service_account_file="path/to/service_account.json",
        project="your-gcp-project-id",
        dataset="overview_report",
        table="forecast_history",
        write_disposition="WRITE_APPEND"  # Append to existing data
    )

    pipeline = ForecastPipeline(
        data_source=data_source,
        forecaster=forecaster,
        output_writer=output_writer,
        transformer=transformer
    )

    forecast_df = pipeline.run(horizon=60)

    print("Forecast appended to BigQuery table!")


if __name__ == "__main__":
    # Run the main example
    main()

    # Uncomment to run alternative examples:
    # example_with_point_forecast()
    # example_append_mode()
