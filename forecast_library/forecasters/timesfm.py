"""
TimesFM forecaster implementation.
"""

import pandas as pd
import numpy as np
import torch
from typing import Optional, Dict, Any
from .base import Forecaster

try:
    import timesfm
except ImportError:
    raise ImportError(
        "timesfm is required for TimesFMForecaster. "
        "Install it with: pip install timesfm"
    )


class TimesFMForecaster(Forecaster):
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
        **kwargs: Any
    ):
        self.model_name = model_name
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
        """
        model = self._get_model()

        # Prepare inputs - each column is a separate time series
        inputs = [dataframe[column].values for column in dataframe.columns]

        # Generate forecasts
        forecast_point, forecast_quantile = model.forecast(
            horizon=horizon,
            inputs=inputs
        )

        if return_point:
            # Return point forecasts
            return self._format_point_forecast(
                forecast_point, dataframe, horizon
            )
        else:
            # Return quantile forecasts (default)
            return self._format_quantile_forecast(
                forecast_quantile, dataframe, horizon
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

        # Generate future dates
        last_date = pd.to_datetime(dataframe.index[-1])
        new_index = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=horizon,
            freq='D'
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

        # Generate future dates
        last_date = pd.to_datetime(dataframe.index[-1])
        new_index = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=forecast_quantile_horizons,
            freq='D'
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
