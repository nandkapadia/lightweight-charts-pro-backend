#!/bin/bash
# Automated documentation formatting script
# This script runs all formatters in the correct order as specified

set -e  # Exit on error

echo "Running code formatters..."

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Find all Python files in the package
PYTHON_FILES=$(find lightweight_charts_pro_backend -name "*.py" -type f)

for file in $PYTHON_FILES; do
    echo "Processing $file..."

    # 1. Run isort with float-to-top
    python -m isort --float-to-top "$file"

    # 2. Run autoflake to remove unused imports
    python -m autoflake --in-place --remove-all-unused-imports "$file"

    # 3. Run black with line length 100 and string processing
    python -m black --line-length 100 --enable-unstable-feature=string_processing --preview "$file"

    # 4. Run ruff with --fix
    python -m ruff check --fix "$file" || true  # Continue even if ruff finds issues
done

echo "All files formatted successfully!"
