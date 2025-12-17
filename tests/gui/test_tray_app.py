"""Tests for the TrayApp GUI components."""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.gui.tray_app import SettingsDialog, TrayApp


@pytest.mark.skipif(
    os.environ.get("ENABLE_QT_TESTS") != "1",
    reason="Qt GUI tests require a real GUI environment. Set ENABLE_QT_TESTS=1 to run.",
)
class TestSettingsDialog:
    """Tests for the SettingsDialog class."""

    def setup_dialog(self, mock_config_manager=None):
        """Setup a dialog instance for testing."""
        if mock_config_manager is None:
            mock_config_manager = MagicMock()

        mock_config = {
            "caldav": {
                "url": "https://example.com/caldav",
                "username": "test_user",
                "password": "test_pass",
                "calendar_name": "Test Calendar",
            },
            "sync": {"interval_minutes": 5, "sync_hours": 24},
            "notifications": {"intervals_minutes": [1, 5, 10], "sound_enabled": True},
            "auto_open_urls": True,
        }

        mock_config_manager.get_config.return_value = mock_config

        return SettingsDialog(mock_config_manager)

    @patch("src.gui.tray_app.CalDAVClient")
    @patch("src.gui.tray_app.QtWidgets.QMessageBox")
    @patch("src.config.config_manager.ConfigManager")
    def test_connection_success(
        self, mock_config_manager, mock_message_box, mock_caldav_client
    ):
        """Test successful connection to CalDAV server."""
        # Setup
        dialog = self.setup_dialog(mock_config_manager)

        # Mock successful connection
        mock_client_instance = MagicMock()
        mock_client_instance.connect.return_value = True
        mock_client_instance.calendar = MagicMock()
        mock_client_instance.calendar.name = "Test Calendar"

        mock_caldav_client.return_value = mock_client_instance

        # Test
        dialog._test_connection()

        # Verify
        mock_caldav_client.assert_called_once_with(
            "https://example.com/caldav", "test_user", "test_pass", "Test Calendar"
        )
        mock_client_instance.connect.assert_called_once()
        mock_message_box.information.assert_called_once()

    @patch("src.gui.tray_app.CalDAVClient")
    @patch("src.gui.tray_app.QtWidgets.QMessageBox")
    @patch("src.config.config_manager.ConfigManager")
    def test_connection_failure(
        self, mock_config_manager, mock_message_box, mock_caldav_client
    ):
        """Test failed connection to CalDAV server."""
        # Setup
        dialog = self.setup_dialog(mock_config_manager)

        # Mock failed connection
        mock_client_instance = MagicMock()
        mock_client_instance.connect.return_value = False

        mock_caldav_client.return_value = mock_client_instance

        # Test
        dialog._test_connection()

        # Verify
        mock_caldav_client.assert_called_once()
        mock_client_instance.connect.assert_called_once()
        mock_message_box.critical.assert_called_once()

    @patch("src.gui.tray_app.CalDAVClient")
    @patch("src.gui.tray_app.QtWidgets.QMessageBox")
    @patch("src.config.config_manager.ConfigManager")
    def test_connection_exception(
        self, mock_config_manager, mock_message_box, mock_caldav_client
    ):
        """Test exception during CalDAV connection."""
        # Setup
        dialog = self.setup_dialog(mock_config_manager)

        # Mock exception during connection
        mock_client_instance = MagicMock()
        mock_client_instance.connect.side_effect = Exception("Connection error")

        mock_caldav_client.return_value = mock_client_instance

        # Test
        dialog._test_connection()

        # Verify
        mock_caldav_client.assert_called_once()
        mock_client_instance.connect.assert_called_once()
        mock_message_box.critical.assert_called_once()

    @patch("src.gui.tray_app.QtWidgets.QMessageBox")
    @patch("src.config.config_manager.ConfigManager")
    def test_connection_missing_url(self, mock_config_manager, mock_message_box):
        """Test connection test with missing URL."""
        # Setup
        dialog = self.setup_dialog(mock_config_manager)
        dialog.url_input.setText("")

        # Test
        dialog._test_connection()

        # Verify
        mock_message_box.warning.assert_called_once()

    @patch("src.gui.tray_app.QtWidgets.QApplication")
    @patch("src.config.config_manager.ConfigManager")
    def test_cursor_reset_on_exception(self, mock_config_manager, mock_qapp):
        """Test that cursor is reset even when exceptions occur."""
        # Mock QtWidgets.QMessageBox to prevent actual dialog creation
        with patch("src.gui.tray_app.QtWidgets.QMessageBox"):
            # Setup
            dialog = self.setup_dialog(mock_config_manager)

            with patch("src.gui.tray_app.CalDAVClient") as mock_caldav_client:
                # Mock exception during connection
                mock_client_instance = MagicMock()
                mock_client_instance.connect.side_effect = Exception("Connection error")
                mock_caldav_client.return_value = mock_client_instance

                # Test
                dialog._test_connection()

            # Verify cursor was reset
            mock_qapp.restoreOverrideCursor.assert_called_once()


