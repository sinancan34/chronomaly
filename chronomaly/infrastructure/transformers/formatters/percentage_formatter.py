"""
Percentage formatter - DEPRECATED: Use ColumnFormatter.percentage() instead.

This module is kept for backward compatibility.
PercentageFormatter is now an alias to ColumnFormatter.percentage().
"""

import warnings
from typing import List, Union
from .column_formatter import ColumnFormatter


class PercentageFormatter(ColumnFormatter):
    """
    DEPRECATED: Use ColumnFormatter.percentage() instead.

    Format numeric columns as percentage strings.

    This class is now an alias to ColumnFormatter for backward compatibility.
    New code should use ColumnFormatter.percentage() directly:

        # Old way (still works):
        formatter = PercentageFormatter('deviation_pct', decimal_places=1)

        # New way (recommended):
        formatter = ColumnFormatter.percentage('deviation_pct', decimal_places=1)

        # Or with custom function:
        formatter = ColumnFormatter({'deviation_pct': lambda x: f"{x:.1f}%"})

    Args:
        columns: Column name or list of column names to format
        decimal_places: Number of decimal places (default: 1)
        multiply_by_100: If True, multiply value by 100 before formatting (default: False)

    Example - Anomaly deviation formatla:
        formatter = PercentageFormatter('deviation_pct', decimal_places=1)
        # 15.3 → "15.3%"
        formatted = formatter.format(anomaly_df)

    Example - Conversion rate formatla:
        formatter = PercentageFormatter('conversion_rate', decimal_places=2, multiply_by_100=True)
        # 0.153 → "15.30%"
        formatted = formatter.format(metrics_df)

    Example - Birden fazla kolon:
        formatter = PercentageFormatter(['growth_rate', 'change_pct'], decimal_places=1)
        formatted = formatter.format(df)
    """

    def __init__(
        self,
        columns: Union[str, List[str]],
        decimal_places: int = 1,
        multiply_by_100: bool = False
    ):
        warnings.warn(
            "PercentageFormatter is deprecated. Use ColumnFormatter.percentage() instead: "
            "ColumnFormatter.percentage('column', decimal_places=X)",
            DeprecationWarning,
            stacklevel=2
        )

        # Use parent class percentage helper
        formatter = ColumnFormatter.percentage(
            columns=columns,
            decimal_places=decimal_places,
            multiply_by_100=multiply_by_100
        )

        # Initialize with the formatters from the helper
        # Call ColumnFormatter.__init__ directly with formatters dict
        ColumnFormatter.__init__(self, formatter.formatters)
