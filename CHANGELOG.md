# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup
- Project structure and dependencies
- README with features and installation instructions
- Configuration management system with YAML support
- CalDAV client for calendar synchronization
- Calendar event model with URL detection
- Desktop notification system with sound support
- System tray integration for all platforms
- Settings UI dialog with PyQt6
- Automatic URL opening for meeting links
- Timezone and recurring event support
- Unit tests for core components
- Test connection button for CalDAV server validation
- Cross-platform start scripts (shell, batch, Python)
- Enhanced .gitignore file with pipenv-specific patterns
- feat(sync): configurable sync period to adjust how many hours of upcoming events to fetch
- feat(notifications): configurable notification times via comma-delimited input
- feat(logging): detailed debug logging for notification timing and sound playback
- feat(notifications): separate per-minute notification check to prevent missing notification windows
- feat(ui): display time until next meeting in tray icon, showing "1h+" if more than 60 minutes away
- feat(ui): enhanced tray icon with larger minutes display and color-coding (green > 10min, yellow 5-10min, red < 5min)
- chore(production): comprehensive linting setup with flake8, black, mypy, isort
- chore(production): pre-commit hooks for automated code quality checks
- chore(production): CI/CD pipelines with GitHub Actions for testing and releases
- chore(production): automated testing with pytest and coverage reporting
- chore(production): PyInstaller configuration for building executables
- docs(production): comprehensive user guide with setup and usage instructions
- docs(production): developer guide with architecture and contribution guidelines
- docs(production): updated README with badges and comprehensive information
- chore(production): MIT license file
- chore(production): version management with _version.py
- chore(production): requirements.txt and requirements-dev.txt generation
- chore(production): production readiness checklist
- Type stub dependencies for better type checking
- Comprehensive linting configuration in setup.cfg

### Changed
- Migrated from venv to pipenv for dependency management
- Updated dependency specifications to use version ranges
- Added pipenv scripts for easier execution
- Fixed Python module import structure to allow proper execution
- Improved package structure with __main__.py for module execution 
- fix(logging): changed default logging level to DEBUG for better troubleshooting
- fix(notifications): tightened notification windows to 0.4 minutes for more precise timing
- fix(notifications): updated to use only WAV sound files for better compatibility
- refactor(code): applied black formatting to entire codebase
- refactor(imports): organized imports with isort
- refactor(types): added type hints to ConfigManager
- Test coverage improved from 44% to 64%
- Black formatter configuration set to 88 character line length

### Fixed
- fix(calendar_sync): revert to using calendar.date_search method for better compatibility
- feat(calendar_sync): add debug logging to identify URL issues in caldav_client
- fix(calendar_sync): prevent authorization errors by handling URL trailing slash inconsistencies
- fix(calendar_sync): improved calendar event filtering with date_search method and additional logging
- fix(notifications): improved sound file detection with better error handling
- fix(notifications): added dedicated notification check thread running every minute to prevent missing notification windows due to sync timing
- fix(notifications): replaced problematic plyer notifications with native AppleScript for reliable macOS notifications
- fix(tray_app): fixed "Force Sync" menu item not working in system tray by improving callback handling
- fix(notifications): increased notification window from 0.4 to 0.5 minutes to avoid missing notifications
- fix(notifications): improved notification checks to run every 20 seconds instead of every minute
- fix(notifications): process recurring events correctly even if original start time is in the past
- fix(notifications): properly adjust recurring event times to today's occurrence for accurate notification timing
- fix(notifications): use local timezone instead of UTC when calculating today's occurrence for recurring events
- fix(ui): update tray icon to correctly display time for recurring events
- fix(ui): ensure dialogs appear in foreground when opened from system tray icon on macOS
- fix(notifications): check for tomorrow's occurrences of recurring events when today's occurrence has passed
- fix(tests): fixed pytest module import issues with pytest.ini configuration
- Fixed infinite loop in `test_notification_thread_runs_independently` test by properly mocking Qt components
- Fixed hanging issue in `test_cursor_reset_on_exception` test by mocking QMessageBox
- Fixed 5 failing SettingsDialog tests by correcting import paths and test setup
- Fixed datetime mocking issue in `test_sync_calendar_uses_configured_sync_hours` by properly mocking datetime.datetime class
- All linting issues resolved across the codebase
- CalDAV client now uses `search` method instead of deprecated `date_search`
- Test suite stability improvements - fixed hanging and infinite running tests
- Improved datetime mocking in tests for recurring event handling

## [0.2.0] - 2025-01-XX
### Added