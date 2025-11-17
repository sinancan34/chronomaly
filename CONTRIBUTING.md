# Contributing to Chronomaly

Thank you for your interest in contributing to Chronomaly! We welcome contributions from the community and appreciate your efforts to improve this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Adding New Features](#adding-new-features)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

1. **Fork the repository** on GitHub: https://github.com/sinancan34/chronomaly
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/chronomaly.git
   cd chronomaly
   ```
3. **Add the upstream repository**:
   ```bash
   git remote add upstream https://github.com/sinancan34/chronomaly.git
   ```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- pip package manager
- git

### Installation

1. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   # Install core dependencies
   pip install -r requirements.txt

   # Install TimesFM
   pip install git+https://github.com/google-research/timesfm.git

   # Install development dependencies
   pip install -e ".[dev]"

   # Install all optional dependencies
   pip install -e ".[all]"
   ```

3. **Verify installation**:
   ```bash
   pytest
   ```

## How to Contribute

### Types of Contributions

We welcome many types of contributions:

- **Bug fixes**: Fix existing issues or bugs you've discovered
- **New features**: Add new data sources, forecasters, transformers, etc.
- **Documentation**: Improve README, docstrings, or add examples
- **Tests**: Increase test coverage or improve existing tests
- **Performance**: Optimize existing code
- **Refactoring**: Improve code quality and maintainability

### Contribution Workflow

1. **Check existing issues** to see if someone is already working on it
2. **Create or comment on an issue** to discuss your proposed changes
3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```
4. **Make your changes** following our coding standards
5. **Write or update tests** for your changes
6. **Run tests** to ensure everything passes
7. **Commit your changes** using conventional commits
8. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
9. **Open a Pull Request** on GitHub

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: Maximum 100 characters
- **Imports**: Group standard library, third-party, and local imports
- **Type hints**: Required for all function signatures
- **Docstrings**: Required for all public classes and functions

### Type Hints

Always use type hints for function parameters and return values:

```python
from typing import Optional, List
import pandas as pd

def process_data(
    df: pd.DataFrame,
    columns: List[str],
    threshold: Optional[float] = None
) -> pd.DataFrame:
    """Process the dataframe with given parameters.

    Args:
        df: Input dataframe
        columns: List of column names to process
        threshold: Optional threshold value

    Returns:
        Processed dataframe
    """
    # Implementation
    pass
```

### Docstrings

Use Google-style docstrings:

```python
class MyClass:
    """Brief description of the class.

    Longer description if needed. Explain the purpose,
    usage, and any important notes.

    Args:
        param1: Description of param1
        param2: Description of param2

    Attributes:
        attribute1: Description of attribute1
        attribute2: Description of attribute2

    Example:
        >>> obj = MyClass(param1="value1", param2="value2")
        >>> result = obj.method()
    """
    pass
```

### Code Formatting

We use **Black** for code formatting and **flake8** for linting:

```bash
# Format code
black chronomaly/

# Check formatting
black --check chronomaly/

# Run linter
flake8 chronomaly/
```

### Import Organization

Organize imports in this order:

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import os
from typing import Optional, List

# Third-party
import pandas as pd
import numpy as np

# Local
from chronomaly.infrastructure.data.readers.base import DataReader
from chronomaly.shared.types import TimeSeriesData
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=chronomaly

# Run specific test file
pytest tests/test_forecasters.py

# Run specific test
pytest tests/test_forecasters.py::test_timesfm_forecaster
```

### Writing Tests

- Place tests in the `tests/` directory
- Mirror the structure of the `chronomaly/` directory
- Name test files with `test_` prefix
- Name test functions with `test_` prefix

Example test structure:

```python
import pytest
import pandas as pd
from chronomaly.infrastructure.forecasters import TimesFMForecaster

class TestTimesFMForecaster:
    """Tests for TimesFMForecaster class."""

    @pytest.fixture
    def sample_data(self) -> pd.DataFrame:
        """Create sample time series data."""
        return pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=100),
            'value': range(100)
        })

    def test_forecast_basic(self, sample_data):
        """Test basic forecasting functionality."""
        forecaster = TimesFMForecaster(frequency='D')
        result = forecaster.forecast(sample_data, horizon=7)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 7
```

### Test Coverage

- Aim for at least 80% code coverage
- Write tests for:
  - Happy path scenarios
  - Edge cases
  - Error conditions
  - Integration between components

## Submitting Changes

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements

**Examples:**

```bash
feat(readers): Add PostgreSQL data reader

Implement PostgreSQL data reader with connection pooling
and parameterized queries for security.

Closes #123
```

```bash
fix(forecaster): Handle empty dataframes correctly

Previously, empty dataframes caused a crash. Now returns
an empty forecast result with appropriate warning.

Fixes #456
```

### Pull Request Process

1. **Update documentation** if you've added or changed functionality
2. **Add tests** for new features or bug fixes
3. **Ensure all tests pass** locally before submitting
4. **Update the README.md** if needed
5. **Fill out the PR template** with all required information
6. **Link related issues** using keywords (Fixes #123, Closes #456)

### Pull Request Template

When opening a PR, include:

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have added tests that prove my fix/feature works
- [ ] All tests pass locally
- [ ] I have updated the documentation
- [ ] I have added type hints
- [ ] I have added docstrings
```

## Adding New Features

### Adding a New Data Source

#### Reader Example

```python
from chronomaly.infrastructure.data.readers.base import DataReader
import pandas as pd

class PostgreSQLDataReader(DataReader):
    """Read data from PostgreSQL database.

    Args:
        connection_string: PostgreSQL connection string
        query: SQL query to execute
        date_column: Name of the date column

    Example:
        >>> reader = PostgreSQLDataReader(
        ...     connection_string="postgresql://user:pass@localhost/db",
        ...     query="SELECT * FROM time_series",
        ...     date_column="date"
        ... )
        >>> df = reader.load()
    """

    def __init__(
        self,
        connection_string: str,
        query: str,
        date_column: str = "date"
    ):
        super().__init__(date_column=date_column)
        self.connection_string = connection_string
        self.query = query

    def load(self) -> pd.DataFrame:
        """Load data from PostgreSQL.

        Returns:
            DataFrame with loaded data
        """
        # Implementation here
        pass
```

#### Writer Example

```python
from chronomaly.infrastructure.data.writers.base import DataWriter
import pandas as pd

class PostgreSQLDataWriter(DataWriter):
    """Write data to PostgreSQL database.

    Args:
        connection_string: PostgreSQL connection string
        table_name: Target table name
        if_exists: How to behave if table exists ('fail', 'replace', 'append')

    Example:
        >>> writer = PostgreSQLDataWriter(
        ...     connection_string="postgresql://user:pass@localhost/db",
        ...     table_name="forecasts",
        ...     if_exists="append"
        ... )
        >>> writer.write(forecast_df)
    """

    def __init__(
        self,
        connection_string: str,
        table_name: str,
        if_exists: str = "append"
    ):
        self.connection_string = connection_string
        self.table_name = table_name
        self.if_exists = if_exists

    def write(self, df: pd.DataFrame) -> None:
        """Write dataframe to PostgreSQL.

        Args:
            df: DataFrame to write
        """
        # Implementation here
        pass
```

### Adding a New Transformer

```python
from chronomaly.infrastructure.transformers.base import Transformer
import pandas as pd

class MyCustomTransformer(Transformer):
    """Custom data transformation.

    Args:
        param1: Description of parameter

    Example:
        >>> transformer = MyCustomTransformer(param1="value")
        >>> transformed_df = transformer.transform(df)
    """

    def __init__(self, param1: str):
        self.param1 = param1

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply transformation to dataframe.

        Args:
            df: Input dataframe

        Returns:
            Transformed dataframe
        """
        # Implementation here
        pass
```

### Adding Tests for New Features

```python
# tests/infrastructure/transformers/test_my_custom_transformer.py

import pytest
import pandas as pd
from chronomaly.infrastructure.transformers import MyCustomTransformer

class TestMyCustomTransformer:
    """Tests for MyCustomTransformer."""

    @pytest.fixture
    def sample_data(self) -> pd.DataFrame:
        """Create sample data for testing."""
        return pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'value': range(10)
        })

    def test_transform_basic(self, sample_data):
        """Test basic transformation."""
        transformer = MyCustomTransformer(param1="test")
        result = transformer.transform(sample_data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_data)

    def test_transform_empty_dataframe(self):
        """Test transformation with empty dataframe."""
        transformer = MyCustomTransformer(param1="test")
        empty_df = pd.DataFrame()
        result = transformer.transform(empty_df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
```

## Reporting Issues

### Bug Reports

When reporting a bug, please include:

1. **Clear title** describing the issue
2. **Description** of what happened vs. what you expected
3. **Steps to reproduce** the issue
4. **Code sample** or test case
5. **Environment information**:
   - Python version
   - Operating system
   - Package versions
6. **Error messages** or stack traces

Example:

```markdown
## Bug: TimesFMForecaster fails with multi-index dataframe

### Description
When using a dataframe with multi-index columns, TimesFMForecaster
raises a KeyError.

### Steps to Reproduce
1. Create multi-index dataframe
2. Pass to TimesFMForecaster.forecast()
3. Error occurs

### Code Sample
```python
import pandas as pd
from chronomaly.infrastructure.forecasters import TimesFMForecaster

df = pd.DataFrame(...) # multi-index setup
forecaster = TimesFMForecaster(frequency='D')
forecaster.forecast(df, horizon=7)  # Fails here
```

### Environment
- Python: 3.11.5
- OS: macOS 14.0
- chronomaly: 0.1.0

### Error Message
```
KeyError: 'date'
...
```
```

### Feature Requests

When requesting a feature, please include:

1. **Clear description** of the feature
2. **Use case** explaining why this feature is needed
3. **Example** of how it would be used
4. **Alternatives** you've considered

## Questions?

If you have questions about contributing:

1. Check existing [GitHub Discussions](https://github.com/sinancan34/chronomaly/discussions)
2. Open a new discussion
3. Review the [README](README.md) for project overview

Thank you for contributing to Chronomaly!
