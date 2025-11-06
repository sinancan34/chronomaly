"""
Example: Multi-dimensional forecasting (multiple grouping columns)
"""

from forecast_library import (
    ForecastPipeline,
    CSVDataSource,
    DataTransformer,
    TimesFMForecaster,
    SQLiteOutputWriter
)


def main():
    # Step 1: Configure data source
    data_source = CSVDataSource(
        file_path="data/sales_multi.csv",
        date_column="date"
    )

    # Step 2: Configure transformer with multiple columns
    # This will create timeseries IDs like "product1_region1", "product1_region2", etc.
    transformer = DataTransformer(
        index="date",
        columns=["product_id", "region"],  # Multiple grouping columns
        values="sales"
    )

    # Step 3: Configure forecaster
    forecaster = TimesFMForecaster()

    # Step 4: Configure output writer
    output_writer = SQLiteOutputWriter(
        database_path="output/forecasts.db",
        table_name="multi_dimension_forecast",
        if_exists="replace"
    )

    # Step 5: Create and run pipeline
    pipeline = ForecastPipeline(
        data_source=data_source,
        forecaster=forecaster,
        output_writer=output_writer,
        transformer=transformer
    )

    # Generate forecast
    forecast_df = pipeline.run(horizon=28)

    print("Multi-dimensional forecast completed!")
    print(forecast_df.head())


if __name__ == "__main__":
    main()
