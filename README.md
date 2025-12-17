# Calendar Desktop Notifications

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A desktop application that syncs with CalDAV calendars and provides desktop notifications for upcoming events.

## Features

- 🔔 **Smart Notifications**: Get alerts 1, 5, and 10 minutes before meetings
- 🔄 **Auto-sync**: Continuously syncs with your CalDAV server
- 🌐 **URL Auto-open**: Automatically opens meeting URLs in your browser
- 🔊 **Sound Alerts**: Customizable notification sounds
- 📅 **Timezone Support**: Handles events across different time zones
- 🔁 **Recurring Events**: Full support for recurring calendar events
- ⚙️ **Configurable**: Adjust sync intervals, notification times, and more

## Installation

### Pre-built Executables (Recommended)

Download the latest release for your platform from the [releases page](https://github.com/yourname/calendar-desktop-notifications/releases).

### From Source

#### Prerequisites
- Python 3.11 or later
- pipenv

#### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourname/calendar-desktop-notifications.git
   cd calendar-desktop-notifications
   ```

2. Install dependencies:
   ```bash
   ./setup.sh
   ```
   
   Or manually:
   ```bash
   pipenv install
   pipenv install --dev  # for development
   ```

3. Run the application:
   ```bash
   pipenv run start
   ```

## Quick Start

1. Launch the application - it will appear in your system tray
2. Right-click the tray icon and select "Settings"
3. Enter your CalDAV server details
4. Click "Test Connection" to verify
5. Save your settings and enjoy automatic meeting notifications!

## Configuration

On macOS, the application stores its configuration in:
- **macOS**: `~/Library/Application Support/calendar-desktop-notifications/`

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `caldav.url` | CalDAV server URL | - |
| `caldav.username` | Your username | - |
| `caldav.password` | Your password (stored securely) | - |
| `sync.interval_minutes` | How often to sync | 5 |
| `sync.sync_hours` | Hours ahead to sync events | 24 |
| `notifications.intervals_minutes` | When to notify (comma-separated) | 1,5,10 |
| `notifications.sound_enabled` | Enable notification sounds | true |
| `auto_open_urls` | Auto-open meeting URLs | true |

## Development

See [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for detailed development instructions.

### Quick Development Setup

```bash
# Install dev dependencies
pipenv install --dev

# Run tests
pipenv run test

# Run with coverage
pipenv run test-cov

# Format code
pipenv run format

# Run linting
pipenv run lint
```

## Documentation

- [User Guide](docs/USER_GUIDE.md) - Detailed usage instructions
- [Developer Guide](docs/DEVELOPER_GUIDE.md) - Development setup and contribution guidelines
- [Changelog](CHANGELOG.md) - Version history and changes

## Contributing

Contributions are welcome! Please read our [Developer Guide](docs/DEVELOPER_GUIDE.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the UI
- Uses [python-caldav](https://github.com/python-caldav/caldav) for CalDAV support
- System tray integration via [pystray](https://github.com/moses-palmer/pystray)

## Support

If you encounter any issues or have questions:
1. Check the [User Guide](docs/USER_GUIDE.md)
2. Look through [existing issues](https://github.com/yourname/calendar-desktop-notifications/issues)
3. Create a new issue with detailed information about your problem 