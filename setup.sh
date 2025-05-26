#!/bin/bash
# setup.sh - Install dependencies and set up the project

# Check if pipenv is installed
if ! command -v pipenv &> /dev/null; then
    echo "Pipenv is not installed. Installing it now..."
    pip install pipenv
fi

# Install dependencies
echo "Installing dependencies..."
pipenv install

# Install dev dependencies
echo "Installing development dependencies..."
pipenv install --dev

echo "Setup complete. You can now run the application with:"
echo "pipenv run python src/main.py"
echo ""
echo "To run tests:"
echo "pipenv run pytest" 