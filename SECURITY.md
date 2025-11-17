# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

The Chronomaly team takes security bugs seriously. We appreciate your efforts to responsibly disclose your findings and will make every effort to acknowledge your contributions.

### How to Report a Security Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing:

**sinan@sinancan.net**

Or open a private security advisory on GitHub:
https://github.com/sinancan34/chronomaly/security/advisories/new

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

### What to Include in Your Report

To help us better understand the nature and scope of the issue, please include as much of the following information as possible:

- **Type of issue** (e.g., SQL injection, cross-site scripting, code injection, etc.)
- **Full paths of source file(s)** related to the manifestation of the issue
- **Location of the affected source code** (tag/branch/commit or direct URL)
- **Step-by-step instructions** to reproduce the issue
- **Proof-of-concept or exploit code** (if possible)
- **Impact of the issue**, including how an attacker might exploit it
- **Any special configuration** required to reproduce the issue

### What to Expect

After you submit a report, you can expect:

1. **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 48 hours
2. **Initial Assessment**: We will send an initial assessment of the vulnerability within 5 business days
3. **Updates**: We will keep you informed of our progress
4. **Resolution**: Once the vulnerability is fixed, we will notify you and may ask you to verify the fix
5. **Disclosure**: We will coordinate with you on the disclosure timeline

### Preferred Languages

We prefer all communications to be in English.

## Security Best Practices for Users

When using Chronomaly, please follow these security best practices:

### 1. Credential Management

**Never hardcode credentials in your code:**

```python
# ❌ DON'T DO THIS
reader = BigQueryDataReader(
    service_account_file="path/to/key.json",
    project="my-project",
    query="SELECT * FROM table"
)
```

**Use environment variables or secure credential management:**

```python
# ✅ DO THIS
import os

reader = BigQueryDataReader(
    service_account_file=os.getenv("GCP_SERVICE_ACCOUNT_FILE"),
    project=os.getenv("GCP_PROJECT"),
    query="SELECT * FROM table"
)
```

### 2. SQL Injection Prevention

**Use parameterized queries when possible:**

```python
# ❌ DON'T: String concatenation
date = user_input
query = f"SELECT * FROM table WHERE date = '{date}'"  # Vulnerable!

# ✅ DO: Use parameterized queries or validate input
from datetime import datetime

def validate_date(date_string: str) -> str:
    """Validate and sanitize date input."""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return date_string
    except ValueError:
        raise ValueError("Invalid date format")

date = validate_date(user_input)
query = f"SELECT * FROM table WHERE date = '{date}'"
```

### 3. File Path Validation

**Validate file paths to prevent directory traversal:**

```python
import os
from pathlib import Path

def safe_path(base_dir: str, filename: str) -> str:
    """Ensure file path is within base directory."""
    base = Path(base_dir).resolve()
    file_path = (base / filename).resolve()

    if not str(file_path).startswith(str(base)):
        raise ValueError("Invalid file path")

    return str(file_path)

# ✅ Use validated paths
file_path = safe_path("/data", user_provided_filename)
reader = CSVDataReader(file_path=file_path)
```

### 4. Dependency Security

**Keep dependencies up to date:**

```bash
# Check for security vulnerabilities
pip install safety
safety check

# Update dependencies regularly
pip install --upgrade -r requirements.txt
```

### 5. Data Validation

**Validate data before processing:**

```python
import pandas as pd

def validate_dataframe(df: pd.DataFrame) -> None:
    """Validate dataframe before processing."""
    if df.empty:
        raise ValueError("DataFrame is empty")

    if 'date' not in df.columns:
        raise ValueError("Missing required 'date' column")

    # Check for suspicious data sizes
    if len(df) > 1_000_000:
        raise ValueError("DataFrame too large")

# ✅ Validate before use
df = reader.load()
validate_dataframe(df)
```

### 6. Service Account Permissions

**Use minimal permissions for service accounts:**

- BigQuery: Grant only `bigquery.dataViewer` and `bigquery.jobUser` roles
- Storage: Grant only necessary read/write permissions
- Follow the principle of least privilege

### 7. Logging Security

**Don't log sensitive information:**

```python
import logging

# ❌ DON'T log credentials
logging.info(f"Connecting with key: {service_account_key}")

# ✅ DO log safely
logging.info("Connecting to BigQuery")
```

### 8. Network Security

**Use secure connections:**

- Always use HTTPS/TLS for API connections
- Verify SSL certificates
- Use VPCs and private endpoints when available

### 9. Code Review

- Review all code before deployment
- Use automated security scanning tools
- Follow secure coding guidelines

## Known Security Considerations

### Data Privacy

When working with sensitive data:

1. **Data Minimization**: Only load the data you need
2. **Encryption**: Ensure data is encrypted at rest and in transit
3. **Access Control**: Implement proper access controls
4. **Audit Logging**: Log access to sensitive data
5. **Data Retention**: Follow data retention policies

### Model Security

When using forecasting models:

1. **Input Validation**: Validate all input data
2. **Resource Limits**: Set limits to prevent resource exhaustion
3. **Model Provenance**: Use models from trusted sources
4. **Version Pinning**: Pin specific versions of dependencies

## Security Updates

Security updates will be released as soon as possible after a vulnerability is confirmed. Updates will be announced:

1. **GitHub Security Advisories**: Primary notification channel
2. **GitHub Releases**: Tagged with security labels
3. **Repository README**: Updated with security notices

## Disclosure Policy

When we receive a security bug report, we will:

1. Confirm the problem and determine affected versions
2. Audit code to find any similar problems
3. Prepare fixes for all supported versions
4. Release patches as soon as possible

We aim to disclose vulnerabilities in a coordinated manner:

- We prefer a 90-day disclosure timeline
- We will work with you to understand the impact
- We will credit you in the security advisory (unless you prefer to remain anonymous)

## Bug Bounty Program

We currently do not offer a paid bug bounty program. However, we deeply appreciate security researchers who responsibly disclose vulnerabilities and will:

- Publicly acknowledge your contribution (with your permission)
- List you in our security hall of fame
- Provide a detailed written thank you

## Security Hall of Fame

We would like to thank the following individuals for responsibly disclosing security issues:

- *No reports yet*

## Contact

For security concerns, please contact:

**Email**: sinan@sinancan.net
**GitHub Security Advisories**: https://github.com/sinancan34/chronomaly/security/advisories/new

For non-security issues, please use:

**GitHub Issues**: https://github.com/sinancan34/chronomaly/issues

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [Google Cloud Security Best Practices](https://cloud.google.com/security/best-practices)

---

**Last Updated**: 2025-11-17
