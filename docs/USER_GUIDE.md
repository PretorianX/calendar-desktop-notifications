# User Guide - Calendar Desktop Notifications

## Table of Contents
1. [Installation](#installation)
2. [Initial Setup](#initial-setup)
3. [Using the Application](#using-the-application)
4. [Configuration Options](#configuration-options)
5. [Troubleshooting](#troubleshooting)

## Installation

### Pre-built Executables (Recommended)

Download the appropriate version for your operating system from the [releases page](https://github.com/yourname/calendar-desktop-notifications/releases):

- **Windows**: `calendar-desktop-notifications-windows-amd64.exe`
- **macOS**: `calendar-desktop-notifications-macos-amd64`
- **Linux**: `calendar-desktop-notifications-linux-amd64`

### From Source

1. Ensure Python 3.11 or later is installed
2. Clone the repository
3. Run the setup script:
   ```bash
   ./setup.sh
   ```

## Initial Setup

### 1. Launch the Application

- **Windows**: Double-click the executable
- **macOS/Linux**: Run `./calendar-desktop-notifications` from terminal or double-click

The application will start in your system tray.

### 2. Configure CalDAV Connection

1. Right-click the system tray icon
2. Select "Settings"
3. Enter your CalDAV server details:
   - **URL**: Your CalDAV server URL (e.g., `https://caldav.example.com/`)
   - **Username**: Your CalDAV username
   - **Password**: Your CalDAV password
   - **Calendar Name**: (Optional) Specific calendar to sync

4. Click "Test Connection" to verify settings
5. Click "Save" to apply settings

## Using the Application

### System Tray Menu

Right-click the tray icon to access:

- **Force Sync**: Manually sync calendars
- **Settings**: Open configuration dialog
- **Quit**: Exit the application

### Notifications

The application will notify you:
- 1 minute before meetings
- 5 minutes before meetings
- 10 minutes before meetings

### Automatic Features

- **URL Opening**: If a meeting has a URL in the location field, it will automatically open in your browser
- **Sound Alerts**: Plays a sound for each notification (can be disabled in settings)
- **Time Display**: The tray icon shows time until your next meeting

## Configuration Options

### Sync Settings

- **Sync Interval**: How often to check for calendar updates (default: 5 minutes)
- **Sync Period**: How many hours ahead to sync events (default: 24 hours)

### Notification Settings

- **Notification Times**: Comma-separated list of minutes before event (e.g., "1,5,10")
- **Sound Enabled**: Toggle notification sounds on/off

### Other Options

- **Auto Open URLs**: Automatically open meeting URLs in browser

## Troubleshooting

### Connection Issues

1. Verify your CalDAV URL is correct
2. Check username and password
3. Ensure your internet connection is active
4. Try adding/removing trailing slash from URL

### Missing Notifications

1. Check system notification settings
2. Verify the application is running in system tray
3. Ensure sync is working (check last sync time)

### Sound Not Playing

1. Check system volume
2. Verify "Sound Enabled" is checked in settings
3. Ensure WAV files exist in the sounds directory

### Logs

Application logs are stored in:
- **Windows**: `%APPDATA%\calendar-desktop-notifications\logs`
- **macOS**: `~/Library/Application Support/calendar-desktop-notifications/logs`
- **Linux**: `~/.config/calendar-desktop-notifications/logs` 