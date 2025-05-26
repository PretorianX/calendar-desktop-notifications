@echo off
REM Start the calendar desktop notifications application

REM Check if pipenv is installed
where pipenv >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Pipenv is not installed. Please run setup.sh first using Git Bash or install pipenv manually.
    exit /b 1
)

REM Run the application
echo Starting Calendar Desktop Notifications...
set PIPENV_IGNORE_VIRTUALENVS=1
pipenv run start 