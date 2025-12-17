"""System tray application for calendar notifications."""

import datetime
import logging
import os
import sys
import threading
import time
import webbrowser
from datetime import datetime as DateTimeType

import pystray
from PIL import Image, ImageDraw, ImageFont
from PyQt6 import QtCore, QtWidgets

from src.calendar_sync.caldav_client import CalDAVClient
from src.config.config_manager import ConfigManager
from src.notification.notification_manager import NotificationManager

logger = logging.getLogger(__name__)


class _MacNativeTrayIcon:
    """macOS tray icon implementation using AppKit.

    pystray cannot distinguish left vs right click on macOS (platform limitation),
    so we implement the status bar item directly to support:
    - left click: events list menu (each event opens URL if present)
    - right click: main control menu (Settings / Force Sync / Exit)
    """

    def __init__(self, app: "TrayApp", icon_image: Image.Image):
        self._app = app
        self._status_item = None
        self._handler = None
        self._icon = icon_image

        # Lazily imported to keep non-macOS environments clean.
        import AppKit  # type: ignore
        import objc  # type: ignore
        from Foundation import NSObject  # type: ignore

        class _Handler(NSObject):
            def initWithApp_(self, tray_app):  # noqa: N802 - Cocoa naming
                self = objc.super(_Handler, self).init()
                if self is None:
                    return None
                self._tray_app = tray_app
                return self

            def onStatusItemClick_(self, sender):  # noqa: N802 - Cocoa naming
                event = AppKit.NSApp.currentEvent()
                if event is None:
                    return
                event_type = event.type()
                # Default to left-click behavior for unknown types.
                if event_type == AppKit.NSEventTypeRightMouseUp:
                    menu = self._tray_app._build_macos_main_menu()  # noqa: SLF001
                else:
                    menu = self._tray_app._build_macos_events_menu()  # noqa: SLF001
                self._tray_app.tray_icon._mac_status_item.popUpStatusItemMenu_(menu)  # type: ignore[attr-defined]  # noqa: SLF001

            def onSettings_(self, sender):  # noqa: N802 - Cocoa naming
                self._tray_app._show_settings()  # noqa: SLF001

            def onForceSync_(self, sender):  # noqa: N802 - Cocoa naming
                self._tray_app._force_sync()  # noqa: SLF001

            def onExit_(self, sender):  # noqa: N802 - Cocoa naming
                self._tray_app._exit()  # noqa: SLF001

            def onOpenEvent_(self, sender):  # noqa: N802 - Cocoa naming
                try:
                    url = sender.representedObject()
                except Exception:
                    url = None
                if url:
                    self._tray_app._open_url(str(url))  # noqa: SLF001

        # Ensure there is an NSApplication instance.
        AppKit.NSApplication.sharedApplication()

        self._handler = _Handler.alloc().initWithApp_(app)

        status_bar = AppKit.NSStatusBar.systemStatusBar()
        self._status_item = status_bar.statusItemWithLength_(
            AppKit.NSVariableStatusItemLength
        )

        button = self._status_item.button()
        button.setTarget_(self._handler)
        button.setAction_("onStatusItemClick:")
        button.sendActionOn_(
            AppKit.NSEventMaskLeftMouseUp | AppKit.NSEventMaskRightMouseUp
        )

        # Used by handler; mirror naming to avoid exposing private status item.
        self._mac_status_item = self._status_item

        # Initial icon.
        self.icon = icon_image

    @property
    def icon(self) -> Image.Image:
        return self._icon

    @icon.setter
    def icon(self, new_icon: Image.Image) -> None:
        self._icon = new_icon
        try:
            import AppKit  # type: ignore
            import Foundation  # type: ignore
            import io

            # Status bar icons must be small; otherwise macOS can render them huge.
            # 22x22 is the typical menu bar height on macOS.
            size_px = 22
            pil_icon = new_icon.convert("RGBA").resize(
                (size_px, size_px), resample=Image.Resampling.LANCZOS
            )

            png_bytes = io.BytesIO()
            pil_icon.save(png_bytes, format="PNG")
            raw = png_bytes.getvalue()
            ns_data = Foundation.NSData.dataWithBytes_length_(raw, len(raw))
            ns_image = AppKit.NSImage.alloc().initWithData_(ns_data)

            # Tell AppKit what size we expect.
            ns_image.setSize_(Foundation.NSMakeSize(size_px, size_px))

            button = self._status_item.button()
            button.setImageScaling_(AppKit.NSImageScaleProportionallyDown)
            button.setImage_(ns_image)
        except Exception as e:
            logger.error(f"Failed to update macOS tray icon image: {e}")

    def run(self):
        import AppKit  # type: ignore

        AppKit.NSApp.run()

    def stop(self):
        try:
            import AppKit  # type: ignore

            AppKit.NSApp.terminate_(None)
        except Exception:
            # Termination is best-effort.
            pass


