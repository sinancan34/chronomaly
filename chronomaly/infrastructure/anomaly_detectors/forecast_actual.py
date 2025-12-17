"""
Forecast vs Actual anomaly detection implementation.
"""

import warnings
import pandas as pd
from typing import Optional, List, Dict, Callable
from .base import AnomalyDetector
from chronomaly.shared import TransformableMixin


class ForecastActualAnomalyDetector(AnomalyDetector, TransformableMixin):
    """
    Anomaly detector that compares forecast quantiles with actual values.

    This detector focuses SOLELY on anomaly detection. Data transformations
    (filtering, formatting, pivoting) should be configured via the
    transformers parameter.

    Note: The actual_df should be already pivoted before passing to detect() method.
    Use PivotTransformer outside the detector if needed.

    Args:
        dimension_names: List of dimension names to extract from group_key (required)
        metric_name: Name of the metric being forecasted, e.g. 'impressions' (required)
        date_column: Name of the date column (default: 'date')
        exclude_columns: List of columns to exclude from comparison
        lower_quantile_idx: Index of lower confidence bound (default: 1 for q10)
        upper_quantile_idx: Index of upper confidence bound (default: 9 for q90)
        transformers: Optional dict of transformer lists to apply after detection
    """

    QUANTILE_POINT_IDX = 0
    EXPECTED_QUANTILE_COUNT = 10

    def __init__(
        self,
        dimension_names: List[str],
        metric_name: str,
        date_column: str = "date",
        exclude_columns: Optional[List[str]] = None,
        lower_quantile_idx: int = 1,
        upper_quantile_idx: int = 9,
        transformers: Optional[Dict[str, List[Callable]]] = None,
    ):
        # Validate required parameters
        if not dimension_names:
            raise ValueError("dimension_names is required and cannot be empty")
        if not metric_name:
            raise ValueError("metric_name is required and cannot be empty")
        if not isinstance(dimension_names, list):
            raise TypeError(
                f"dimension_names must be a list, got {type(dimension_names).__name__}"
            )

        self.dimension_names: list[str] = dimension_names
        self.metric_name: str = metric_name
        self.date_column: str = date_column
        self.exclude_columns: list[str] = exclude_columns or [date_column]
        self.lower_quantile_idx: int = lower_quantile_idx
        self.upper_quantile_idx: int = upper_quantile_idx
        self.transformers: dict[str, list[Callable]] = transformers or {}

    @property
    def _result_schema(self) -> dict[str, str]:
        """
        Define the schema for result DataFrame columns.

        This is the single source of truth for column names and dtypes.
        Used by both _get_empty_result_dataframe and _compare_metric.

        Returns:
            dict: Column names mapped to their pandas dtypes
        """
        schema = {
            self.date_column: 'datetime64[ns]',
            'group_key': 'object',
            'metric_name': 'object',
            'actual_value': 'int64',
            'forecast_value': 'int64',
            'lower_limit': 'int64',
            'upper_limit': 'int64',
            'alert_type': 'object',
            'anomaly_score': 'float64',
        }
        # Add dimension columns
        for dim_name in self.dimension_names:
            schema[dim_name] = 'object'
        return schema

    def detect(
        self, forecast_df: pd.DataFrame, actual_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Detect anomalies by comparing forecast quantiles with actual values."""
        self._validate_inputs(forecast_df, actual_df)
        forecast_std, actual_std, all_columns = self._prepare_data(
            forecast_df, actual_df
        )
        results = self._compare_all_metrics(forecast_std, actual_std, all_columns)

        if not results:
            empty_df = self._get_empty_result_dataframe()
            # Apply transformers to empty DataFrame for consistency
            empty_df = self._apply_transformers(empty_df, "after")
            return empty_df

        result_df = pd.DataFrame(results)

        result_df = self._split_group_key_to_dimensions(result_df)

        # Apply transformers after detection
        result_df = self._apply_transformers(result_df, "after")

        return result_df

    def _validate_inputs(self, forecast_df: pd.DataFrame, actual_df: pd.DataFrame):
        """
        Validate input DataFrames.

        Args:
            forecast_df: Forecast data (pivoted format)
            actual_df: Actual data (must be pivoted format)

        Raises:
            TypeError: If inputs are not DataFrames
            ValueError: If DataFrames are empty or actual_df is not pivoted
        """
        if not isinstance(forecast_df, pd.DataFrame):
            raise TypeError(
                f"Expected DataFrame for forecast_df, got {type(forecast_df).__name__}"
            )
        if not isinstance(actual_df, pd.DataFrame):
            raise TypeError(
                f"Expected DataFrame for actual_df, got {type(actual_df).__name__}"
            )
        if forecast_df.empty:
            raise ValueError("Forecast DataFrame is empty")
        if actual_df.empty:
            raise ValueError("Actual DataFrame is empty")

        # Validate that actual_df is in pivoted format
        self._validate_pivoted_format(actual_df)

    def _validate_pivoted_format(self, df: pd.DataFrame) -> None:
        """
        Validate that DataFrame is in pivoted (wide) format, not long format.

        Pivoted format characteristics:
        - Has date column + multiple metric columns
        - Metric columns contain numeric values
        - NOT long format (date, metric_name, value columns)

        Args:
            df: DataFrame to validate

        Raises:
            ValueError: If DataFrame appears to be in long format instead of pivoted
        """
        # Check for common long-format column names
        long_format_indicators = ["metric", "metric_name", "value", "values", "measure"]
        df_columns_lower = [col.lower() for col in df.columns]

        for indicator in long_format_indicators:
            if indicator in df_columns_lower:
                raise ValueError(
                    f"actual_df appears to be in long format "
                    f"(contains '{indicator}' column). "
                    f"Please pivot the data using PivotTransformer "
                    f"before passing to detect(). "
                )

        # Check that we have more than just the date column
        non_date_columns = [
            col for col in df.columns if col not in self.exclude_columns
        ]
        if len(non_date_columns) == 0:
            raise ValueError(
                "actual_df has no metric columns (only date column found). "
                "Please ensure data is pivoted with metric columns."
            )

    def _prepare_data(
        self, forecast_df: pd.DataFrame, actual_df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
        # Assume actual_df is already pivoted (use PivotTransformer outside if needed)
        actual_pivot = (
            actual_df.reset_index()
            if isinstance(actual_df.index, pd.DatetimeIndex)
            else actual_df.copy()
        )
        forecast_cols = set(forecast_df.columns) - set(self.exclude_columns)
        actual_cols = set(actual_pivot.columns) - set(self.exclude_columns)
        all_columns = sorted(forecast_cols.union(actual_cols))

        forecast_std = self._standardize_columns(
            forecast_df.copy(), all_columns, "0|0|0|0|0|0|0|0|0|0"
        )
        actual_std = self._standardize_columns(actual_pivot.copy(), all_columns, 0.0)

        return forecast_std, actual_std, all_columns

    def _standardize_columns(
        self, df: pd.DataFrame, column_list: List[str], fill_value: float
    ) -> pd.DataFrame:
        missing_columns = [col for col in column_list if col not in df.columns]
        if missing_columns:
            new_cols_df = pd.DataFrame(
                fill_value, index=df.index, columns=missing_columns
            )
            df = pd.concat([df, new_cols_df], axis=1)

        for column in column_list:
            df[column] = df[column].fillna(fill_value).replace("None", fill_value)

        return df

    def _compare_all_metrics(
        self,
        forecast_std: pd.DataFrame,
        actual_std: pd.DataFrame,
        all_columns: list[str],
    ) -> list[dict]:
        results = []
        for idx in forecast_std.index:
            date_value = (
                forecast_std.loc[idx, self.date_column]
                if self.date_column in forecast_std.columns
                else None
            )
            forecast_row = forecast_std.loc[idx]
            actual_row = actual_std.loc[idx] if idx in actual_std.index else None

            if actual_row is None:
                continue

            for column in all_columns:
                result = self._compare_metric(
                    column, forecast_row[column], actual_row[column], date_value
                )
                results.append(result)

        return results

    def _compare_metric(
        self,
        column: str,
        forecast_value: str,
        actual_value: float,
        date_value: Optional[pd.Timestamp] = None,
    ) -> dict:
        forecast_parts = str(forecast_value).split("|")

        try:
            point_forecast = (
                float(forecast_parts[self.QUANTILE_POINT_IDX])
                if len(forecast_parts) > self.QUANTILE_POINT_IDX
                else 0.0
            )
            lower_bound = (
                float(forecast_parts[self.lower_quantile_idx])
                if len(forecast_parts) > self.lower_quantile_idx
                else 0.0
            )
            upper_bound = (
                float(forecast_parts[self.upper_quantile_idx])
                if len(forecast_parts) > self.upper_quantile_idx
                else 0.0
            )

            if len(forecast_parts) < self.EXPECTED_QUANTILE_COUNT:
                warnings.warn(
                    f"Expected {self.EXPECTED_QUANTILE_COUNT} quantiles, "
                    f"got {len(forecast_parts)}."
                )
        except (ValueError, IndexError):
            point_forecast = lower_bound = upper_bound = 0.0

        try:
            actual = float(actual_value)
        except (ValueError, TypeError):
            actual = 0.0

        status = "NO_FORECAST"
        deviation_pct = 0.0

        if pd.isna(lower_bound) or pd.isna(upper_bound) or pd.isna(point_forecast):
            status = "NO_FORECAST"
        elif lower_bound == 0 and upper_bound == 0 and point_forecast == 0:
            status = "NO_FORECAST"
        elif lower_bound <= actual <= upper_bound:
            status = "IN_RANGE"
        else:
            if actual < lower_bound:
                status = "BELOW_LOWER"
                deviation_pct = (
                    ((lower_bound - actual) / lower_bound)
                    if lower_bound != 0
                    else (abs(actual) if actual != 0 else 0.0)
                )
            elif actual > upper_bound:
                status = "ABOVE_UPPER"
                deviation_pct = (
                    ((actual - upper_bound) / upper_bound)
                    if upper_bound != 0
                    else (abs(actual) if actual != 0 else 0.0)
                )

        result = {
            "group_key": column,
            "metric_name": self.metric_name,
            "actual_value": round(actual),
            "forecast_value": round(point_forecast),
            "lower_limit": round(lower_bound),
            "upper_limit": round(upper_bound),
            "alert_type": status,
            "anomaly_score": round(deviation_pct, 2),
        }

        if date_value is not None:
            # Convert to date only (remove time component for consistency)
            if isinstance(date_value, pd.Timestamp):
                date_value = date_value.date()
            result = {self.date_column: date_value, **result}

        return result

    def _get_empty_result_dataframe(self) -> pd.DataFrame:
        """
        Create an empty DataFrame with the correct schema for anomaly detection results.

        Uses _result_schema property as the single source of truth for column
        names and data types.

        Returns:
            pd.DataFrame: Empty DataFrame with complete schema
        """
        schema = {
            col: pd.Series(dtype=dtype)
            for col, dtype in self._result_schema.items()
        }
        return pd.DataFrame(schema)

    def _split_group_key_to_dimensions(self, df: pd.DataFrame):
        """Split group_key column into separate dimension columns."""
        if "group_key" not in df.columns:
            return df

        df = df.copy()
        group_key_parts = df["group_key"].str.split("_", expand=True)

        for i, dim_name in enumerate(self.dimension_names):
            if i < group_key_parts.shape[1]:
                df[dim_name] = group_key_parts[i]
            else:
                df[dim_name] = None

        return df


# Backward compatibility alias
ForecastActualComparator = ForecastActualAnomalyDetector
