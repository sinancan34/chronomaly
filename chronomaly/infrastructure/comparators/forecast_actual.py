"""
Forecast vs Actual anomaly detection implementation.
"""

import pandas as pd
import numpy as np
from typing import Optional, Union, List
from .base import AnomalyDetector
from ..transformers.pivot import DataTransformer


class ForecastActualComparator(AnomalyDetector):
    """
    Anomaly detector that compares forecast quantiles with actual values.

    This detector:
    1. Pivots actual data (raw format) to match forecast format
    2. Extracts q10 and q90 from pipe-separated forecast values (80% confidence interval)
    3. Compares actual values against the confidence interval
    4. Calculates deviation percentages
    5. Unpivots results for analysis

    The forecast data is expected to be in pivot format with pipe-separated quantiles:
    "point|q10|q20|q30|q40|q50|q60|q70|q80|q90"
    where q10 is at index 1 and q90 is at index 9.

    Args:
        transformer: DataTransformer instance to pivot actual data
        date_column: Name of the date column (default: 'date')
        exclude_columns: List of columns to exclude from comparison (e.g., ['date', 'company'])
    """

    def __init__(
        self,
        transformer: DataTransformer,
        date_column: str = 'date',
        exclude_columns: Optional[List[str]] = None
    ):
        self.transformer = transformer
        self.date_column = date_column
        self.exclude_columns = exclude_columns or [date_column]

    def detect(
        self,
        forecast_df: pd.DataFrame,
        actual_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Detect anomalies by comparing forecast quantiles with actual values.

        Args:
            forecast_df: Forecast data in pivot format with pipe-separated quantiles
            actual_df: Actual data in raw format (will be pivoted)

        Returns:
            pd.DataFrame: Unpivoted anomaly results with columns:
                - date: The date of the observation
                - metric: The metric name (column name from pivot)
                - actual: Actual value
                - forecast: Point forecast (q50)
                - q10: Lower bound of 80% confidence interval
                - q90: Upper bound of 80% confidence interval
                - status: IN_RANGE, BELOW_P10, ABOVE_P90, or NO_FORECAST
                - deviation_pct: Percentage deviation from q10 or q90

        Raises:
            TypeError: If inputs are not pandas DataFrames
            ValueError: If dataframes are empty or incompatible
        """
        # Validate inputs
        if not isinstance(forecast_df, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame for forecast_df, got {type(forecast_df).__name__}"
            )
        if not isinstance(actual_df, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame for actual_df, got {type(actual_df).__name__}"
            )

        if forecast_df.empty:
            raise ValueError("Forecast DataFrame is empty")
        if actual_df.empty:
            raise ValueError("Actual DataFrame is empty")

        # Step 1: Pivot actual data to match forecast format
        actual_pivot = self.transformer.pivot_table(actual_df)
        actual_pivot = actual_pivot.reset_index()

        # Step 2: Standardize columns between forecast and actual
        forecast_cols = set(forecast_df.columns) - set(self.exclude_columns)
        actual_cols = set(actual_pivot.columns) - set(self.exclude_columns)

        # Get all unique columns
        all_columns = sorted(forecast_cols.union(actual_cols))

        # Standardize forecast dataframe
        forecast_std = self._standardize_columns(
            forecast_df.copy(),
            all_columns,
            '0|0|0|0|0|0|0|0|0|0'  # Default pipe-separated zeros
        )

        # Standardize actual dataframe
        actual_std = self._standardize_columns(
            actual_pivot.copy(),
            all_columns,
            0.0  # Default numeric zero
        )

        # Step 3: Compare forecast and actual for each column
        results = []

        # Iterate through data rows (assuming single row or date-based rows)
        for idx in forecast_std.index:
            # Get date if available
            date_value = forecast_std.loc[idx, self.date_column] if self.date_column in forecast_std.columns else None

            forecast_row = forecast_std.loc[idx]
            actual_row = actual_std.loc[idx] if idx in actual_std.index else None

            if actual_row is None:
                continue

            # Compare each metric column
            for column in all_columns:
                result = self._compare_metric(
                    column=column,
                    forecast_value=forecast_row[column],
                    actual_value=actual_row[column],
                    date_value=date_value
                )
                results.append(result)

        # Step 4: Create result dataframe
        result_df = pd.DataFrame(results)

        # Step 5: Filter only anomalies (optional - keep all for transparency)
        # User can filter afterwards if needed

        return result_df

    def _standardize_columns(
        self,
        df: pd.DataFrame,
        column_list: List[str],
        fill_value: Union[str, float]
    ) -> pd.DataFrame:
        """
        Add missing columns with fill values.

        Args:
            df: DataFrame to standardize
            column_list: List of columns that should exist
            fill_value: Value to use for missing columns

        Returns:
            pd.DataFrame: Standardized dataframe
        """
        missing_columns = [col for col in column_list if col not in df.columns]

        if missing_columns:
            new_cols_df = pd.DataFrame(
                fill_value,
                index=df.index,
                columns=missing_columns
            )
            df = pd.concat([df, new_cols_df], axis=1)

        # Fill NaN values
        for column in column_list:
            df[column] = df[column].fillna(fill_value).replace('None', fill_value)

        return df

    def _compare_metric(
        self,
        column: str,
        forecast_value: str,
        actual_value: float,
        date_value: Optional[pd.Timestamp] = None
    ) -> dict:
        """
        Compare a single metric between forecast and actual.

        Args:
            column: Metric name
            forecast_value: Pipe-separated forecast string
            actual_value: Actual numeric value
            date_value: Date of the observation

        Returns:
            dict: Comparison result with status and deviation
        """
        # Parse forecast quantiles
        forecast_parts = str(forecast_value).split('|')

        try:
            # Extract values: point (index 0), q10 (index 1), q90 (index 9)
            point_forecast = float(forecast_parts[0]) if len(forecast_parts) > 0 else 0.0
            q10 = float(forecast_parts[1]) if len(forecast_parts) > 1 else 0.0
            q90 = float(forecast_parts[9]) if len(forecast_parts) > 9 else 0.0
        except (ValueError, IndexError):
            # Invalid forecast format
            point_forecast = 0.0
            q10 = 0.0
            q90 = 0.0

        # Convert actual to float
        try:
            actual = float(actual_value)
        except (ValueError, TypeError):
            actual = 0.0

        # Determine status and deviation
        status = 'NO_FORECAST'
        deviation_pct = 0.0

        if pd.isna(q10) or pd.isna(q90):
            status = 'NO_FORECAST'
        elif q10 == 0 and q90 == 0:
            status = 'NO_FORECAST'
        elif q10 <= actual <= q90:
            status = 'IN_RANGE'
        else:
            if actual < q10:
                status = 'BELOW_P10'
                deviation_pct = ((q10 - actual) / q10 * 100) if q10 != 0 else 0.0
            elif actual > q90:
                status = 'ABOVE_P90'
                deviation_pct = ((actual - q90) / q90 * 100) if q90 != 0 else 0.0

        result = {
            'metric': column,
            'actual': round(actual, 2),
            'forecast': round(point_forecast, 2),
            'q10': round(q10, 2),
            'q90': round(q90, 2),
            'status': status,
            'deviation_pct': round(deviation_pct, 2)
        }

        # Add date if available
        if date_value is not None:
            result = {'date': date_value, **result}

        return result

    def detect_with_filter(
        self,
        forecast_df: pd.DataFrame,
        actual_df: pd.DataFrame,
        min_deviation_pct: float = 5.0,
        exclude_no_forecast: bool = True
    ) -> pd.DataFrame:
        """
        Detect anomalies with filtering options.

        Args:
            forecast_df: Forecast data in pivot format
            actual_df: Actual data in raw format
            min_deviation_pct: Minimum deviation percentage to include (default: 5%)
            exclude_no_forecast: Exclude NO_FORECAST status (default: True)

        Returns:
            pd.DataFrame: Filtered anomaly results
        """
        # Run full detection
        result_df = self.detect(forecast_df, actual_df)

        # Apply filters
        if exclude_no_forecast:
            result_df = result_df[result_df['status'] != 'NO_FORECAST']

        # Filter by deviation percentage
        result_df = result_df[
            (result_df['status'] == 'IN_RANGE') |
            (result_df['deviation_pct'] >= min_deviation_pct)
        ]

        return result_df
