"""
Main forecast workflow orchestrator.
"""

import pandas as pd
import inspect
from typing import Optional
from ...infrastructure.data.readers.base import DataReader
from ...infrastructure.transformers.pivot import PivotTransformer
from ...infrastructure.forecasters.base import Forecaster
from ...infrastructure.data.writers.base import DataWriter


class ForecastWorkflow:
    """
    Main orchestrator class for the forecast workflow.

    This class coordinates the entire forecasting workflow:
    1. Load data from source
    2. Transform data (pivot if needed)
    3. Generate forecast
    4. Write results to output

    Args:
        data_reader: Data reader instance (CSV, SQLite, BigQuery, etc.)
        forecaster: Forecaster instance (TimesFM, etc.)
        data_writer: Data writer instance (SQLite, BigQuery, etc.)
        transformer: Optional data transformer for pivot operations
    """

    def __init__(
        self,
        data_reader: DataReader,
        forecaster: Forecaster,
        data_writer: DataWriter,
        transformer: Optional[PivotTransformer] = None
    ):
        self.data_reader = data_reader
        self.forecaster = forecaster
        self.data_writer = data_writer
        self.transformer = transformer

    def run(
        self,
        horizon: int,
        return_point: bool = False
    ) -> pd.DataFrame:
        """
        Execute the complete forecast workflow.

        Args:
            horizon: Number of periods to forecast
            return_point: If True, return point forecasts instead of quantiles
                         (only applicable if forecaster supports this)

        Returns:
            pd.DataFrame: The forecast results

        Raises:
            ValueError: If horizon is invalid or loaded data is empty
        """
        # Validate horizon parameter (BUG-011 fix)
        if not isinstance(horizon, int) or horizon <= 0:
            raise ValueError(
                f"horizon must be a positive integer, got: {horizon} (type: {type(horizon).__name__})"
            )

        # Step 1: Load data
        df = self.data_reader.load()

        # Validate loaded data (BUG-012 fix)
        if df is None or df.empty:
            raise ValueError(
                "Data reader returned empty dataset. Cannot proceed with forecast."
            )

        # Step 2: Transform data (if transformer is provided)
        if self.transformer is not None:
            df = self.transformer.pivot_table(df)
            # Validate transformed data
            if df.empty:
                raise ValueError(
                    "Transformer returned empty dataset. Check your transformation configuration."
                )

        # Step 3: Generate forecast
        # Check if forecaster supports return_point parameter using inspect (BUG-010 fix)
        sig = inspect.signature(self.forecaster.forecast)
        supports_return_point = 'return_point' in sig.parameters

        if supports_return_point:
            forecast_df = self.forecaster.forecast(
                dataframe=df,
                horizon=horizon,
                return_point=return_point
            )
        else:
            # Forecaster doesn't support return_point, call without it
            forecast_df = self.forecaster.forecast(
                dataframe=df,
                horizon=horizon
            )

        # Step 4: Write results to output
        self.data_writer.write(forecast_df)

        return forecast_df

    def run_without_output(
        self,
        horizon: int,
        return_point: bool = False
    ) -> pd.DataFrame:
        """
        Execute forecast workflow without writing to output.

        Useful for testing or when you want to inspect results before writing.

        Args:
            horizon: Number of periods to forecast
            return_point: If True, return point forecasts instead of quantiles

        Returns:
            pd.DataFrame: The forecast results

        Raises:
            ValueError: If horizon is invalid or loaded data is empty
        """
        # Validate horizon parameter
        if not isinstance(horizon, int) or horizon <= 0:
            raise ValueError(
                f"horizon must be a positive integer, got: {horizon} (type: {type(horizon).__name__})"
            )

        # Step 1: Load data
        df = self.data_reader.load()

        # Validate loaded data
        if df is None or df.empty:
            raise ValueError(
                "Data reader returned empty dataset. Cannot proceed with forecast."
            )

        # Step 2: Transform data (if transformer is provided)
        if self.transformer is not None:
            df = self.transformer.pivot_table(df)
            # Validate transformed data
            if df.empty:
                raise ValueError(
                    "Transformer returned empty dataset. Check your transformation configuration."
                )

        # Step 3: Generate forecast
        # Check if forecaster supports return_point parameter using inspect
        sig = inspect.signature(self.forecaster.forecast)
        supports_return_point = 'return_point' in sig.parameters

        if supports_return_point:
            forecast_df = self.forecaster.forecast(
                dataframe=df,
                horizon=horizon,
                return_point=return_point
            )
        else:
            # Forecaster doesn't support return_point, call without it
            forecast_df = self.forecaster.forecast(
                dataframe=df,
                horizon=horizon
            )

        return forecast_df
