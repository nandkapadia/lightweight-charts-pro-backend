# Quick Start Guide

Welcome to the Lightweight Charts Pro Backend! This guide will get you up and running in minutes.

## Installation

```bash
# Install the package
pip install lightweight-charts-pro-backend

# Or for development
pip install -e ".[dev,docs]"
```

## Basic Usage

### 1. Start the Server

```python
from lightweight_charts_pro_backend import create_app
import uvicorn

# Create the FastAPI application
app = create_app()

# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Run it:
```bash
python your_file.py
```

### 2. Load Chart Data

```python
import asyncio
from lightweight_charts_pro_backend import DatafeedService

async def load_data():
    # Create datafeed
    datafeed = DatafeedService()

    # Sample candlestick data
    data = [
        {"time": 1609459200, "open": 100, "high": 105, "low": 99, "close": 103},
        {"time": 1609545600, "open": 103, "high": 108, "low": 102, "close": 107},
    ]

    # Set series data
    await datafeed.set_series_data(
        chart_id="my_chart",
        pane_id=0,
        series_id="main",
        series_type="candlestick",
        data=data
    )

asyncio.run(load_data())
```

### 3. Access the API

```bash
# Health check
curl http://localhost:8000/health

# Get chart data
curl http://localhost:8000/api/charts/my_chart

# OpenAPI docs
open http://localhost:8000/docs
```

## Development

### Setting Up for Development

```bash
# Clone the repository
git clone https://github.com/nandkapadia/streamlit-lightweight-charts-pro.git
cd lightweight-charts-pro-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev,docs]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lightweight_charts_pro_backend --cov-report=html

# Run specific test file
pytest tests/test_api.py -v
```

### Code Formatting

Formatting runs automatically via pre-commit hooks, or manually:

```bash
# Run all formatters
./scripts/document_and_format.sh

# Or individually
isort lightweight_charts_pro_backend/
black lightweight_charts_pro_backend/
ruff check --fix lightweight_charts_pro_backend/
```

### Building Documentation

```bash
cd docs
make html
open _build/html/index.html

# Or with live reload
make livehtml  # Opens at http://127.0.0.1:8000
```

## Documentation

### Where to Find Documentation

- **API Reference**: `docs/_build/html/index.html` (after building)
- **GitHub Pages**: `https://<username>.github.io/<repository>/` (after deployment)
- **Contributing Guide**: `CONTRIBUTING.md`
- **Documentation Setup**: `DOCUMENTATION_SETUP.md`
- **Examples**: `docs/examples.rst`

### Documentation Standards

This project uses **Google-style docstrings** exclusively:

```python
def example_function(param1: str, param2: int = 0) -> bool:
    """Short description.

    Longer description with more context about what this function
    does and how it should be used.

    Args:
        param1: Description of param1.
        param2: Description of param2. Defaults to 0.

    Returns:
        bool: Description of return value.

    Raises:
        ValueError: When and why this is raised.

    Example:
        >>> result = example_function("test", 42)
        >>> print(result)
        True
    """
    pass
```

## CI/CD

### GitHub Actions

Two workflows are configured:

1. **CI/CD** (`.github/workflows/ci.yml`):
   - Runs on every push/PR
   - Tests on Python 3.10, 3.11, 3.12
   - Runs linters (isort, black, ruff)
   - Generates coverage reports

2. **Documentation** (`.github/workflows/docs.yml`):
   - Builds Sphinx documentation
   - Deploys to GitHub Pages (on main/master)
   - Uploads documentation artifacts

### Pre-commit Hooks

Automatically runs before each commit:
- isort (import organization)
- autoflake (unused import removal)
- black (code formatting)
- ruff (linting)
- File checks (trailing whitespace, etc.)
- Security checks (bandit)

## File Structure

```
lightweight-charts-pro-backend/
├── lightweight_charts_pro_backend/  # Main package
│   ├── __init__.py                  # Package exports
│   ├── app.py                       # FastAPI application factory
│   ├── api/                         # REST API endpoints
│   │   ├── __init__.py
│   │   └── charts.py                # Chart endpoints
│   ├── models/                      # Pydantic models
│   │   ├── __init__.py
│   │   └── charts.py                # Request/response models
│   ├── services/                    # Business logic
│   │   ├── __init__.py
│   │   └── datafeed.py              # Data management
│   └── websocket/                   # WebSocket handlers
│       ├── __init__.py
│       └── handlers.py              # WebSocket endpoints
├── tests/                           # Test suite
│   ├── conftest.py                  # Shared fixtures
│   ├── test_api.py                  # API tests
│   ├── test_datafeed_service.py     # Service tests
│   └── test_websocket.py            # WebSocket tests
├── docs/                            # Sphinx documentation
│   ├── conf.py                      # Sphinx config
│   ├── index.rst                    # Main page
│   ├── modules.rst                  # API reference
│   ├── examples.rst                 # Usage examples
│   └── README.md                    # Doc guide
├── scripts/                         # Utility scripts
│   └── document_and_format.sh       # Formatting script
├── .github/workflows/               # CI/CD
│   ├── ci.yml                       # Tests and linting
│   └── docs.yml                     # Documentation
├── .pre-commit-config.yaml          # Pre-commit hooks
├── pyproject.toml                   # Project config
├── CONTRIBUTING.md                  # Contribution guide
├── DOCUMENTATION_SETUP.md           # Doc setup guide
└── README.md                        # Project README
```

## Common Tasks

### Adding a New Feature

1. Create a branch: `git checkout -b feature/your-feature`
2. Write code with docstrings (Google style)
3. Add tests in `tests/`
4. Run tests: `pytest`
5. Format code: `./scripts/document_and_format.sh` (or commit, hooks run auto)
6. Build docs: `cd docs && make html`
7. Commit: `git commit -m "feat: your feature"`
8. Push and create PR

### Fixing a Bug

1. Create a branch: `git checkout -b fix/bug-description`
2. Write a failing test that reproduces the bug
3. Fix the bug
4. Ensure test passes
5. Follow steps 5-8 from "Adding a New Feature"

### Updating Documentation

1. Edit docstrings in Python files (Google style)
2. Or edit `.rst` files in `docs/`
3. Build and preview: `cd docs && make html`
4. Commit changes

## Configuration

### Environment Variables

```bash
# Server configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# CORS origins (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Custom Configuration

```python
from lightweight_charts_pro_backend import create_app

app = create_app(
    cors_origins=[
        "https://myapp.com",
        "http://localhost:3000"
    ],
    title="My Custom API",
    version="1.0.0"
)
```

## Troubleshooting

### Tests Failing

```bash
# Check if dependencies are installed
pip install -e ".[dev]"

# Run tests with verbose output
pytest -vv

# Check specific test
pytest tests/test_api.py::test_name -vv
```

### Documentation Build Errors

```bash
# Clean and rebuild
cd docs
make clean
make html

# Check for warnings
make html 2>&1 | grep WARNING
```

### Pre-commit Hooks Issues

```bash
# Update hooks
pre-commit autoupdate

# Run manually
pre-commit run --all-files

# Skip hooks (not recommended)
git commit --no-verify
```

## Getting Help

- **Issues**: https://github.com/nandkapadia/streamlit-lightweight-charts-pro/issues
- **Discussions**: Use GitHub Discussions
- **Documentation**: `docs/_build/html/index.html`
- **Contributing**: See `CONTRIBUTING.md`

## License

MIT License - see LICENSE file for details.
