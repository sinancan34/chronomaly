"""
Example: Forecasting from SQLite data source
"""

from forecast_library import (
    ForecastPipeline,
    SQLiteDataSource,
    DataTransformer,
    TimesFMForecaster,
    SQLiteOutputWriter
)


def main():
    # Step 1: Configure data source
    data_source = SQLiteDataSource(
        database_path="data/sales.db",
        query="""
            SELECT date, product_id, SUM(quantity) as sales
            FROM sales_transactions
            WHERE date >= '2023-01-01'
            GROUP BY date, product_id
        """,
        date_column="date"
    )

    # Step 2: Configure transformer for pivot
    transformer = DataTransformer(
        index="date",
        columns="product_id",
        values="sales"
    )

    # Step 3: Configure forecaster
    forecaster = TimesFMForecaster()

    # Step 4: Configure output writer
    output_writer = SQLiteOutputWriter(
        database_path="output/forecasts.db",
        table_name="sales_forecast_from_sqlite",
        if_exists="replace"
    )

    # Step 5: Create and run pipeline
    pipeline = ForecastPipeline(
        data_source=data_source,
        forecaster=forecaster,
        output_writer=output_writer,
        transformer=transformer
    )

    # Generate 30-day forecast
    forecast_df = pipeline.run(horizon=30)

    print("Forecast completed!")
    print(forecast_df.head())


if __name__ == "__main__":
    main()
