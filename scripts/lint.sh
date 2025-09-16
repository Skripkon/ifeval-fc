#!/bin/bash

# Script to run all linters
set -e

echo "🔍 Running code quality checks..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Run isort check
echo "📦 Checking import sorting with isort..."
isort IFEval_FC/ --check-only --profile black
echo "✅ isort check passed"

# Run black check
echo "🎨 Checking code formatting with black..."
black IFEval_FC/ --check --config pyproject.toml
echo "✅ black check passed"

# Run pylint
echo "🔍 Running pylint..." 
pylint IFEval_FC/ --rcfile=pyproject.toml
echo "✅ pylint check passed"

# Run mypy
echo "🔬 Running type checking with mypy..."
mypy IFEval_FC/ --config-file=pyproject.toml
echo "✅ mypy check passed"

echo "🎉 All code quality checks passed!"
