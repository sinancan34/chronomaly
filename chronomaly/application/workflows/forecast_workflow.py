"""
Main forecast workflow orchestrator.
"""

import pandas as pd
import inspect
from ...infrastructure.data.readers.base import DataReader
from ...infrastructure.forecasters.base import Forecaster
from ...infrastructure.data.writers.base import DataWriter


class ForecastWorkflow:
    """
    Main orchestrator class for the forecast workflow.

    This class coordinates the entire forecasting workflow:
    1. Load data from source (via data_reader)
    2. Generate forecast (via forecaster)
    3. Write results to output (via data_writer)

    All data transformations (pivot, filtering, formatting) should be configured
    at the component level using the transformers parameter.

    Args:
        data_reader: Data reader instance (CSV, SQLite, BigQuery, etc.)
        forecaster: Forecaster instance (TimesFM, etc.)
        data_writer: Data writer instance (SQLite, BigQuery, etc.)

    Example:
        from chronomaly.infrastructure.transformers.pivot import PivotTransformer
        from chronomaly.infrastructure.transformers.filters import ValueFilter
        from chronomaly.infrastructure.transformers.formatters import ColumnFormatter

        # Reader with pivot transformation
        reader = BigQueryDataReader(
            ...,
            transformers={
                'after': [
                    PivotTransformer(
                        index=['date'],
                        columns=['platform', 'channel'],
                        values='sessions'
                    )
                ]
            }
        )

        # Forecaster with input/output transformations
        forecaster = TimesFMForecaster(
            ...,
            transformers={
                'before': [ValueFilter('outliers', max_value=1000, mode='exclude')],
                'after': [ValueFilter('confidence', min_value=0.8, mode='include')]
            }
        )

        # Writer with pre-write transformations
        writer = BigQueryDataWriter(
            ...,
            transformers={
                'before': [
                    ColumnFormatter({'forecast': lambda x: round(x, 2)})
                ]
            }
        )

        workflow = ForecastWorkflow(
            data_reader=reader,
            forecaster=forecaster,
            data_writer=writer
        )
    """

    def __init__(
        self,
        data_reader: DataReader,
        forecaster: Forecaster,
        data_writer: DataWriter
    ):
        self.data_reader = data_reader
        self.forecaster = forecaster
        self.data_writer = data_writer

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

        # Step 1: Load data (transformations handled by reader)
        df = self.data_reader.load()

        # Validate loaded data (BUG-012 fix)
        if df is None or df.empty:
            raise ValueError(
                "Data reader returned empty dataset. Cannot proceed with forecast."
            )

        # Step 2: Generate forecast
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

        # Step 1: Load data (transformations handled by reader)
        df = self.data_reader.load()

        # Validate loaded data
        if df is None or df.empty:
            raise ValueError(
                "Data reader returned empty dataset. Cannot proceed with forecast."
            )

        # Step 2: Generate forecast
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
