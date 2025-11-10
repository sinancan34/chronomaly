"""
Advanced: Anomaly Detection with Transformers (Filters and Formatters)

This example demonstrates the power of general-purpose transformers:
1. TRANSFORM: Apply transformers at any stage of the pipeline
2. DETECT: Run anomaly detection
3. TRANSFORM: Apply filters and formatters to results

Use Case: Focus on top metrics and format results for reporting

Requirements:
    pip install pandas

Usage:
    python examples/advanced/anomaly_with_filters.py
"""

import pandas as pd
import sqlite3
from datetime import datetime

print("""
╔══════════════════════════════════════════════════════════════════════╗
║          ADVANCED: Anomaly Detection with Filters                    ║
║                                                                      ║
║  Pre-Filter → Detect → Post-Filter → Format → Output                ║
╚══════════════════════════════════════════════════════════════════════╝
""")

# Create comprehensive forecast data
def create_comprehensive_forecast():
    """Create forecast with many metrics."""
    data = pd.DataFrame({
        'date': [datetime(2024, 11, 10)],
        # High-value metrics
        'desktop_organic_home': ['5000|4500|4600|4750|4875|5000|5125|5250|5400|5500'],
        'desktop_paid_product': ['3000|2700|2775|2850|2925|3000|3075|3150|3240|3300'],
        'mobile_organic_home': ['4000|3600|3700|3800|3900|4000|4100|4200|4320|4400'],

        # Medium-value metrics
        'tablet_organic_home': ['1000|900|925|950|975|1000|1025|1050|1080|1100'],
        'tablet_paid_product': ['500|450|465|480|490|500|510|525|540|550'],

        # Low-value metrics (will be filtered out by cumulative threshold)
        'other_organic_blog': ['100|90|92|95|97|100|102|105|108|110'],
        'other_paid_blog': ['50|45|46|48|49|50|51|52|54|55']
    })

    data.to_csv('/tmp/comprehensive_forecast.csv', index=False)
    print("✓ Created forecast with 7 metrics")
    return data


# Create actual data with anomalies
def create_actual_with_anomalies():
    """Create actual data with various anomaly types."""
    data = pd.DataFrame({
        'date': [datetime(2024, 11, 10)] * 7,
        'platform': ['desktop', 'desktop', 'mobile', 'tablet', 'tablet', 'other', 'other'],
        'channel': ['organic', 'paid', 'organic', 'organic', 'paid', 'organic', 'paid'],
        'page': ['home', 'product', 'home', 'home', 'product', 'blog', 'blog'],
        'sessions': [
            4800,   # desktop_organic_home: IN_RANGE
            3500,   # desktop_paid_product: ABOVE_UPPER (16.67% deviation)
            3200,   # mobile_organic_home: BELOW_LOWER (11.11% deviation)
            980,    # tablet_organic_home: IN_RANGE
            480,    # tablet_paid_product: IN_RANGE
            105,    # other_organic_blog: IN_RANGE (but will be filtered by pre-filter)
            52      # other_paid_blog: IN_RANGE (but will be filtered by pre-filter)
        ]
    })

    data.to_csv('/tmp/comprehensive_actual.csv', index=False)
    print("✓ Created actual data with 7 metrics")
    return data


print("\n📋 WORKFLOW CONFIGURATION")
print("=" * 70)
print("Input:        /tmp/comprehensive_forecast.csv (7 metrics)")
print("              /tmp/comprehensive_actual.csv")
print("Transformers: ValueFilter (categorical + numeric filtering)")
print("              ColumnFormatter (format as percentage)")
print("Output:       /tmp/filtered_anomalies.db")
print()

forecast = create_comprehensive_forecast()
actual = create_actual_with_anomalies()

print("\n🔧 WORKFLOW CODE")
print("=" * 70)

workflow_code = '''
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.anomaly_detectors import ForecastActualAnomalyDetector
from chronomaly.infrastructure.transformers import DataTransformer

# Import general-purpose transformers
from chronomaly.infrastructure.transformers.filters import ValueFilter
from chronomaly.infrastructure.transformers.formatters import ColumnFormatter

# Configure readers
forecast_reader = CSVDataReader('/tmp/comprehensive_forecast.csv')
actual_reader = CSVDataReader('/tmp/comprehensive_actual.csv')

# Configure transformer
transformer = DataTransformer(
    index='date',
    columns=['platform', 'channel', 'page'],
    values='sessions'
)

# ═══════════════════════════════════════════════════════════════
# DETECTOR: Pure anomaly detection
# ═══════════════════════════════════════════════════════════════
detector = ForecastActualAnomalyDetector(
    transformer=transformer,
    dimension_names=['platform', 'channel', 'page'],
    lower_quantile_idx=1,   # q10
    upper_quantile_idx=9    # q90
)

# ═══════════════════════════════════════════════════════════════
# TRANSFORMERS: General-purpose DataFrame transformations
# ═══════════════════════════════════════════════════════════════

# Transformer 1: Keep only anomalies (BELOW_LOWER, ABOVE_UPPER)
anomaly_filter = ValueFilter(
    column='status',
    values=['BELOW_LOWER', 'ABOVE_UPPER'],
    mode='include'
)

# Transformer 2: Keep only significant deviations (>10%)
deviation_filter = ValueFilter(
    column='deviation_pct',
    min_value=10.0
)

# Transformer 3: Format deviation as percentage string
formatter = ColumnFormatter.percentage(
    columns='deviation_pct',
    decimal_places=1
)

# ═══════════════════════════════════════════════════════════════
# WORKFLOW: Assemble pipeline with transformers at any stage
# ═══════════════════════════════════════════════════════════════
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=SQLiteDataWriter('/tmp/filtered_anomalies.db', 'anomalies'),
    transformers={
        'after_detection': [
            anomaly_filter,      # Filter to only anomalies
            deviation_filter,    # Filter to significant deviations
            formatter            # Format as percentage
        ]
    }
)

# Run the pipeline
results = workflow.run()

print(f"\\n✓ Pipeline complete!")
print(f"  Input metrics: 7")
print(f"  After detection: {len(results)}")
print(f"  Significant anomalies: {len(results)}")
'''

