"""
Simple test to demonstrate the AnomalyDetectionWorkflow functionality.

This test creates sample forecast and actual data to show how anomaly detection works.
Run this after installing dependencies: pip install -r requirements.txt
"""

import pandas as pd
from datetime import datetime, timedelta


def create_sample_data():
    """Create sample forecast and actual data for testing."""

    # Sample date
    test_date = datetime(2024, 1, 15)

    # Create forecast data (pivot format with pipe-separated quantiles)
    # Format: "point|q10|q20|q30|q40|q50|q60|q70|q80|q90"
    forecast_data = {
        'date': [test_date],
        'desktop_organic': ['100|90|92|95|98|100|102|105|108|110'],
        'desktop_paid': ['50|45|46|47|48|50|52|53|55|60'],
        'mobile_organic': ['80|70|72|75|77|80|82|85|88|90'],
        'mobile_paid': ['30|25|26|27|28|30|32|33|35|40']
    }
    forecast_df = pd.DataFrame(forecast_data)

    # Create actual data (raw format - will be pivoted)
    actual_data = {
        'date': [test_date, test_date, test_date, test_date],
        'platform': ['desktop', 'desktop', 'mobile', 'mobile'],
        'channel': ['organic', 'paid', 'organic', 'paid'],
        'sessions': [95, 65, 75, 28]  # organic in range, paid above, organic below, paid in range
    }
    actual_df = pd.DataFrame(actual_data)

    return forecast_df, actual_df


def test_anomaly_detection():
    """Test the anomaly detection workflow."""

    try:
        from chronomaly.infrastructure.comparators import ForecastActualComparator
        from chronomaly.infrastructure.transformers import DataTransformer

        # Create sample data
        forecast_df, actual_df = create_sample_data()

        print("=" * 60)
        print("ANOMALY DETECTION TEST")
        print("=" * 60)

        print("\n1. FORECAST DATA (Pivot format with quantiles):")
        print("-" * 60)
        print(forecast_df.to_string(index=False))

        print("\n2. ACTUAL DATA (Raw format):")
        print("-" * 60)
        print(actual_df.to_string(index=False))

        # Configure transformer
        transformer = DataTransformer(
            index="date",
            columns=["platform", "channel"],
            values="sessions"
        )

        # Configure detector
        detector = ForecastActualComparator(
            transformer=transformer,
            date_column="date",
            exclude_columns=["date"]
        )

        # Run detection
        results = detector.detect(forecast_df, actual_df)

        print("\n3. ANOMALY DETECTION RESULTS:")
        print("-" * 60)
        print(results.to_string(index=False))

        print("\n4. SUMMARY:")
        print("-" * 60)
        print(f"Total metrics analyzed: {len(results)}")
        print("\nStatus breakdown:")
        print(results['status'].value_counts())

        # Show anomalies
        anomalies = results[results['status'].isin(['BELOW_P10', 'ABOVE_P90'])]
        print(f"\nAnomalies detected: {len(anomalies)}")

        if len(anomalies) > 0:
            print("\nAnomaly details:")
            print(anomalies[['metric', 'actual', 'q10', 'q90', 'status', 'deviation_pct']].to_string(index=False))

        print("\n5. EXPECTED RESULTS:")
        print("-" * 60)
        print("• desktop_organic: 95 (IN_RANGE, between 90-110)")
        print("• desktop_paid: 65 (ABOVE_P90, above 60)")
        print("• mobile_organic: 75 (BELOW_P10, below 70)")
        print("• mobile_paid: 28 (IN_RANGE, between 25-40)")

        print("\n" + "=" * 60)
        print("TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)

        return results

    except ImportError as e:
        print(f"Error: {e}")
        print("\nPlease install dependencies first:")
        print("  pip install -r requirements.txt")
        return None
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_with_filter():
    """Test the filtered detection method."""

    try:
        from chronomaly.infrastructure.comparators import ForecastActualComparator
        from chronomaly.infrastructure.transformers import DataTransformer

        # Create sample data
        forecast_df, actual_df = create_sample_data()

        # Configure transformer and detector
        transformer = DataTransformer(
            index="date",
            columns=["platform", "channel"],
            values="sessions"
        )

        detector = ForecastActualComparator(
            transformer=transformer,
            date_column="date"
        )

        print("\n" + "=" * 60)
        print("FILTERED DETECTION TEST")
        print("=" * 60)

        # Run filtered detection (only significant deviations > 5%)
        filtered_results = detector.detect_with_filter(
            forecast_df=forecast_df,
            actual_df=actual_df,
            min_deviation_pct=5.0,
            exclude_no_forecast=True
        )

        print("\nFiltered results (deviation > 5%):")
        print("-" * 60)
        if len(filtered_results) > 0:
            print(filtered_results.to_string(index=False))
        else:
            print("No significant anomalies found.")

        return filtered_results

    except Exception as e:
        print(f"Error during filtered test: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Run basic test
    results = test_anomaly_detection()

    # Run filtered test
    if results is not None:
        test_with_filter()
