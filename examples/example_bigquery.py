"""
Example: Forecasting from BigQuery data source
"""

from forecast_library import (
    ForecastPipeline,
    BigQueryDataSource,
    DataTransformer,
    TimesFMForecaster,
    SQLiteOutputWriter
)


def main():
    # Step 1: Configure BigQuery data source
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

    # Step 4: Configure output writer
    output_writer = SQLiteOutputWriter(
        database_path="output/forecasts.db",
        table_name="bigquery_forecast",
        if_exists="replace"
    )

    # Step 5: Create and run pipeline
    pipeline = ForecastPipeline(
        data_source=data_source,
        forecaster=forecaster,
        output_writer=output_writer,
        transformer=transformer
    )

    # Generate 60-day forecast
    forecast_df = pipeline.run(horizon=60)

    print("Forecast completed!")
    print(forecast_df.head())


if __name__ == "__main__":
    main()
