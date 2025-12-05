# Contributing to Lightweight Charts Pro Backend

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip or poetry
- git

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/nandkapadia/streamlit-lightweight-charts-pro.git
   cd lightweight-charts-pro-backend
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**:
   ```bash
   pip install -e ".[dev,docs]"
   ```

4. **Install pre-commit hooks**:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Code Style and Standards

### Python Code Standards

We follow these principles:

1. **Explicit over Implicit**: Production-ready code with clear intent
2. **Type Hints**: All functions should have type annotations
3. **Docstrings**: Google-style docstrings for all public APIs
4. **Line Length**: Maximum 100 characters
5. **Testing**: All code should have corresponding tests

### Documentation Standards

#### Google-Style Docstrings

All docstrings must follow Google style:

```python
def function_name(param1: str, param2: int = 0) -> bool:
    """Short one-line description.

    Longer description explaining the function's purpose, behavior,
    and any important implementation details.

    Args:
        param1: Description of param1.
        param2: Description of param2. Defaults to 0.

    Returns:
        bool: Description of return value.

    Raises:
        ValueError: When and why this is raised.

    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
        True
    """
    pass
```

#### Inline Comments

Add clear inline comments explaining:
- Why certain decisions were made (not just what the code does)
- Complex logic or algorithms
- Workarounds or non-obvious solutions
- Trading-specific considerations (avoid lookahead bias, etc.)

Example:

```python
# Calculate returns using log differences to maintain numerical stability
# for long time series and to make returns additive
returns = np.log(prices / prices.shift(1))
```

### Import Organization

Imports must be organized in three sections with blank lines between:

```python
# Standard Imports
import asyncio
import logging
from typing import Optional

# Third Party Imports
from fastapi import FastAPI
import pandas as pd

# Local Imports
from lightweight_charts_pro_backend.models import ChartData
from lightweight_charts_pro_backend.services import DatafeedService
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes

Write your code following the style guidelines above.

### 3. Add Tests

All new functionality must include tests:

```bash
# Create test file in tests/
tests/test_your_feature.py
```

Example test:

```python
"""Tests for your feature.

This module tests the functionality of X, Y, and Z.
"""

import pytest
from lightweight_charts_pro_backend import your_module


class TestYourFeature:
    """Test suite for YourFeature class."""

    def test_basic_functionality(self):
        """Test basic functionality works as expected."""
        # Arrange
        input_data = "test"

        # Act
        result = your_module.process(input_data)

        # Assert
        assert result == expected_value

    async def test_async_functionality(self):
        """Test asynchronous functionality."""
        result = await your_module.async_process()
        assert result is not None
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lightweight_charts_pro_backend --cov-report=html

# Run specific test file
pytest tests/test_your_feature.py

# Run specific test
pytest tests/test_your_feature.py::TestYourFeature::test_basic_functionality
```

### 5. Format Code

The pre-commit hooks will automatically format your code, but you can also run manually:

```bash
# Run all formatters
isort lightweight_charts_pro_backend tests
autoflake --in-place --remove-all-unused-imports -r lightweight_charts_pro_backend tests
black --line-length 100 lightweight_charts_pro_backend tests
ruff check --fix lightweight_charts_pro_backend tests
```

Or use the convenience script:

```bash
./scripts/document_and_format.sh
```

### 6. Update Documentation

If you added new functionality:

1. **Update docstrings** in your code (Google style)
2. **Add examples** to `docs/examples.rst` if applicable
3. **Build and check documentation**:
   ```bash
   cd docs
   make clean
   make html
   # Open docs/_build/html/index.html to preview
   ```

### 7. Commit Changes

```bash
git add .
git commit -m "feat: add new feature X"
```

Commit message format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

### 8. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Review Process

1. **Automated Checks**: CI/CD runs tests and linters
2. **Documentation Check**: Documentation builds successfully
3. **Code Review**: Maintainer reviews code
4. **Feedback**: Address any feedback or requested changes
5. **Merge**: Once approved, code is merged

## Pre-commit Hooks

Pre-commit hooks automatically run before each commit:

- **isort**: Organizes imports
- **autoflake**: Removes unused imports
- **black**: Formats code
- **ruff**: Lints code
- **trailing-whitespace**: Removes trailing whitespace
- **end-of-file-fixer**: Ensures files end with newline
- **check-yaml/json/toml**: Validates config files
- **bandit**: Security checks

To skip hooks (not recommended):
```bash
git commit --no-verify -m "message"
```

## Testing Guidelines

### Test Organization

```
tests/
├── conftest.py          # Shared fixtures
├── test_api.py          # API endpoint tests
├── test_datafeed_service.py  # Service layer tests
├── test_websocket.py    # WebSocket tests
└── __init__.py
```

### Writing Good Tests

1. **Use descriptive names**: `test_create_chart_with_valid_data`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **One assertion per test** (when possible)
4. **Test edge cases**: Empty data, None values, large datasets
5. **Use fixtures**: Share setup code via pytest fixtures
6. **Mock external dependencies**: Don't rely on external services

### Test Coverage

Aim for >80% test coverage. Check coverage:

```bash
pytest --cov=lightweight_charts_pro_backend --cov-report=term
```

## Documentation Guidelines

### When to Update Documentation

- Adding new public API
- Changing function signatures
- Adding new features
- Fixing bugs that affect behavior
- Adding examples or clarifying existing docs

### Documentation Checklist

- [ ] Docstrings follow Google style
- [ ] All parameters documented
- [ ] Return values documented
- [ ] Exceptions documented
- [ ] Examples provided for complex functions
- [ ] Sphinx documentation builds without warnings
- [ ] New modules added to `docs/modules.rst`

## Trading Code Guidelines

When working with trading/quantitative code:

### Avoid Lookahead Bias

```python
# BAD: Using future data
signal = data['close'] > data['close'].shift(-1)  # Looks ahead!

# GOOD: Only use past data
signal = data['close'] > data['close'].shift(1)  # Looks back
```

### Be Explicit About Assumptions

```python
def calculate_returns(prices: pd.Series, include_fees: bool = False) -> pd.Series:
    """Calculate returns from price series.

    Args:
        prices: Time series of prices.
        include_fees: Whether to subtract trading fees. Defaults to False,
            which assumes zero fees. In production, set to True and specify
            fee structure explicitly.

    Returns:
        pd.Series: Log returns.

    Note:
        Assumes no slippage, dividends, or stock splits. For production
        use, these factors should be accounted for separately.
    """
    returns = np.log(prices / prices.shift(1))
    if include_fees:
        # Subtract 0.1% fee per trade (round-trip)
        returns -= 0.001
    return returns
```

### Document Data Requirements

```python
def process_ohlc_data(data: pd.DataFrame) -> pd.DataFrame:
    """Process OHLC candlestick data.

    Args:
        data: DataFrame with columns ['time', 'open', 'high', 'low', 'close'].
            - 'time': Unix timestamp (int) or datetime
            - 'open', 'high', 'low', 'close': Float prices
            - Data must be sorted by time ascending
            - No missing values allowed

    Returns:
        pd.DataFrame: Processed data with same structure.

    Raises:
        ValueError: If required columns are missing or data is not sorted.
    """
    # Validation logic here
    pass
```

## Getting Help

- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check `docs/` directory

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
