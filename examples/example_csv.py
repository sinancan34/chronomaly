"""
Example: Forecasting from CSV data source
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
        file_path="data/sales.csv",
        date_column="date"
    )

    # Step 2: Configure transformer for pivot
    transformer = DataTransformer(
        index="date",
        columns="product_id",
        values="sales"
    )

    # Step 3: Configure forecaster
    forecaster = TimesFMForecaster(
        max_context=1024,
        max_horizon=256,
        normalize_inputs=True,
        use_continuous_quantile_head=True
    )

    # Step 4: Configure output writer
    output_writer = SQLiteOutputWriter(
        database_path="output/forecasts.db",
        table_name="sales_forecast",
        if_exists="replace"
    )

    # Step 5: Create and run pipeline
    pipeline = ForecastPipeline(
        data_source=data_source,
        forecaster=forecaster,
        output_writer=output_writer,
        transformer=transformer
    )

    # Generate 28-day forecast with quantile predictions
    forecast_df = pipeline.run(horizon=28, return_point=False)

    print("Forecast completed!")
    print(f"Shape: {forecast_df.shape}")
    print("\nFirst few rows:")
    print(forecast_df.head())


if __name__ == "__main__":
    main()
