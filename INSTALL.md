# Quick Installation Guide

## Prerequisites

- Python 3.11 or higher
- Git

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone https://github.com/insightlytics/chronomaly.git
cd chronomaly
```

### 2. Create Virtual Environment

**For Python 3.11 (Recommended):**
```bash
python3.11 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

**For Python 3.13:**
```bash
python3.13 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

### 3. Install the Package

**Option A: Basic Installation (without TimesFM)**
```bash
pip install -e .
```

**Option B: With BigQuery Support**
```bash
pip install -e ".[bigquery]"
```

**Option C: With TimesFM (Python 3.11 only)**
```bash
pip install -e ".[timesfm]"
```

**Option D: Full Installation (All Features)**
```bash
pip install -e ".[all]"
```

**For Python 3.13 with TimesFM:**
```bash
# First install TimesFM from GitHub
pip install git+https://github.com/google-research/timesfm.git

# Then install chronomaly
pip install -e ".[bigquery]"
```

### 4. Verify Installation

```bash
python -c "from forecast_library import ForecastPipeline; print('✓ Installation successful!')"
```

### 5. Run Examples

```bash
# Make sure you have sample data first
python examples/example_csv.py
```

## Troubleshooting

### Issue: ModuleNotFoundError

**Problem:**
```
ModuleNotFoundError: No module named 'forecast_library'
```

**Solution:**
```bash
# Make sure you're in the project root directory
cd /path/to/chronomaly

# Install in editable mode
pip install -e .
```

### Issue: TimesFM Installation Fails on Python 3.13

**Problem:**
```
ERROR: Could not find a version that satisfies the requirement timesfm
```

**Solution:**
Use Python 3.11 or install TimesFM from GitHub:
```bash
pip install git+https://github.com/google-research/timesfm.git
```

### Issue: Virtual Environment Not Activated

**Symptoms:**
- Package installs but import fails
- Wrong Python version

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Verify Python version
python --version
```

## Next Steps

1. Check out the [README.md](README.md) for full documentation
2. Review examples in the `examples/` directory
3. Read about the architecture and usage patterns

## Support

For issues and questions:
- GitHub Issues: https://github.com/insightlytics/chronomaly/issues
- Documentation: See README.md
