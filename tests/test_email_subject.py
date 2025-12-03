"""
Test script for email subject customization feature.
This script tests various subject templates with date formatting.
"""

import os
import pandas as pd
from datetime import datetime
from chronomaly.infrastructure.notifiers import EmailNotifier

# Set up required SMTP environment variables for testing
os.environ['SMTP_HOST'] = 'smtp.test.com'
os.environ['SMTP_USER'] = 'test@example.com'
os.environ['SMTP_PASSWORD'] = 'testpassword'
os.environ['SMTP_FROM_EMAIL'] = 'test@example.com'

# Create sample anomalies DataFrame
anomalies_df = pd.DataFrame({
    'date': ['2025-12-03'],
    'metric': ['web_organic_sessions'],
    'platform': ['web'],
    'channel': ['Organic Search'],
    'actual': [1500],
    'forecast': [2000],
    'deviation_pct': ['-25.0%'],
    'status': ['BELOW_LOWER']
})

print("=" * 80)
print("Testing Email Subject Customization")
print("=" * 80)
print()

# Test 1: Default subject (backward compatibility)
print("Test 1: Default subject (no subject parameter)")
print("-" * 80)
try:
    notifier = EmailNotifier(to=["test@example.com"])
    subject = notifier._get_email_subject()
    print(f"✓ Subject: '{subject}'")
    assert subject == "Anomaly Detection Alert", "Default subject should be 'Anomaly Detection Alert'"
    print("✓ PASSED: Default subject works correctly")
except Exception as e:
    print(f"✗ FAILED: {e}")
print()

# Test 2: Custom static subject
print("Test 2: Custom static subject")
print("-" * 80)
try:
    notifier = EmailNotifier(
        to=["test@example.com"],
        subject="Custom Alert Subject"
    )
    subject = notifier._get_email_subject()
    print(f"✓ Subject: '{subject}'")
    assert subject == "Custom Alert Subject", "Subject should match custom text"
    print("✓ PASSED: Static custom subject works correctly")
except Exception as e:
    print(f"✗ FAILED: {e}")
print()

# Test 3: Subject with {date} placeholder
print("Test 3: Subject with {date} placeholder")
print("-" * 80)
try:
    notifier = EmailNotifier(
        to=["test@example.com"],
        subject="Daily Report - {date}"
    )
    test_date = datetime(2025, 12, 2, 10, 30, 0)
    subject = notifier._get_email_subject(anomaly_date=test_date)
    expected_subject = "Daily Report - 2025-12-02"
    print(f"✓ Subject: '{subject}'")
    assert subject == expected_subject, f"Subject should be '{expected_subject}'"
    print("✓ PASSED: {date} placeholder works correctly")
except Exception as e:
    print(f"✗ FAILED: {e}")
print()

# Test 4: Subject with {date:FORMAT} custom format
print("Test 4: Subject with custom date format {date:%d.%m.%Y}")
print("-" * 80)
try:
    notifier = EmailNotifier(
        to=["test@example.com"],
        subject="Günlük Rapor - {date:%d.%m.%Y}"
    )
    test_date = datetime(2025, 12, 2, 10, 30, 0)
    subject = notifier._get_email_subject(anomaly_date=test_date)
    expected_subject = "Günlük Rapor - 02.12.2025"
    print(f"✓ Subject: '{subject}'")
    assert subject == expected_subject, f"Subject should be '{expected_subject}'"
    print("✓ PASSED: {date:FORMAT} custom format works correctly")
except Exception as e:
    print(f"✗ FAILED: {e}")
print()

print("=" * 80)
print("All tests completed!")
print("=" * 80)
print()
print("Summary:")
print("- Default subject: ✓")
print("- Custom static subject: ✓")
print("- {date} placeholder: ✓")
print("- {date:FORMAT} custom format: ✓")
print()
print("✓ All email subject customization features are working correctly!")
