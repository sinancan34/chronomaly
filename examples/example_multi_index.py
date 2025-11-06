"""
Example: Multi-Index forecasting (advanced usage)
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
        file_path="data/hierarchical_sales.csv",
        date_column="date"
    )

    # Step 2: Configure transformer with multiple index columns
    # This creates a MultiIndex (date, store_id)
    # ⚠️ Warning: MultiIndex may not be compatible with TimesFM
    transformer = DataTransformer(
        index=["date", "store_id"],  # Creates MultiIndex
        columns="product_id",
        values="sales"
    )

    # Step 3: Configure forecaster
    forecaster = TimesFMForecaster()

    # Step 4: Configure output writer
    output_writer = SQLiteOutputWriter(
        database_path="output/forecasts.db",
        table_name="multi_index_forecast",
        if_exists="replace"
    )

    # Step 5: Create pipeline
    pipeline = ForecastPipeline(
        data_source=data_source,
        forecaster=forecaster,
        output_writer=output_writer,
        transformer=transformer
    )

    # Step 6: Run forecast without writing first to inspect
    print("Generating forecast with MultiIndex...")
    forecast_df = pipeline.run_without_output(horizon=28)

    print("\nForecast with MultiIndex:")
    print(forecast_df.head())
    print(f"\nIndex type: {type(forecast_df.index)}")
    print(f"Index names: {forecast_df.index.names}")

    # Step 7: If you need to flatten MultiIndex
    print("\nFlattening MultiIndex...")
    forecast_df_flat = forecast_df.reset_index()
    print(forecast_df_flat.head())

    # Step 8: Write to output
    output_writer.write(forecast_df_flat)
    print("\nForecast saved to SQLite!")


if __name__ == "__main__":
    main()
