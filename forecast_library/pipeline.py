"""
Main forecast pipeline orchestrator.
"""

import pandas as pd
from typing import Optional
from .data_sources.base import DataSource
from .transformers.pivot import DataTransformer
from .forecasters.base import Forecaster
from .outputs.base import OutputWriter


class ForecastPipeline:
    """
    Main orchestrator class for the forecast pipeline.

    This class coordinates the entire forecasting workflow:
    1. Load data from source
    2. Transform data (pivot if needed)
    3. Generate forecast
    4. Write results to output

    Args:
        data_source: Data source instance (CSV, SQLite, BigQuery, etc.)
        forecaster: Forecaster instance (TimesFM, etc.)
        output_writer: Output writer instance (SQLite, etc.)
        transformer: Optional data transformer for pivot operations
    """

    def __init__(
        self,
        data_source: DataSource,
        forecaster: Forecaster,
        output_writer: OutputWriter,
        transformer: Optional[DataTransformer] = None
    ):
        self.data_source = data_source
        self.forecaster = forecaster
        self.output_writer = output_writer
        self.transformer = transformer

    def run(
        self,
        horizon: int,
        return_point: bool = False
    ) -> pd.DataFrame:
        """
        Execute the complete forecast pipeline.

        Args:
            horizon: Number of periods to forecast
            return_point: If True, return point forecasts instead of quantiles
                         (only applicable if forecaster supports this)

        Returns:
            pd.DataFrame: The forecast results
        """
        # Step 1: Load data
        df = self.data_source.load()

        # Step 2: Transform data (if transformer is provided)
        if self.transformer is not None:
            df = self.transformer.pivot_table(df)

        # Step 3: Generate forecast
        # Check if forecaster's forecast method accepts return_point parameter
        try:
            forecast_df = self.forecaster.forecast(
                dataframe=df,
                horizon=horizon,
                return_point=return_point
            )
        except TypeError:
            # Fallback for forecasters that don't support return_point
            forecast_df = self.forecaster.forecast(
                dataframe=df,
                horizon=horizon
            )

        # Step 4: Write results to output
        self.output_writer.write(forecast_df)

        return forecast_df

    def run_without_output(
        self,
        horizon: int,
        return_point: bool = False
    ) -> pd.DataFrame:
        """
        Execute forecast pipeline without writing to output.

        Useful for testing or when you want to inspect results before writing.

        Args:
            horizon: Number of periods to forecast
            return_point: If True, return point forecasts instead of quantiles

        Returns:
            pd.DataFrame: The forecast results
        """
        # Step 1: Load data
        df = self.data_source.load()

        # Step 2: Transform data (if transformer is provided)
        if self.transformer is not None:
            df = self.transformer.pivot_table(df)

        # Step 3: Generate forecast
        try:
            forecast_df = self.forecaster.forecast(
                dataframe=df,
                horizon=horizon,
                return_point=return_point
            )
        except TypeError:
            forecast_df = self.forecaster.forecast(
                dataframe=df,
                horizon=horizon
            )

        return forecast_df
