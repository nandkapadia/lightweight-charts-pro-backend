.PHONY: help install install-dev test lint format type-check clean build publish run

help:
	@echo "Available commands:"
	@echo "  make install      - Install package"
	@echo "  make install-dev  - Install package with dev dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code with black and isort"
	@echo "  make type-check   - Run type checking with mypy"
	@echo "  make clean        - Remove build artifacts"
	@echo "  make build        - Build distribution packages"
	@echo "  make publish      - Publish to PyPI"
	@echo "  make run          - Run development server"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --tb=short

lint:
	ruff check lightweight_charts_pro_backend
	pylint lightweight_charts_pro_backend

format:
	black lightweight_charts_pro_backend tests
	isort lightweight_charts_pro_backend tests

type-check:
	mypy lightweight_charts_pro_backend --ignore-missing-imports

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

build: clean
	python -m build

publish: build
	python -m twine upload dist/*

publish-test: build
	python -m twine upload --repository testpypi dist/*

run:
	uvicorn lightweight_charts_pro_backend.app:app --reload --host 0.0.0.0 --port 8000
