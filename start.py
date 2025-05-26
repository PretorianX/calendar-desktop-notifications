#!/usr/bin/env python3
"""
Start script for the Calendar Desktop Notifications application.
This script can be run directly with Python to start the application.
"""

import os
import sys
import subprocess
import shutil

def main():
    """Run the Calendar Desktop Notifications application."""
    print("Starting Calendar Desktop Notifications...")
    
    # Check if pipenv is installed
    pipenv_path = shutil.which('pipenv')
    if not pipenv_path:
        print("Error: Pipenv is not installed. Please run setup.sh first or install pipenv manually.")
        sys.exit(1)
    
    # Run the application using pipenv
    env = os.environ.copy()
    env["PIPENV_IGNORE_VIRTUALENVS"] = "1"
    
    try:
        subprocess.run([pipenv_path, "run", "start"], check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"Error starting the application: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
        sys.exit(0)

if __name__ == "__main__":
    main() 