# Add function to activate application on macOS
def activate_app_on_macos():
    """Activates the application and brings it to the foreground on macOS."""
    try:
        if sys.platform == "darwin":  # macOS
            import subprocess

            import psutil

            # Get our own process name
            process = psutil.Process(os.getpid())
            process_name = process.name()

            logger.debug(f"Current process name: {process_name}")

            # First try to activate using the process name
            apple_script = f'tell application "System Events" to set frontmost of process "{process_name}" to true'
            result = subprocess.run(
                ["osascript", "-e", apple_script], capture_output=True
            )

            if result.returncode != 0:
                logger.debug(
                    "Couldn't activate using process name, "
                    "trying parent application name"
                )

                # Try using the application name if process activation failed
                # This gets the name of the application bundle on macOS
                apple_script = (
                    """
                tell application "System Events"
                    set frontApp to first application process whose unix id is %d
                    set frontmost of frontApp to true
                end tell
                """
                    % os.getpid()
                )

                subprocess.run(
                    ["osascript", "-e", apple_script], check=False, capture_output=True
                )

            logger.debug("Activated application on macOS")
    except Exception as e:
        logger.error(f"Error activating application: {e}")


class SettingsDialog(QtWidgets.QDialog):
    """Settings dialog for the application."""

    def __init__(self, config_manager: ConfigManager, parent=None):
        """Initialize settings dialog."""
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = config_manager.get_config()

        self.setWindowTitle("Calendar Notifications Settings")
        self.resize(450, 350)

        self._init_ui()

        # Set window flags to ensure it appears on top
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )

        # Activate app when dialog is shown
        activate_app_on_macos()

        # Make sure window is active and raised
        self.activateWindow()
        self.raise_()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QtWidgets.QVBoxLayout(self)

        # CalDAV settings
        caldav_form = QtWidgets.QFormLayout()

        self.url_input = QtWidgets.QLineEdit(self.config["caldav"]["url"])
        caldav_form.addRow("CalDAV URL:", self.url_input)

        self.username_input = QtWidgets.QLineEdit(self.config["caldav"]["username"])
        caldav_form.addRow("Username:", self.username_input)

        self.password_input = QtWidgets.QLineEdit(self.config["caldav"]["password"])
        self.password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        caldav_form.addRow("Password:", self.password_input)

        self.calendar_name_input = QtWidgets.QLineEdit(
            self.config["caldav"]["calendar_name"]
        )
        caldav_form.addRow("Calendar Name:", self.calendar_name_input)

        # Add Test Connection button
        test_conn_layout = QtWidgets.QHBoxLayout()
        self.test_connection_button = QtWidgets.QPushButton("Test Connection")
        self.test_connection_button.clicked.connect(self._test_connection)
        test_conn_layout.addStretch()
        test_conn_layout.addWidget(self.test_connection_button)

        layout.addLayout(caldav_form)
        layout.addLayout(test_conn_layout)

        # Sync settings
        sync_form = QtWidgets.QFormLayout()

        self.sync_interval = QtWidgets.QSpinBox()
        self.sync_interval.setMinimum(1)
        self.sync_interval.setMaximum(60)
        self.sync_interval.setValue(self.config["sync"]["interval_minutes"])
        sync_form.addRow("Sync Interval (minutes):", self.sync_interval)

        self.sync_hours = QtWidgets.QSpinBox()
        self.sync_hours.setMinimum(1)
        self.sync_hours.setMaximum(168)  # Up to 7 days (7*24=168 hours)
        self.sync_hours.setValue(self.config["sync"]["sync_hours"])
        sync_form.addRow("Sync Period (hours):", self.sync_hours)

        layout.addLayout(sync_form)

        # Notification settings
        notifications_form = QtWidgets.QFormLayout()

        # Convert notification intervals list to comma-separated string
        notification_intervals_str = ", ".join(
            map(str, self.config["notifications"]["intervals_minutes"])
        )
        self.notification_intervals_input = QtWidgets.QLineEdit(
            notification_intervals_str
        )
        self.notification_intervals_input.setToolTip(
            "Enter minutes before meeting to show notifications, separated by commas (e.g. '1, 5, 10')"
        )
        notifications_form.addRow(
            "Notification Times (minutes):", self.notification_intervals_input
        )

        layout.addLayout(notifications_form)

        self.sound_enabled = QtWidgets.QCheckBox("Enable Sound Notifications")
        self.sound_enabled.setChecked(self.config["notifications"]["sound_enabled"])
        layout.addWidget(self.sound_enabled)

        self.auto_open_urls = QtWidgets.QCheckBox("Auto-open Meeting URLs")
        self.auto_open_urls.setChecked(self.config["auto_open_urls"])
        layout.addWidget(self.auto_open_urls)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)

        layout.addStretch()
        layout.addLayout(button_layout)

    def _test_connection(self):
        """Test connection to CalDAV server."""
        url = self.url_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        calendar_name = self.calendar_name_input.text().strip()

        if not url:
            QtWidgets.QMessageBox.warning(
                self, "Missing Information", "Please enter a CalDAV URL."
            )
            return

        try:
            # Show cursor as waiting
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)

            # Create a temporary client
            client = CalDAVClient(url, username, password, calendar_name)

            # Try to connect
            success = client.connect()

            # Restore cursor
            QtWidgets.QApplication.restoreOverrideCursor()

            if success:
                QtWidgets.QMessageBox.information(
                    self,
                    "Connection Successful",
                    f"Successfully connected to the CalDAV server.\n"
                    f"Calendar: {client.calendar.name if client.calendar else 'Default'}",
                )
            else:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Connection Failed",
                    "Could not connect to the CalDAV server or find the specified calendar.",
                )

        except Exception as e:
            # Restore cursor
            QtWidgets.QApplication.restoreOverrideCursor()

            logger.error(f"Error testing connection: {e}")
            QtWidgets.QMessageBox.critical(
                self, "Connection Error", f"Error connecting to CalDAV server: {str(e)}"
            )

    def save_settings(self):
        """Save settings to config."""
        try:
            # Parse notification intervals from comma-separated text
            intervals_text = self.notification_intervals_input.text().strip()
            notification_intervals = []

            try:
                if intervals_text:
                    # Split by comma, strip whitespace, convert to int
                    parts = [part.strip() for part in intervals_text.split(",")]
                    notification_intervals = sorted(
                        [int(part) for part in parts if part]
                    )

                if not notification_intervals:
                    # If parsing failed or empty, use default values
                    notification_intervals = [1, 5, 10]
                    logger.warning("Invalid notification intervals, using defaults")
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Invalid Input",
                        "Invalid notification intervals. Using default values (1, 5, 10 minutes).",
                    )
            except Exception as e:
                notification_intervals = [1, 5, 10]
                logger.warning(f"Error parsing notification intervals: {e}")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Invalid Input",
                    f"Error parsing notification intervals: {e}\nUsing default values (1, 5, 10 minutes).",
                )

            new_config = {
                "caldav": {
                    "url": self.url_input.text(),
                    "username": self.username_input.text(),
                    "password": self.password_input.text(),
                    "calendar_name": self.calendar_name_input.text(),
                },
                "sync": {
                    "interval_minutes": self.sync_interval.value(),
                    "sync_hours": self.sync_hours.value(),
                },
                "notifications": {
                    "sound_enabled": self.sound_enabled.isChecked(),
                    "intervals_minutes": notification_intervals,
                },
                "auto_open_urls": self.auto_open_urls.isChecked(),
            }

            logger.info(f"Saving notification intervals: {notification_intervals}")
            self.config_manager.update_config(new_config)
            self.accept()

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Error saving settings: {e}")