print(workflow_code)

print("\n\n📊 PIPELINE FLOW")
print("=" * 70)
print("""
Step 1: LOAD FORECAST
  Input:  /tmp/comprehensive_forecast.csv
  Output: 7 metrics with quantiles

Step 2: LOAD ACTUAL
  Input:  /tmp/comprehensive_actual.csv
  Output: 7 actual measurements

Step 3: DETECT ANOMALIES
  Input:  7 forecast + 7 actual
  Detect: Compare actual vs forecast with q10/q90
  Output: 7 detection results (all statuses)

Step 4: TRANSFORM (after_detection)
  Input:  7 detection results
  Filter: ValueFilter (status) → Keep only ABOVE_UPPER/BELOW_LOWER
  Filter: ValueFilter (deviation_pct) → Keep only >10% deviation
  Format: ColumnFormatter.percentage() → "16.7%" instead of 16.7
  Output: 2 significant anomalies

Step 5: WRITE
  Output: Save to SQLite database
""")

print("\n\n📈 EXPECTED RESULTS")
print("=" * 70)

expected_results = pd.DataFrame({
    'date': [datetime(2024, 11, 10)] * 2,
    'platform': ['desktop', 'mobile'],
    'channel': ['paid', 'organic'],
    'page': ['product', 'home'],
    'actual': [3500, 3200],
    'forecast': [3000, 4000],
    'lower_bound': [2700, 3600],
    'upper_bound': [3300, 4400],
    'status': ['ABOVE_UPPER', 'BELOW_LOWER'],
    'deviation_pct': ['16.7%', '11.1%']
})

print(expected_results.to_string(index=False))

print("\n\n💡 WHY USE TRANSFORMERS?")
print("=" * 70)
print("""
1. GENERAL-PURPOSE TRANSFORMERS
   ✓ Apply at ANY stage: after_forecast_read, after_actual_read,
                         after_detection, before_write
   ✓ Not limited to anomaly detection - use in ANY workflow
   ✓ Reusable across different pipelines
   ✓ Example: ValueFilter can filter forecast, actual, or anomaly data

2. TRANSFORMER TYPES
   ✓ Filters: ValueFilter (unified - supports categorical & numeric filtering)
   ✓ Formatters: ColumnFormatter (unified - custom functions or helpers like .percentage())
   ✓ Pivot: DataTransformer (wide ↔ long format)

3. BENEFITS
   ✓ Modular: Add/remove transformers easily
   ✓ Composable: Chain multiple transformers
   ✓ Testable: Test each transformer independently
   ✓ Flexible: Use same transformer in different stages
   ✓ Cleaner code: Detector only detects, transformers transform
""")

print("\n\n🔧 TRANSFORMER CUSTOMIZATION")
print("=" * 70)

customization_code = '''
# Example 1: Apply transformers at different stages
workflow = AnomalyDetectionWorkflow(
    forecast_reader=reader,
    actual_reader=reader,
    anomaly_detector=detector,
    data_writer=writer,
    transformers={
        'after_forecast_read': [
            # Filter forecast data before detection
            ValueFilter('date', datetime(2024, 11, 1), mode='include')
        ],
        'after_actual_read': [
            # Filter actual data before detection (numeric filtering)
            ValueFilter('sessions', min_value=100)
        ],
        'after_detection': [
            # Filter and format results
            ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER']),  # Categorical
            ValueFilter('deviation_pct', min_value=20.0),  # Numeric
            ColumnFormatter.percentage('deviation_pct', decimal_places=2)
        ]
    }
)

# Example 2: Focus on specific dimensions
transformers_after_detection = [
    ValueFilter('platform', values=['desktop', 'mobile']),  # Categorical filtering
    ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER']),
    ColumnFormatter.percentage('deviation_pct')
]

# Example 3: Multi-tier alerting
# Critical anomalies (>50% deviation)
critical_transformers = [
    ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER']),
    ValueFilter('deviation_pct', min_value=50.0),  # Numeric filtering
    ColumnFormatter.percentage('deviation_pct')
]

# Warning anomalies (20-50% deviation)
warning_transformers = [
    ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER']),
    ValueFilter('deviation_pct', min_value=20.0, max_value=50.0),  # Numeric range
    ColumnFormatter.percentage('deviation_pct')
]
'''

print(customization_code)

print("\n" + "=" * 70)
print("This example shows the POWER of general-purpose transformers!")
print("Apply them at ANY stage of the pipeline for maximum flexibility.")
print("=" * 70)
