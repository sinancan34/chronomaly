"""
Example: Forecasting without transformation (data already in pivot format)
"""

from forecast_library import (
    ForecastPipeline,
    CSVDataSource,
    TimesFMForecaster,
    SQLiteOutputWriter
)


def main():
    # Step 1: Configure data source
    # Assuming CSV is already in pivot format with date as index
    # and each column representing a different time series
    data_source = CSVDataSource(
        file_path="data/sales_pivot.csv",
        date_column="date",
        index_col="date",  # Set date as index
        parse_dates=True
    )

    # Step 2: Configure forecaster
    forecaster = TimesFMForecaster()

    # Step 3: Configure output writer
    output_writer = SQLiteOutputWriter(
        database_path="output/forecasts.db",
        table_name="no_transform_forecast",
        if_exists="replace"
    )

    # Step 4: Create pipeline WITHOUT transformer
    pipeline = ForecastPipeline(
        data_source=data_source,
        forecaster=forecaster,
        output_writer=output_writer,
        transformer=None  # No transformation needed
    )

    # Generate forecast
    forecast_df = pipeline.run(horizon=28)

    print("Forecast completed without transformation!")
    print(forecast_df.head())


if __name__ == "__main__":
    main()