class TrayApp:
    """System tray application."""

    def __init__(self):
        """Initialize tray application."""
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()

        # Initialize CalDAV client
        self.caldav_client = CalDAVClient(
            url=self.config["caldav"]["url"],
            username=self.config["caldav"]["username"],
            password=self.config["caldav"]["password"],
            calendar_name=self.config["caldav"]["calendar_name"],
        )

        # Initialize notification manager
        self.notification_manager = NotificationManager(
            notification_intervals=self.config["notifications"]["intervals_minutes"],
            sound_enabled=self.config["notifications"]["sound_enabled"],
            auto_open_urls=self.config["auto_open_urls"],
        )

        # Initialize Qt application
        self.qt_app = QtWidgets.QApplication(sys.argv)

        # Initialize threads and flags
        self.sync_thread = None
        self.notification_thread = None
        self.running = True
        self._events_lock = threading.RLock()
        self._events = []

        # Tray icon is created on `run()` to avoid side effects during construction.
        self.tray_icon = None

    def _set_events(self, events):
        """Atomically replace cached events."""
        with self._events_lock:
            self._events = events

    def _get_events_snapshot(self):
        """Get a snapshot of cached events (thread-safe)."""
        with self._events_lock:
            return list(self._events)

    def _create_tray_icon(self):
        """Create system tray icon."""
        icon = self._create_macos_icon_image() if sys.platform == "darwin" else self._create_icon_image()

        if sys.platform == "darwin":
            # Native macOS tray icon to distinguish left vs right click.
            self.tray_icon = _MacNativeTrayIcon(self, icon)
        else:
            # pystray dynamic submenu to show upcoming events.
            def events_menu():
                return pystray.Menu(*self._build_pystray_event_items())

            menu = pystray.Menu(
                pystray.MenuItem("Events", events_menu),
                pystray.MenuItem(
                    "Show Events (Window)", lambda _icon, _item: self._show_events()
                ),
                pystray.MenuItem("Settings", lambda _icon, _item: self._show_settings()),
                pystray.MenuItem("Force Sync", lambda _icon, _item: self._force_sync()),
                pystray.MenuItem("Exit", lambda _icon, _item: self._exit()),
            )

            self.tray_icon = pystray.Icon(
                "calendar_notifications", icon, "Calendar Notifications", menu
            )

        # On macOS, we need to ensure the icon is visible on all monitors
        if sys.platform == "darwin":
            # Set icon to be visible across all displays
            try:
                import AppKit

                # This makes the icon visible in the menu bar regardless of which display is active
                AppKit.NSApp.setActivationPolicy_(
                    AppKit.NSApplicationActivationPolicyRegular
                )

                # After a short delay, switch back to accessory mode for the icon
                def switch_to_accessory():
                    import time

                    time.sleep(0.5)
                    AppKit.NSApp.setActivationPolicy_(
                        AppKit.NSApplicationActivationPolicyAccessory
                    )

                threading.Thread(target=switch_to_accessory, daemon=True).start()
            except Exception as e:
                logger.error(f"Error configuring macOS tray icon visibility: {e}")

    def _create_icon_image(self):
        """Create icon image for the tray."""
        events = self._get_events_snapshot()

        # Create a simple calendar icon
        width = 64
        height = 64
        image = Image.new("RGB", (width, height), color=(255, 255, 255))
        dc = ImageDraw.Draw(image)

        # Draw calendar outline
        dc.rectangle(
            (8, 8, width - 8, height - 8), fill=(0, 120, 212), outline=(0, 0, 0)
        )

        # Draw calendar header
        dc.rectangle((8, 8, width - 8, 20), fill=(0, 80, 140), outline=(0, 0, 0))

        # Display time until next meeting if available
        if events:
            next_event = self._get_next_event(events)
            if next_event:
                self._add_time_to_icon(dc, next_event, width, height)

        return image

    def _create_macos_icon_image(self):
        """Create a small (menubar-sized) icon for macOS with readable minutes.

        Keep the visual style close to the original tray icon (calendar header + body),
        but rendered at status-bar size.
        """
        events = self._get_events_snapshot()
        size = 22
        image = Image.new("RGBA", (size, size), color=(0, 0, 0, 0))
        dc = ImageDraw.Draw(image)

        def draw_calendar_shell(body_fill):
            # Outer body
            dc.rectangle(
                (1, 1, size - 2, size - 2),
                fill=body_fill,
                outline=(200, 200, 200, 255),
            )
            # Header strip (same color to keep a single background color per time range)
            header_h = 6
            header_fill = body_fill
            dc.rectangle(
                (1, 1, size - 2, 1 + header_h),
                fill=header_fill,
                outline=(200, 200, 200, 255),
            )

        next_event = self._get_next_event(events)
        if not events or not next_event:
            # Default calendar look before first sync / when no upcoming events.
            draw_calendar_shell((0, 120, 212, 255))
            return image

        now = datetime.datetime.now().astimezone()
        temp_time = getattr(next_event, "_temp_display_time", None)
        event_time = (
            temp_time if isinstance(temp_time, DateTimeType) else next_event.start_time
        )
        minutes_until = int((event_time - now).total_seconds() / 60)

        if minutes_until <= 0:
            text = "0"
        elif minutes_until > 99:
            text = "99"
        else:
            text = f"{minutes_until}"

        if minutes_until > 10:
            bg_color = (0, 180, 0, 255)
        elif minutes_until > 5:
            bg_color = (255, 200, 0, 255)
        else:
            bg_color = (220, 0, 0, 255)

        draw_calendar_shell(bg_color)

        # Small, readable font for menubar.
        font_size = 12 if len(text) <= 2 else 11
        try:
            font = ImageFont.truetype("Arial Bold", font_size)
        except OSError:
            try:
                font = ImageFont.truetype("Arial", font_size)
            except OSError:
                font = ImageFont.load_default()

        # Slight shadow for legibility.
        dc.text(
            (size // 2 + 1, size // 2 + 1),
            text,
            fill=(0, 0, 0, 180),
            font=font,
            anchor="mm",
        )
        dc.text(
            (size // 2, size // 2 + 0),
            text,
            fill=(255, 255, 255, 255),
            font=font,
            anchor="mm",
        )
        return image

    def _add_time_to_icon(self, dc, event, width, height):
        """Add time until next meeting to the icon.

        Args:
            dc: ImageDraw context
            event: Next calendar event
            width: Icon width
            height: Icon height
        """
        now = datetime.datetime.now().astimezone()

        # Use the adjusted time for recurring events if available.
        # NOTE: be defensive with MagicMock events in tests: MagicMock will "have"
        # any attribute, so only honor the temp time if it's a real datetime.
        temp_time = getattr(event, "_temp_display_time", None)
        event_time = (
            temp_time if isinstance(temp_time, DateTimeType) else event.start_time
        )
        minutes_until = int((event_time - now).total_seconds() / 60)

        # Create text to display - only show minutes
        if minutes_until <= 0:
            text = "0"
        elif minutes_until > 99:
            text = "99"
        else:
            text = f"{minutes_until}"

        # Set background color based on time remaining
        if minutes_until > 10:
            bg_color = (0, 180, 0)  # Green for > 10 minutes
        elif minutes_until > 5:
            bg_color = (255, 200, 0)  # Yellow for 5-10 minutes
        else:
            bg_color = (220, 0, 0)  # Red for < 5 minutes

        # Fill the entire icon with the background color
        dc.rectangle((8, 8, width - 8, height - 8), fill=bg_color, outline=(0, 0, 0))

        # Draw text with larger font for better visibility
        font_size = 32  # Increased from 16 to 32
        try:
            # Try to use a system font - fallback to default if not available
            try:
                font = ImageFont.truetype("Arial Bold", font_size)
            except IOError:
                try:
                    font = ImageFont.truetype("Arial", font_size)
                except IOError:
                    font = ImageFont.load_default()

            # Draw text with shadow for better visibility
            dc.text(
                (width // 2 + 1, height // 2 + 1),
                text,
                fill=(0, 0, 0),
                font=font,
                anchor="mm",
            )
            dc.text(
                (width // 2, height // 2),
                text,
                fill=(255, 255, 255),
                font=font,
                anchor="mm",
            )
        except Exception as e:
            logger.error(f"Error drawing time on icon: {e}")
            # Fallback - draw a simpler version
            dc.text((width // 2, height // 2), text, fill=(255, 255, 255))

    def _get_next_event(self, events):
        """Get the next upcoming event.

        Returns:
            CalendarEvent: Next upcoming event or None if no events
        """
        now = datetime.datetime.now().astimezone()

        # First check for adjusted recurring events (events that happen today)
        # This handles the case where the original start_time is in the past
        closest_event = None
        min_time_until = float("inf")

        for event in events:
            # For modified instances (events with RECURRENCE-ID), the CalDAV client has already
            # corrected the start_time to the actual event time, so treat them as regular events
            is_modified_instance = getattr(event, "is_modified_instance", False) is True
            if is_modified_instance:
                logger.debug(
                    f"Event '{event.summary}' is a modified instance with corrected time: {event.start_time} "
                    f"(RECURRENCE-ID: {getattr(event, 'recurrence_id', 'N/A')}). "
                    f"Using corrected time for tray icon."
                )
                # Check if this future event is sooner than what we've found
                if event.start_time > now:
                    time_until = (event.start_time - now).total_seconds() / 60
                    if time_until < min_time_until:
                        min_time_until = time_until
                        closest_event = event
                continue

            # Skip events that are already over
            if event.start_time < now:
                # For events with start times far in the past, check if they might be recurring events
                time_until_event = (event.start_time - now).total_seconds() / 60
                if time_until_event < -1440:  # More than 1 day in the past

                    # Try to determine if this event recurs today
                    try:
                        # Get the time component from the original event
                        event_time = event.start_time.time()

                        # FIXED: Use the original event's timezone, not local timezone
                        original_timezone = event.start_time.tzinfo

                        # FIXED: Create today's occurrence using utility function for proper timezone handling
                        today_date = now.astimezone(original_timezone).date()
                        today_occurrence = _create_timezone_aware_datetime(
                            today_date, event_time, original_timezone
                        )

                        # If this is a future occurrence today, consider it
                        if today_occurrence > now:
                            time_until = (today_occurrence - now).total_seconds() / 60
                            if time_until < min_time_until:
                                min_time_until = time_until
                                # Create a copy of the event with the adjusted time
                                closest_event = event
                                # We can't modify the original event as it's used elsewhere
                                # But we can return a modified version for display purposes
                                closest_event._temp_display_time = today_occurrence
                    except Exception as e:
                        logger.error(
                            f"Error calculating recurring event time for icon: {e}"
                        )
                continue

            # For regular future events, check if they're sooner than what we've found
            time_until = (event.start_time - now).total_seconds() / 60
            if time_until < min_time_until:
                min_time_until = time_until
                closest_event = event

        return closest_event

    def _show_events(self, _=None):
        """Show upcoming events in a dialog."""
        events = self._get_events_snapshot()

        class EventsDialog(QtWidgets.QDialog):
            def __init__(self, events, parent=None):
                super().__init__(parent)
                self.events = events
                self.setWindowTitle("Upcoming Events")
                self.resize(500, 400)
                self._init_ui()

                # Set window flags to ensure it appears on top
                self.setWindowFlags(
                    self.windowFlags() | QtCore.Qt.WindowType.WindowStaysOnTopHint
                )

                # Make sure window is active and raised
                self.activateWindow()
                self.raise_()

            def _init_ui(self):
                layout = QtWidgets.QVBoxLayout(self)

                if not self.events:
                    layout.addWidget(QtWidgets.QLabel("No upcoming events found."))
                else:
                    event_list = QtWidgets.QListWidget()

                    for event in self.events:
                        start_time = event.start_time.strftime("%Y-%m-%d %H:%M")
                        event_list.addItem(f"{start_time} - {event.summary}")

                    layout.addWidget(event_list)

                close_button = QtWidgets.QPushButton("Close")
                close_button.clicked.connect(self.accept)
                layout.addWidget(close_button)

        dialog = EventsDialog(events)
        # Activate app when dialog is shown
        activate_app_on_macos()
        dialog.exec()

    def _open_url(self, url: str) -> None:
        """Open a URL in the default browser."""
        webbrowser.open(url)

    def _format_event_menu_title(self, event) -> str:
        """Format an event label for tray menus."""
        start_time = event.start_time.strftime("%Y-%m-%d %H:%M")
        summary = getattr(event, "summary", "Untitled")
        return f"{start_time} - {summary}"

    def _get_event_display_start_time(self, event, now: DateTimeType) -> DateTimeType | None:
        """Compute an event's display start time for menus.

        - Returns None for events that should not be shown (already in the past).
        - For recurring events whose original DTSTART is long in the past, tries to
          compute today's occurrence in the event's original timezone (same logic as tray icon).
        """
        # Modified instances already have the corrected start_time.
        if getattr(event, "is_modified_instance", False) is True:
            return event.start_time if event.start_time > now else None

        start_time = event.start_time
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=now.tzinfo)

        if start_time > now:
            return start_time

        # Skip events that are already in the past (including earlier today).
        time_until_event = (start_time - now).total_seconds() / 60
        if time_until_event >= -1440:
            return None

        # Attempt to compute today's occurrence for recurring events with DTSTART far in the past.
        try:
            event_time = start_time.time()
            original_timezone = start_time.tzinfo
            today_date = now.astimezone(original_timezone).date()
            today_occurrence = _create_timezone_aware_datetime(
                today_date, event_time, original_timezone
            )
            return today_occurrence if today_occurrence > now else None
        except Exception as e:
            logger.error(f"Error calculating recurring event time for menu: {e}")
            return None

    def _get_event_menu_entries(self):
        """Get (title, url) entries for upcoming events menus."""
        now = datetime.datetime.now().astimezone()
        entries: list[tuple[DateTimeType, str, str | None]] = []

        for event in self._get_events_snapshot():
            display_start = self._get_event_display_start_time(event, now)
            if display_start is None:
                continue

            summary = getattr(event, "summary", "Untitled")
            title = f"{display_start:%Y-%m-%d %H:%M} - {summary}"
            entries.append((display_start, title, event.get_url()))

        entries.sort(key=lambda x: x[0])
        return [(title, url) for _dt, title, url in entries]

    def _build_pystray_event_items(self):
        """Build pystray menu items for events (dynamic)."""
        entries = self._get_event_menu_entries()
        if not entries:
            return (pystray.MenuItem("No upcoming events", None, enabled=False),)

        items = []
        for title, url in entries:
            if url:
                items.append(
                    pystray.MenuItem(
                        title,
                        lambda _icon, _item, url=url: self._open_url(url),
                    )
                )
            else:
                items.append(pystray.MenuItem(title, None, enabled=False))

        return tuple(items)

    def _build_macos_events_menu(self):
        """Build the macOS left-click menu (events list)."""
        import AppKit  # type: ignore

        menu = AppKit.NSMenu.alloc().init()
        entries = self._get_event_menu_entries()
        if not entries:
            item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "No upcoming events", None, ""
            )
            item.setEnabled_(False)
            menu.addItem_(item)
            return menu

        for title, url in entries:
            item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                title, "onOpenEvent:", ""
            )
            item.setTarget_(self.tray_icon._handler)  # type: ignore[attr-defined]  # noqa: SLF001
            if url:
                item.setRepresentedObject_(url)
            else:
                item.setEnabled_(False)
            menu.addItem_(item)

        return menu

    def _build_macos_main_menu(self):
        """Build the macOS right-click menu (controls)."""
        import AppKit  # type: ignore

        menu = AppKit.NSMenu.alloc().init()

        settings = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Settings", "onSettings:", ""
        )
        settings.setTarget_(self.tray_icon._handler)  # type: ignore[attr-defined]  # noqa: SLF001
        menu.addItem_(settings)

        force_sync = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Force Sync", "onForceSync:", ""
        )
        force_sync.setTarget_(self.tray_icon._handler)  # type: ignore[attr-defined]  # noqa: SLF001
        menu.addItem_(force_sync)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        exit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Exit", "onExit:", ""
        )
        exit_item.setTarget_(self.tray_icon._handler)  # type: ignore[attr-defined]  # noqa: SLF001
        menu.addItem_(exit_item)

        return menu

    def _show_settings(self, _=None):
        """Show settings dialog."""
        dialog = SettingsDialog(self.config_manager)
        # Activate app when dialog is shown
        activate_app_on_macos()
        if dialog.exec():
            # Reload configuration
            self.config = self.config_manager.get_config()

            # Update CalDAV client
            self.caldav_client = CalDAVClient(
                url=self.config["caldav"]["url"],
                username=self.config["caldav"]["username"],
                password=self.config["caldav"]["password"],
                calendar_name=self.config["caldav"]["calendar_name"],
            )

            # Update notification manager
            self.notification_manager = NotificationManager(
                notification_intervals=self.config["notifications"][
                    "intervals_minutes"
                ],
                sound_enabled=self.config["notifications"]["sound_enabled"],
                auto_open_urls=self.config["auto_open_urls"],
            )

            # Force sync
            self._force_sync()

    def _force_sync(self, _=None):
        """Force calendar synchronization."""
        logger.info("Manual force sync requested")
        # Run in a separate thread to avoid blocking the UI
        sync_thread = threading.Thread(target=self._sync_calendar)
        sync_thread.daemon = True
        sync_thread.start()

    def _exit(self, _=None):
        """Exit the application."""
        self.running = False
        if self.tray_icon is not None:
            self.tray_icon.stop()
        self.qt_app.quit()

    def _sync_calendar(self):
        """Synchronize calendar events."""
        try:
            now = datetime.datetime.now().astimezone()
            sync_end = now + datetime.timedelta(hours=self.config["sync"]["sync_hours"])

            # Get events for configured sync period
            events = self.caldav_client.get_events(now, sync_end)
            self._set_events(events)

            # Initial check for notifications
            self.notification_manager.check_events(events)

            # Update tray icon with time to next meeting
            self._update_tray_icon()

            logger.info(
                f"Synced {len(events)} events for the next {self.config['sync']['sync_hours']} hours"
            )

        except Exception as e:
            logger.error(f"Error syncing calendar: {e}")

    def _check_notifications(self):
        """Check for notifications on already synced events."""
        events = self._get_events_snapshot()
        if events:
            logger.debug("Performing notification check on cached events")
            self.notification_manager.check_events(events)

            # Update the tray icon to reflect current time until next meeting
            self._update_tray_icon()
        else:
            logger.debug("No events to check for notifications")

    def _update_tray_icon(self):
        """Update the tray icon with current time until next meeting."""
        try:
            if self.tray_icon is None:
                return
            new_icon = (
                self._create_macos_icon_image()
                if sys.platform == "darwin"
                else self._create_icon_image()
            )
            self.tray_icon.icon = new_icon
        except Exception as e:
            logger.error(f"Error updating tray icon: {e}")

    def _notification_thread_func(self):
        """Thread function to check for notifications more frequently."""
        logger.info("Notification check thread started")
        while self.running:
            try:
                # Check notifications more frequently (every 20 seconds) to avoid missing notification windows
                for _ in range(20):
                    if not self.running:
                        break
                    time.sleep(1)

                if not self.running:
                    break

                self._check_notifications()
            except Exception as e:
                logger.error(f"Error in notification check thread: {e}")
                time.sleep(5)  # Wait 5 seconds and try again

    def _sync_thread_func(self):
        """Calendar sync thread function."""
        while self.running:
            try:
                self._sync_calendar()

                # Sleep for sync interval (minutes)
                for _ in range(self.config["sync"]["interval_minutes"] * 60):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in sync thread: {e}")
                time.sleep(30)  # Wait 30 seconds and try again

    def run(self):
        """Run the application."""
        # Create tray icon at start-up (side-effectful / platform-specific)
        self._create_tray_icon()

        # Start sync thread
        self.sync_thread = threading.Thread(target=self._sync_thread_func)
        self.sync_thread.daemon = True
        self.sync_thread.start()

        # Start notification check thread
        self.notification_thread = threading.Thread(
            target=self._notification_thread_func
        )
        self.notification_thread.daemon = True
        self.notification_thread.start()

        # On macOS, ensure the icon is properly registered with the system
        if sys.platform == "darwin":
            try:
                # Force an update to ensure the icon is created properly
                self._update_tray_icon()
            except Exception as e:
                logger.error(f"Error updating tray icon during startup: {e}")

        # Run tray icon
        if self.tray_icon is None:
            raise RuntimeError("Tray icon was not initialized")
        self.tray_icon.run()


def setup_logging():
    """Setup application logging."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                os.path.join(os.path.expanduser("~"), ".calendar_notifications.log")
            ),
        ],
    )

    # Set custom log levels for noisy modules
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("pystray").setLevel(logging.WARNING)

    logger.info("Logging initialized at DEBUG level")


def main():
    """Main entry point."""
    setup_logging()
    logger.info("Starting Calendar Notifications app")

    app = TrayApp()
    app.run()


if __name__ == "__main__":
    main()


def _create_timezone_aware_datetime(date_obj, time_obj, timezone_obj):
    """Create a timezone-aware datetime, handling different timezone types.

    Args:
        date_obj: date object
        time_obj: time object
        timezone_obj: timezone object (could be pytz, _tzicalvtz, etc.)

    Returns:
        timezone-aware datetime object
    """
    # Combine date and time first
    naive_dt = datetime.datetime.combine(date_obj, time_obj)

    # Handle different timezone types
    if hasattr(timezone_obj, "localize"):
        # Standard pytz timezone
        return timezone_obj.localize(naive_dt)
    else:
        # For _tzicalvtz and other timezone types, use replace
        return naive_dt.replace(tzinfo=timezone_obj)