class TestTrayApp:
    """Tests for the TrayApp class."""

    @patch("src.gui.tray_app.QtWidgets.QApplication")
    @patch("src.gui.tray_app.NotificationManager")
    @patch("src.gui.tray_app.CalDAVClient")
    @patch("src.gui.tray_app.ConfigManager")
    def test_sync_calendar_uses_configured_sync_hours(
        self,
        mock_config_manager,
        mock_caldav_client,
        mock_notification_manager,
        mock_qapp,
    ):
        """Test that _sync_calendar uses the configured sync_hours value."""
        # Setup mock config with custom sync_hours
        mock_config = {
            "caldav": {
                "url": "https://example.com/caldav",
                "username": "test_user",
                "password": "test_pass",
                "calendar_name": "Test Calendar",
            },
            "sync": {"interval_minutes": 5, "sync_hours": 48},  # Custom sync hours
            "notifications": {"intervals_minutes": [1, 5, 10], "sound_enabled": True},
            "auto_open_urls": True,
        }
        mock_config_manager.return_value.get_config.return_value = mock_config

        # Mock the caldav client instance
        mock_caldav_instance = MagicMock()
        mock_caldav_client.return_value = mock_caldav_instance

        # Create the TrayApp instance with mocked dependencies
        tray_app = TrayApp()

        # Mock datetime.now() to return a fixed time
        fixed_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        with patch("src.gui.tray_app.datetime.datetime") as mock_datetime_class:
            # Mock the datetime.now().astimezone() chain
            mock_now = MagicMock()
            mock_now.astimezone.return_value = fixed_now
            mock_datetime_class.now.return_value = mock_now

            # Also need to mock datetime.timedelta
            with patch("src.gui.tray_app.datetime.timedelta", timedelta):
                # Call the sync calendar method
                tray_app._sync_calendar()

                # Calculate the expected end time based on configured sync_hours (48)
                expected_end_time = fixed_now + timedelta(hours=48)

                # Verify that get_events was called with correct time range
                mock_caldav_instance.get_events.assert_called_once()
                call_args = mock_caldav_instance.get_events.call_args[0]

                # First arg should be the current time
                assert call_args[0] == fixed_now

                # Second arg should be current time + sync_hours
                assert call_args[1] == expected_end_time

    @patch("src.gui.tray_app.QtWidgets.QApplication")
    @patch("src.gui.tray_app.NotificationManager")
    @patch("src.gui.tray_app.CalDAVClient")
    @patch("src.gui.tray_app.ConfigManager")
    @patch("src.gui.tray_app.sys")
    def test_notification_thread_runs_independently(
        self,
        mock_sys,
        mock_config_manager,
        mock_caldav_client,
        mock_notification_manager,
        mock_qapp,
    ):
        """Test that the notification thread runs independently of the sync thread."""
        # Mock sys.platform to avoid macOS-specific thread creation
        mock_sys.platform = "linux"

        # Setup mock config
        mock_config = {
            "caldav": {
                "url": "https://example.com/caldav",
                "username": "test_user",
                "password": "test_pass",
                "calendar_name": "Test Calendar",
            },
            "sync": {"interval_minutes": 5, "sync_hours": 24},
            "notifications": {"intervals_minutes": [1, 5, 10], "sound_enabled": True},
            "auto_open_urls": True,
        }
        mock_config_manager.return_value.get_config.return_value = mock_config

        # Setup mock clients
        mock_caldav_instance = MagicMock()
        mock_caldav_client.return_value = mock_caldav_instance

        mock_notification_instance = MagicMock()
        mock_notification_manager.return_value = mock_notification_instance

        # Create app with threading and pystray patched
        with patch("src.gui.tray_app.threading.Thread") as mock_thread:
            # Mock the icon to prevent actual system tray creation
            with patch("src.gui.tray_app.pystray.Icon") as mock_icon:
                mock_icon_instance = MagicMock()
                mock_icon.return_value = mock_icon_instance

                # Mock icon.run() to prevent blocking
                mock_icon_instance.run = MagicMock()

                tray_app = TrayApp()

                # Reset the mock to clear any calls from __init__
                mock_thread.reset_mock()

                # Call run but it won't block because icon.run is mocked
                tray_app.run()

                # Verify that two threads were created - one for sync and one for notifications
                assert (
                    mock_thread.call_count == 2
                ), f"Expected 2 threads, but got {mock_thread.call_count}"

                # Extract the thread creation calls
                thread_calls = mock_thread.call_args_list

                # Verify thread targets
                sync_thread_created = False
                notification_thread_created = False

                for call in thread_calls:
                    # Thread can be created with target as first positional arg or as keyword arg
                    if call.args and len(call.args) > 0:
                        # Positional argument case
                        target = call.args[0]
                    else:
                        # Keyword argument case
                        target = call.kwargs.get("target")

                    if target and hasattr(target, "__name__"):
                        if target.__name__ == "_sync_thread_func":
                            sync_thread_created = True
                        elif target.__name__ == "_notification_thread_func":
                            notification_thread_created = True

                assert sync_thread_created, "Sync thread was not created"
                assert (
                    notification_thread_created
                ), "Notification thread was not created"

                # Verify both threads were marked as daemon
                for call in thread_calls:
                    assert (
                        call.kwargs.get("daemon") is None
                        or call.kwargs.get("daemon") is True
                    )

                # Verify threads were started
                assert mock_thread.return_value.start.call_count == 2

    @patch("src.gui.tray_app.QtWidgets.QApplication")
    @patch("src.gui.tray_app.NotificationManager")
    @patch("src.gui.tray_app.CalDAVClient")
    @patch("src.gui.tray_app.ConfigManager")
    @patch("src.gui.tray_app.time")
    def test_notification_check_function(
        self,
        mock_time,
        mock_config_manager,
        mock_caldav_client,
        mock_notification_manager,
        mock_qapp,
    ):
        """Test that notification check function checks events correctly."""
        # Setup test data
        mock_config_manager.return_value.get_config.return_value = {
            "caldav": {"url": "", "username": "", "password": "", "calendar_name": ""},
            "sync": {"interval_minutes": 5, "sync_hours": 24},
            "notifications": {"intervals_minutes": [1, 5], "sound_enabled": True},
            "auto_open_urls": True,
        }

        # Create TrayApp instance with mocked dependencies
        tray_app = TrayApp()

        # Test scenario: with events
        tray_app._set_events(["event1", "event2"])

        tray_app._check_notifications()

        # Verify notification manager was called
        mock_notification_manager.return_value.check_events.assert_called_with(
            ["event1", "event2"]
        )

    @patch("src.gui.tray_app.QtWidgets.QApplication")
    @patch("src.gui.tray_app.NotificationManager")
    @patch("src.gui.tray_app.CalDAVClient")
    @patch("src.gui.tray_app.ConfigManager")
    @patch("src.gui.tray_app.Image")
    @patch("src.gui.tray_app.ImageDraw")
    def test_tray_icon_shows_meeting_time(
        self,
        mock_image_draw,
        mock_image,
        mock_config_manager,
        mock_caldav_client,
        mock_notification_manager,
        mock_qapp,
    ):
        """Test that tray icon displays time until next meeting correctly."""
        # Setup mock config
        mock_config_manager.return_value.get_config.return_value = {
            "caldav": {"url": "", "username": "", "password": "", "calendar_name": ""},
            "sync": {"interval_minutes": 5, "sync_hours": 24},
            "notifications": {"intervals_minutes": [1, 5], "sound_enabled": True},
            "auto_open_urls": True,
        }

        # Create test event
        fixed_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Create a mock for the drawing context
        mock_draw = MagicMock()
        mock_image_draw.Draw.return_value = mock_draw

        # Create app instance with mocked dependencies
        with patch("src.gui.tray_app.pystray"):
            with patch("src.gui.tray_app.datetime") as mock_datetime:
                # Mock the datetime module properly for all uses
                mock_datetime.datetime = MagicMock()
                mock_datetime.datetime.now = MagicMock()
                mock_datetime.datetime.combine = datetime.combine
                mock_datetime.timedelta = timedelta

                # Mock the datetime.now().astimezone() chain
                mock_now = MagicMock()
                mock_now.astimezone.return_value = fixed_now
                mock_datetime.datetime.now.return_value = mock_now

                tray_app = TrayApp()

                # Test case 1: No events
                tray_app._events = []
                tray_app._create_icon_image()
                # No specific assertions for no events case

                # Test case 2: Event in the past (0 minutes)
                # The implementation skips recently past events, so we need to test differently
                # Let's test with an event that just started (0 minutes from now)
                current_event = MagicMock()
                current_event.start_time = fixed_now  # Event starting right now
                current_event.summary = "Current meeting"

                tray_app._events = [current_event]
                mock_draw.reset_mock()
                tray_app._create_icon_image()
                # Verify "0" text
                mock_draw.text.assert_called()
                assert any("0" in str(call) for call in mock_draw.text.call_args_list)

                # Test case 3: Event in 3 minutes
                soon_event = MagicMock()
                soon_event.start_time = fixed_now + timedelta(minutes=3)
                soon_event.summary = "Upcoming meeting soon"

                tray_app._events = [soon_event]
                mock_draw.reset_mock()
                tray_app._create_icon_image()
                # Verify "3" text
                mock_draw.text.assert_called()
                assert any("3" in str(call) for call in mock_draw.text.call_args_list)

                # Test case 4: Event in 7 minutes
                medium_event = MagicMock()
                medium_event.start_time = fixed_now + timedelta(minutes=7)
                medium_event.summary = "Medium time meeting"

                tray_app._events = [medium_event]
                mock_draw.reset_mock()
                tray_app._create_icon_image()

                # Verify "7" text
                mock_draw.text.assert_called()
                print(f"Text calls: {mock_draw.text.call_args_list}")  # Debug print
                assert any("7" in str(call) for call in mock_draw.text.call_args_list)

                # Test case 5: Event in 15 minutes
                far_event = MagicMock()
                far_event.start_time = fixed_now + timedelta(minutes=15)
                far_event.summary = "Far meeting"

                tray_app._events = [far_event]
                mock_draw.reset_mock()
                tray_app._create_icon_image()
                # Verify "15" text
                mock_draw.text.assert_called()
                assert any("15" in str(call) for call in mock_draw.text.call_args_list)

                # Test case 6: Event in 120 minutes (capped at 99)
                very_far_event = MagicMock()
                very_far_event.start_time = fixed_now + timedelta(minutes=120)
                very_far_event.summary = "Very far meeting"

                tray_app._events = [very_far_event]
                mock_draw.reset_mock()
                tray_app._create_icon_image()
                # Verify "99" text
                mock_draw.text.assert_called()
                assert any("99" in str(call) for call in mock_draw.text.call_args_list)
