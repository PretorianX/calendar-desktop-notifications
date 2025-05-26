# Developer Guide

## Development Setup

### Prerequisites

- Python 3.11 or later
- pipenv
- Git

### Environment Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourname/calendar-desktop-notifications.git
   cd calendar-desktop-notifications
   ```

2. Install dependencies:
   ```bash
   pipenv install --dev
   ```

3. Activate the virtual environment:
   ```bash
   pipenv shell
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Project Structure

```
calendar-desktop-notifications/
├── src/
│   ├── main.py              # Application entry point
│   ├── config/              # Configuration management
│   ├── calendar_sync/       # CalDAV synchronization
│   ├── gui/                 # User interface components
│   └── notification/        # Notification system
├── tests/                   # Test suite
├── docs/                    # Documentation
├── sounds/                  # Notification sounds
└── .github/workflows/       # CI/CD pipelines
```

## Development Workflow

### Running the Application

```bash
pipenv run start
```

### Running Tests

```bash
# Run all tests
pipenv run test

# Run with coverage
pipenv run test-cov

# Run specific test file
pipenv run pytest tests/config/test_config_manager.py
```

### Code Quality

```bash
# Format code
pipenv run format

# Check formatting
pipenv run format-check

# Sort imports
pipenv run isort

# Run linting
pipenv run lint

# Type checking
pipenv run mypy

# Security scan
pipenv run security
```

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality. They run automatically on `git commit`.

To run manually:
```bash
pre-commit run --all-files
```

## Architecture Overview

### Components

1. **ConfigManager**: Handles application configuration
   - YAML-based configuration
   - User preferences storage
   - Default settings management

2. **CalDAVClient**: Manages calendar synchronization
   - Connects to CalDAV servers
   - Fetches and parses events
   - Handles recurring events

3. **NotificationManager**: Handles desktop notifications
   - Platform-specific notification systems
   - Sound playback
   - URL opening

4. **TrayApp**: System tray application
   - PyQt6-based UI
   - Settings dialog
   - Event loop management

### Key Design Decisions

- **Threading**: Separate threads for sync and notifications to prevent blocking
- **Platform Support**: Abstraction layers for cross-platform compatibility
- **Configuration**: YAML format for human-readable settings
- **Logging**: Structured logging with rotating file handlers

## Adding Features

### Example: Adding a New Notification Type

1. Update the configuration schema in `ConfigManager.DEFAULT_CONFIG`
2. Add notification logic in `NotificationManager`
3. Update the settings UI in `SettingsDialog`
4. Add tests for the new feature
5. Update documentation

## Testing Strategy

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Aim for >80% coverage

### Integration Tests
- Test component interactions
- Use test fixtures for CalDAV servers
- Verify end-to-end workflows

### Platform Testing
- Test on Windows, macOS, and Linux
- Verify platform-specific features
- Check installer functionality

## Release Process

1. Update version in `src/_version.py`
2. Update CHANGELOG.md
3. Create a git tag: `git tag v0.1.0`
4. Push tag: `git push origin v0.1.0`
5. GitHub Actions will build and create release

## Debugging

### Enable Debug Logging

Set logging level in `src/gui/tray_app.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

1. **Import Errors**: Ensure virtual environment is activated
2. **Platform-specific Issues**: Check platform detection in code
3. **CalDAV Issues**: Use debug logging to inspect requests

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Ensure all tests pass
5. Submit a pull request

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all functions/classes
- Keep functions small and focused

### Commit Messages

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Testing
- `refactor:` Code refactoring
- `chore:` Maintenance 