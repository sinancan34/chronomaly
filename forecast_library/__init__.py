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

# Forecasters
from .forecasters.base import Forecaster

# Output writers
from .outputs.base import OutputWriter
from .outputs.sqlite_writer import SQLiteOutputWriter

__version__ = "0.1.0"

# Build __all__ dynamically based on available optional dependencies
__all__ = [
    # Main pipeline
    "ForecastPipeline",
    "DataTransformer",
    # Data sources
    "DataSource",
    "CSVDataSource",
    "SQLiteDataSource",
    # Forecasters
    "Forecaster",
    # Output writers
    "OutputWriter",
    "SQLiteOutputWriter",
]

# Optional: BigQuery support
try:
    from .data_sources.bigquery_source import BigQueryDataSource
    __all__.append("BigQueryDataSource")
except ImportError:
    pass

try:
    from .outputs.bigquery_writer import BigQueryOutputWriter
    __all__.append("BigQueryOutputWriter")
except ImportError:
    pass

# Optional: TimesFM support
try:
    from .forecasters.timesfm import TimesFMForecaster
    __all__.append("TimesFMForecaster")
except ImportError:
    pass
