"""
TimesFM forecaster implementation.
"""

import pandas as pd
import numpy as np
import torch
from typing import Optional, Dict, Any, List, Callable
from .base import Forecaster
from chronomaly.shared import TransformableMixin

try:
    import timesfm
except ImportError:
    raise ImportError(
        "timesfm is required for TimesFMForecaster. "
        "Install it with: pip install timesfm"
    )


class TimesFMForecaster(Forecaster, TransformableMixin):
    """
    Forecaster implementation using Google's TimesFM model.

    This forecaster supports both point forecasts and quantile forecasts.
    Quantile values are returned as pipe-separated strings.

    Args:
        model_name: TimesFM model name (default: 'google/timesfm-2.5-200m-pytorch')
        max_context: Maximum context length (default: 1024)
        max_horizon: Maximum forecast horizon (default: 256)
        normalize_inputs: Whether to normalize inputs (default: True)
        use_continuous_quantile_head: Use continuous quantile head (default: True)
        force_flip_invariance: Force flip invariance (default: True)
        infer_is_positive: Infer if data is positive (default: True)
        fix_quantile_crossing: Fix quantile crossing (default: True)
        frequency: Pandas frequency string for forecast dates (default: 'D' for daily)
                  Common values: 'D' (daily), 'H' (hourly), 'W' (weekly), 'M' (monthly)
        transformers: Optional dict of transformer lists to apply before/after forecasting
                     Example: {'before': [Filter1()], 'after': [Filter2()]}
        **kwargs: Additional configuration parameters
    """

    def __init__(
        self,
        model_name: str = 'google/timesfm-2.5-200m-pytorch',
        max_context: int = 1024,
        max_horizon: int = 256,
        normalize_inputs: bool = True,
        use_continuous_quantile_head: bool = True,
        force_flip_invariance: bool = True,
        infer_is_positive: bool = True,
        fix_quantile_crossing: bool = True,
        frequency: str = 'D',
        transformers: Optional[Dict[str, List[Callable]]] = None,
        **kwargs: Any
    ):
        self.model_name = model_name
        self.max_horizon = max_horizon  # Store for validation
        self.frequency = frequency  # BUG-34 FIX: Make frequency configurable
        self.transformers = transformers or {}
        self.config = timesfm.ForecastConfig(
            max_context=max_context,
            max_horizon=max_horizon,
            normalize_inputs=normalize_inputs,
            use_continuous_quantile_head=use_continuous_quantile_head,
            force_flip_invariance=force_flip_invariance,
            infer_is_positive=infer_is_positive,
            fix_quantile_crossing=fix_quantile_crossing,
            **kwargs
        )
        self._model = None

    def _get_model(self):
        """
        Initialize and compile TimesFM model.

        Returns:
            Compiled TimesFM model
        """
        if self._model is None:
            torch.set_float32_matmul_precision('high')

            self._model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
                self.model_name
            )
            self._model.compile(self.config)

        return self._model


    def forecast(
        self,
        dataframe: pd.DataFrame,
        horizon: int,
        return_point: bool = False
    ) -> pd.DataFrame:
        """
        Generate forecast using TimesFM model.

        Args:
            dataframe: Input pandas DataFrame with time series in columns
            horizon: Number of periods to forecast
            return_point: If True, return point forecasts instead of quantiles

        Returns:
            pd.DataFrame: Forecast results with date column and quantile values

        Raises:
            TypeError: If dataframe is not a pandas DataFrame
            ValueError: If dataframe is empty, has no columns, or horizon is invalid
        """
        # BUG-44 FIX: Validate dataframe type
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame, got {type(dataframe).__name__}"
            )

        # BUG-32 FIX: Validate dataframe is not empty
        if dataframe.empty:
            raise ValueError("Cannot forecast on empty DataFrame")

        if len(dataframe.columns) == 0:
            raise ValueError("DataFrame has no columns to forecast")

        # BUG-33 FIX: Validate horizon
        if not isinstance(horizon, int):
            raise TypeError(f"horizon must be an integer, got {type(horizon).__name__}")

        if horizon <= 0:
            raise ValueError(f"horizon must be positive, got {horizon}")

        if horizon > self.max_horizon:
            raise ValueError(
                f"Requested horizon ({horizon}) exceeds max_horizon ({self.max_horizon}). "
                f"Please reduce horizon or increase max_horizon in forecaster configuration."
            )

        # Apply transformers before forecasting (on input data)
        dataframe = self._apply_transformers(dataframe, 'before')

        model = self._get_model()

        # Prepare inputs - each column is a separate time series
        inputs = [dataframe[column].values for column in dataframe.columns]

        # Generate forecasts
        try:
            forecast_point, forecast_quantile = model.forecast(
                horizon=horizon,
                inputs=inputs
            )
        except Exception as e:
            raise RuntimeError(
                f"TimesFM forecast failed: {str(e)}"
            ) from e

        if return_point:
            # Return point forecasts
            forecast_df = self._format_point_forecast(
                forecast_point, dataframe, horizon
            )
        else:
            # Return quantile forecasts (default)
            forecast_df = self._format_quantile_forecast(
                forecast_quantile, dataframe, horizon
            )

        # Apply transformers after forecasting
        forecast_df = self._apply_transformers(forecast_df, 'after')

        return forecast_df

    def _get_last_date(self, dataframe: pd.DataFrame) -> pd.Timestamp:
        """
        Extract the last date from dataframe index.

        Handles both DatetimeIndex and regular index that can be converted to datetime.

        Args:
            dataframe: Input pandas DataFrame

        Returns:
            pd.Timestamp: The last date in the index

        Raises:
            ValueError: If index cannot be converted to datetime or dataframe is empty
        """
        # BUG-46 FIX: Check if dataframe is empty before accessing index
        if dataframe.empty or len(dataframe) == 0:
            raise ValueError("Cannot get last date from empty DataFrame")

        # Get the last index value
        last_idx = dataframe.index[-1]

        # Check if index is already a DatetimeIndex
        if isinstance(dataframe.index, pd.DatetimeIndex):
            return last_idx

        # Check if it's a MultiIndex
        if isinstance(dataframe.index, pd.MultiIndex):
            # Try to find a date level in the MultiIndex
            for level_idx in range(dataframe.index.nlevels):
                level_values = dataframe.index.get_level_values(level_idx)
                try:
                    # Try to convert this level to datetime
                    if isinstance(level_values, pd.DatetimeIndex):
                        return level_values[-1]
                    else:
                        return pd.to_datetime(level_values[-1])
                except (ValueError, TypeError):
                    continue

            raise ValueError(
                f"Could not find a datetime level in MultiIndex. "
                f"Index levels: {dataframe.index.names}. "
                f"Please ensure your dataframe has a datetime index or "
                f"a MultiIndex with at least one datetime level."
            )

        # Try to convert the last index value to datetime
        try:
            return pd.to_datetime(last_idx)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Could not parse index value '{last_idx}' as datetime. "
                f"Index type: {type(dataframe.index).__name__}. "
                f"Please ensure your dataframe has a datetime index. "
                f"Original error: {str(e)}"
            )

    def _format_point_forecast(
        self,
        forecast_point: np.ndarray,
        dataframe: pd.DataFrame,
        horizon: int
    ) -> pd.DataFrame:
        """
        Format point forecast results.

        Args:
            forecast_point: Point forecast array from TimesFM
            dataframe: Original input dataframe
            horizon: Forecast horizon

        Returns:
            pd.DataFrame: Formatted forecast with date column
        """
        forecast_data = forecast_point.T

        # BUG-34 FIX: Use configurable frequency instead of hardcoded 'D'
        # Generate future dates
        last_date = self._get_last_date(dataframe)

        # Calculate the appropriate offset based on frequency
        if self.frequency == 'D':
            start_date = last_date + pd.Timedelta(days=1)
        elif self.frequency == 'H':
            start_date = last_date + pd.Timedelta(hours=1)
        elif self.frequency == 'W':
            start_date = last_date + pd.Timedelta(weeks=1)
        elif self.frequency == 'M':
            start_date = last_date + pd.DateOffset(months=1)
        else:
            # For other frequencies, use pd.date_range to calculate offset
            start_date = last_date + pd.tseries.frequencies.to_offset(self.frequency)

        new_index = pd.date_range(
            start=start_date,
            periods=horizon,
            freq=self.frequency
        )

        # Create forecast dataframe
        dataframe_forecast = pd.DataFrame(
            forecast_data,
            columns=dataframe.columns
        )
        dataframe_forecast.columns.name = None
        dataframe_forecast.insert(0, "date", new_index)
        dataframe_forecast['date'] = dataframe_forecast['date'].dt.date

        return dataframe_forecast

    def _format_quantile_forecast(
        self,
        forecast_quantile: np.ndarray,
        dataframe: pd.DataFrame,
        horizon: int
    ) -> pd.DataFrame:
        """
        Format quantile forecast results.

        Quantile values are combined into pipe-separated strings.

        Args:
            forecast_quantile: Quantile forecast array from TimesFM
            dataframe: Original input dataframe
            horizon: Forecast horizon

        Returns:
            pd.DataFrame: Formatted forecast with date column and quantile values
        """
        (
            forecast_quantile_items,
            forecast_quantile_horizons,
            forecast_quantile_quantiles
        ) = forecast_quantile.shape

        # Format quantiles as pipe-separated strings
        forecast_data = []

        for forecast_quantile_item in range(forecast_quantile_items):
            forecast_data_row = []

            for forecast_quantile_horizon in range(forecast_quantile_horizons):
                cell_value = "|".join(
                    map(str, forecast_quantile[
                        forecast_quantile_item,
                        forecast_quantile_horizon,
                        :
                    ])
                )
                forecast_data_row.append(cell_value)

            forecast_data.append(forecast_data_row)

        forecast_data = np.array(forecast_data, dtype=object).T

        # BUG-34 FIX: Use configurable frequency instead of hardcoded 'D'
        # Generate future dates
        last_date = self._get_last_date(dataframe)

        # Calculate the appropriate offset based on frequency
        if self.frequency == 'D':
            start_date = last_date + pd.Timedelta(days=1)
        elif self.frequency == 'H':
            start_date = last_date + pd.Timedelta(hours=1)
        elif self.frequency == 'W':
            start_date = last_date + pd.Timedelta(weeks=1)
        elif self.frequency == 'M':
            start_date = last_date + pd.DateOffset(months=1)
        else:
            start_date = last_date + pd.tseries.frequencies.to_offset(self.frequency)

        new_index = pd.date_range(
            start=start_date,
            periods=forecast_quantile_horizons,
            freq=self.frequency
        )

        # Create forecast dataframe
        dataframe_forecast = pd.DataFrame(
            forecast_data,
            columns=dataframe.columns
        )
        dataframe_forecast.columns.name = None
        dataframe_forecast.insert(0, "date", new_index)
        dataframe_forecast['date'] = dataframe_forecast['date'].dt.date

        return dataframe_forecast
