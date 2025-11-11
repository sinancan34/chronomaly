"""
Forecast vs Actual anomaly detection implementation.
"""

import warnings
import pandas as pd
import numpy as np
from typing import Optional, List
from .base import AnomalyDetector
from ..transformers.pivot import PivotTransformer


class ForecastActualAnomalyDetector(AnomalyDetector):
    """
    Anomaly detector that compares forecast quantiles with actual values.

    This detector focuses SOLELY on anomaly detection. It does NOT include:
    - Pre-filtering (use PreFilter classes)
    - Post-filtering (use PostFilter classes)
    - Result formatting (use PostFilter classes)

    Args:
        transformer: PivotTransformer instance to pivot actual data
        date_column: Name of the date column (default: 'date')
        exclude_columns: List of columns to exclude from comparison
        dimension_names: List of dimension names to extract from metric
        lower_quantile_idx: Index of lower confidence bound (default: 1 for q10)
        upper_quantile_idx: Index of upper confidence bound (default: 9 for q90)
    """

    QUANTILE_POINT_IDX = 0
    EXPECTED_QUANTILE_COUNT = 10

    def __init__(
        self,
        transformer: PivotTransformer,
        date_column: str = 'date',
        exclude_columns: Optional[List[str]] = None,
        dimension_names: Optional[List[str]] = None,
        lower_quantile_idx: int = 1,
        upper_quantile_idx: int = 9
    ):
        self.transformer = transformer
        self.date_column = date_column
        self.exclude_columns = exclude_columns or [date_column]
        self.dimension_names = dimension_names
        self.lower_quantile_idx = lower_quantile_idx
        self.upper_quantile_idx = upper_quantile_idx

        if dimension_names is not None:
            self._validate_dimension_names()

    def _validate_dimension_names(self):
        if not hasattr(self.transformer, 'columns'):
            return

        transformer_columns = self.transformer.columns
        if isinstance(transformer_columns, str):
            transformer_columns = [transformer_columns]
        else:
            transformer_columns = list(transformer_columns)

        dimension_names = list(self.dimension_names)

        if dimension_names != transformer_columns:
            raise ValueError(
                f"dimension_names must match transformer.columns in the same order.\n"
                f"  dimension_names: {dimension_names}\n"
                f"  transformer.columns: {transformer_columns}"
            )

    def detect(self, forecast_df: pd.DataFrame, actual_df: pd.DataFrame) -> pd.DataFrame:
        """Detect anomalies by comparing forecast quantiles with actual values."""
        self._validate_inputs(forecast_df, actual_df)
        forecast_std, actual_std, all_columns = self._prepare_data(forecast_df, actual_df)
        results = self._compare_all_metrics(forecast_std, actual_std, all_columns)

        if not results:
            return pd.DataFrame()

        result_df = pd.DataFrame(results)

        if self.dimension_names:
            result_df = self._split_metric_to_dimensions(result_df)
            if 'metric' in result_df.columns:
                result_df = result_df.drop(columns=['metric'])

        return result_df

    def _validate_inputs(self, forecast_df: pd.DataFrame, actual_df: pd.DataFrame):
        if not isinstance(forecast_df, pd.DataFrame):
            raise TypeError(f"Expected DataFrame for forecast_df, got {type(forecast_df).__name__}")
        if not isinstance(actual_df, pd.DataFrame):
            raise TypeError(f"Expected DataFrame for actual_df, got {type(actual_df).__name__}")
        if forecast_df.empty:
            raise ValueError("Forecast DataFrame is empty")
        if actual_df.empty:
            raise ValueError("Actual DataFrame is empty")

    def _prepare_data(self, forecast_df: pd.DataFrame, actual_df: pd.DataFrame):
        actual_pivot = self.transformer.pivot_table(actual_df).reset_index()
        forecast_cols = set(forecast_df.columns) - set(self.exclude_columns)
        actual_cols = set(actual_pivot.columns) - set(self.exclude_columns)
        all_columns = sorted(forecast_cols.union(actual_cols))

        forecast_std = self._standardize_columns(forecast_df.copy(), all_columns, '0|0|0|0|0|0|0|0|0|0')
        actual_std = self._standardize_columns(actual_pivot.copy(), all_columns, 0.0)

        return forecast_std, actual_std, all_columns

    def _standardize_columns(self, df: pd.DataFrame, column_list: List[str], fill_value):
        missing_columns = [col for col in column_list if col not in df.columns]
        if missing_columns:
            new_cols_df = pd.DataFrame(fill_value, index=df.index, columns=missing_columns)
            df = pd.concat([df, new_cols_df], axis=1)

        for column in column_list:
            df[column] = df[column].fillna(fill_value).replace('None', fill_value)

        return df

    def _compare_all_metrics(self, forecast_std: pd.DataFrame, actual_std: pd.DataFrame, all_columns: list):
        results = []
        for idx in forecast_std.index:
            date_value = forecast_std.loc[idx, self.date_column] if self.date_column in forecast_std.columns else None
            forecast_row = forecast_std.loc[idx]
            actual_row = actual_std.loc[idx] if idx in actual_std.index else None

            if actual_row is None:
                continue

            for column in all_columns:
                result = self._compare_metric(column, forecast_row[column], actual_row[column], date_value)
                results.append(result)

        return results

    def _compare_metric(self, column: str, forecast_value: str, actual_value: float, date_value: Optional[pd.Timestamp] = None):
        forecast_parts = str(forecast_value).split('|')

        try:
            point_forecast = float(forecast_parts[self.QUANTILE_POINT_IDX]) if len(forecast_parts) > self.QUANTILE_POINT_IDX else 0.0
            lower_bound = float(forecast_parts[self.lower_quantile_idx]) if len(forecast_parts) > self.lower_quantile_idx else 0.0
            upper_bound = float(forecast_parts[self.upper_quantile_idx]) if len(forecast_parts) > self.upper_quantile_idx else 0.0

            if len(forecast_parts) < self.EXPECTED_QUANTILE_COUNT:
                warnings.warn(f"Expected {self.EXPECTED_QUANTILE_COUNT} quantiles, got {len(forecast_parts)}.")
        except (ValueError, IndexError):
            point_forecast = lower_bound = upper_bound = 0.0

        try:
            actual = float(actual_value)
        except (ValueError, TypeError):
            actual = 0.0

        status = 'NO_FORECAST'
        deviation_pct = 0.0

        if pd.isna(lower_bound) or pd.isna(upper_bound) or pd.isna(point_forecast):
            status = 'NO_FORECAST'
        elif lower_bound == 0 and upper_bound == 0 and point_forecast == 0:
            status = 'NO_FORECAST'
        elif lower_bound <= actual <= upper_bound:
            status = 'IN_RANGE'
        else:
            if actual < lower_bound:
                status = 'BELOW_LOWER'
                deviation_pct = ((lower_bound - actual) / lower_bound * 100) if lower_bound != 0 else (abs(actual) * 100 if actual != 0 else 0.0)
            elif actual > upper_bound:
                status = 'ABOVE_UPPER'
                deviation_pct = ((actual - upper_bound) / upper_bound * 100) if upper_bound != 0 else (abs(actual) * 100 if actual != 0 else 0.0)

        result = {
            'metric': column,
            'actual': round(actual),
            'forecast': round(point_forecast),
            'lower_bound': round(lower_bound),
            'upper_bound': round(upper_bound),
            'status': status,
            'deviation_pct': round(deviation_pct, 2)
        }

        if date_value is not None:
            result = {'date': date_value, **result}

        return result

    def _split_metric_to_dimensions(self, df: pd.DataFrame):
        if 'metric' not in df.columns or not self.dimension_names:
            return df

        df = df.copy()
        metric_parts = df['metric'].str.split('_', expand=True)

        for i, dim_name in enumerate(self.dimension_names):
            if i < metric_parts.shape[1]:
                df[dim_name] = metric_parts[i]
            else:
                df[dim_name] = None

        return df


# Backward compatibility alias  
ForecastActualComparator = ForecastActualAnomalyDetector
