#!/bin/bash
# Start the calendar desktop notifications application

# Check if pipenv is installed
if ! command -v pipenv &> /dev/null; then
    echo "Pipenv is not installed. Please run ./setup.sh first."
    exit 1
fi

# Run the application
echo "Starting Calendar Desktop Notifications..."
PIPENV_IGNORE_VIRTUALENVS=1 pipenv run start 