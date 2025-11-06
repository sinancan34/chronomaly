"""
Example: Point forecast (instead of quantile forecast)
"""

from forecast_library import (
    ForecastPipeline,
    CSVDataSource,
    DataTransformer,
    TimesFMForecaster,
    SQLiteOutputWriter
)


def main():
    # Configure components
    data_source = CSVDataSource(
        file_path="data/sales.csv",
        date_column="date"
    )

    transformer = DataTransformer(
        index="date",
        columns="product_id",
        values="sales"
    )

    forecaster = TimesFMForecaster()

    output_writer = SQLiteOutputWriter(
        database_path="output/forecasts.db",
        table_name="point_forecast",
        if_exists="replace"
    )

    # Create pipeline
    pipeline = ForecastPipeline(
        data_source=data_source,
        forecaster=forecaster,
        output_writer=output_writer,
        transformer=transformer
    )

    # Generate point forecast (not quantile)
    forecast_df = pipeline.run(horizon=28, return_point=True)

    print("Point forecast completed!")
    print(forecast_df.head())


if __name__ == "__main__":
    main()
