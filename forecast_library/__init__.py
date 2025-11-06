"""
Chronomaly - Time Series Forecasting Library

A flexible and extensible library for time series forecasting using Google TimesFM.
Supports multiple data sources (CSV, SQLite, BigQuery) and outputs.
"""

from .pipeline import ForecastPipeline
from .transformers.pivot import DataTransformer

# Data sources
from .data_sources.base import DataSource
from .data_sources.csv_source import CSVDataSource
from .data_sources.sqlite_source import SQLiteDataSource
from .data_sources.bigquery_source import BigQueryDataSource

# Forecasters
from .forecasters.base import Forecaster
from .forecasters.timesfm import TimesFMForecaster

# Output writers
from .outputs.base import OutputWriter
from .outputs.sqlite_writer import SQLiteOutputWriter

__version__ = "0.1.0"

__all__ = [
    # Main pipeline
    "ForecastPipeline",
    "DataTransformer",
    # Data sources
    "DataSource",
    "CSVDataSource",
    "SQLiteDataSource",
    "BigQueryDataSource",
    # Forecasters
    "Forecaster",
    "TimesFMForecaster",
    # Output writers
    "OutputWriter",
    "SQLiteOutputWriter",
]
