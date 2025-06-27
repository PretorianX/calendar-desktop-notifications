"""Notification manager for desktop notifications."""

import datetime
import logging
import os
import platform
import subprocess
import threading
import webbrowser
from typing import List

import simpleaudio as sa
import pytz

from src.calendar_sync.caldav_client import CalendarEvent

logger = logging.getLogger(__name__)


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
    if hasattr(timezone_obj, 'localize'):
        # Standard pytz timezone
        return timezone_obj.localize(naive_dt)
    else:
        # For _tzicalvtz and other timezone types, use replace
        return naive_dt.replace(tzinfo=timezone_obj)


class NotificationManager:
    """Manages desktop notifications for calendar events."""

    def __init__(
        self,
        notification_intervals: List[int],
        sound_enabled: bool = True,
        auto_open_urls: bool = True,
    ):
        """Initialize notification manager.

        Args:
            notification_intervals: List of minutes before event to show notifications
            sound_enabled: Whether to play sound notifications
            auto_open_urls: Whether to automatically open URLs from event locations
        """
        self.notification_intervals = sorted(notification_intervals)
        self.sound_enabled = sound_enabled
        self.auto_open_urls = auto_open_urls
        self.notified_events = {}  # Dict to track notified events
        self.sounds_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sounds"
        )
        self._setup_sounds()
        self._url_opener_thread = None
        self._stop_flag = threading.Event()

        # Detect platform for platform-specific notification handling
        self.platform = platform.system()
        logger.info(f"Detected platform: {self.platform}")

    def _setup_sounds(self):
        """Setup notification sounds."""
        self.sounds = {}
        try:
            # Log sound directory
            logger.debug(f"Sound directory: {self.sounds_dir}")

            # Check if directory exists
            if not os.path.exists(self.sounds_dir):
                logger.error(f"Sound directory not found: {self.sounds_dir}")
                return

            # List available sound files
            sound_files = [f for f in os.listdir(self.sounds_dir) if f.endswith(".wav")]
            logger.debug(f"Available sound files: {sound_files}")

            # Map notification intervals to sound files
            for interval in self.notification_intervals:
                sound_file = os.path.join(
                    self.sounds_dir, f"notification_{interval}min.wav"
                )

                if os.path.exists(sound_file):
                    logger.debug(
                        f"Found sound file for {interval} minute notification: {sound_file}"
                    )
                    self.sounds[interval] = sound_file
                else:
                    logger.warning(
                        f"Sound file for {interval} minute notification not found"
                    )

            logger.info(
                f"Configured sound notifications for intervals: {list(self.sounds.keys())}"
            )
        except Exception as e:
            logger.error(f"Error setting up sounds: {e}")
            logger.exception("Detailed sound setup error")

    def check_events(self, events: List[CalendarEvent]):
        """Check events for notifications.

        Args:
            events: List of calendar events to check
        """
        now = datetime.datetime.now(datetime.timezone.utc)

        logger.debug(f"Checking {len(events)} events for notifications at {now}")

        for event in events:
            event_id = event.uid
            time_until_event = (event.start_time - now).total_seconds() / 60

            # Handle recurring events with past start times
            # If time is significantly negative (more than 1 day), check if this might be a recurring event
            if time_until_event < -1440:  # More than 1 day in the past
                logger.debug(
                    f"Event '{event.summary}' has a start time far in the past "
                    f"(time_until_event={time_until_event:.2f} min)"
                )

                try:
                    # Try to determine if this event recurs today or tomorrow
                    # Use the local timezone for today, not UTC
                    local_now = datetime.datetime.now().astimezone()
                    
                    # FIXED: Use the original event's timezone, not local timezone
                    original_timezone = event.start_time.tzinfo

                    # Get the time component from the original event
                    event_time = event.start_time.time()
                    
                    # Debug: Log the original event details
                    logger.debug(
                        f"Processing recurring event '{event.summary}': "
                        f"Original start_time: {event.start_time} "
                        f"(timezone: {original_timezone}), "
                        f"extracted time: {event_time}"
                    )
                    
                    # Special handling for events that might have been rescheduled
                    # If this event has a RECURRENCE-ID, it might be a moved/rescheduled event
                    if hasattr(event, 'is_modified_instance') and event.is_modified_instance:
                        logger.debug(
                            f"Event '{event.summary}' is a modified instance "
                            f"(RECURRENCE-ID: {getattr(event, 'recurrence_id', 'N/A')}). "
                            f"This might be a rescheduled event - checking for today's occurrence with different times."
                        )

                    # FIXED: Create today's occurrence using utility function for proper timezone handling
                    today_date = local_now.astimezone(original_timezone).date()
                    today_occurrence = _create_timezone_aware_datetime(
                        today_date, event_time, original_timezone
                    )

                    # Create tomorrow's occurrence using utility function
                    tomorrow_date = today_date + datetime.timedelta(days=1)
                    tomorrow_occurrence = _create_timezone_aware_datetime(
                        tomorrow_date, event_time, original_timezone
                    )

                    # Calculate time until these occurrences
                    time_until_today = (
                        today_occurrence - local_now
                    ).total_seconds() / 60
                    time_until_tomorrow = (
                        tomorrow_occurrence - local_now
                    ).total_seconds() / 60

                    logger.debug(
                        f"Possible occurrence today at {today_occurrence} "
                        f"(local equivalent: {today_occurrence.astimezone(local_now.tzinfo)}), "
                        f"time until: {time_until_today:.2f} min"
                    )
                    logger.debug(
                        f"Possible occurrence tomorrow at {tomorrow_occurrence} "
                        f"(local equivalent: {tomorrow_occurrence.astimezone(local_now.tzinfo)}), "
                        f"time until: {time_until_tomorrow:.2f} min"
                    )

                    # Use today's occurrence if it's in the future
                    if today_occurrence > local_now:
                        time_until_event = time_until_today
                        logger.debug(
                            f"Adjusted recurring event '{event.summary}' to today's "
                            f"occurrence: {time_until_event:.2f} min until start"
                        )
                    # Otherwise use tomorrow's occurrence if it's within our notification window
                    elif (
                        tomorrow_occurrence > local_now
                        and time_until_tomorrow <= max(self.notification_intervals) + 60
                    ):
                        # Add 60 minutes buffer to catch events that might need notification soon
                        time_until_event = time_until_tomorrow
                        logger.debug(
                            f"Adjusted recurring event '{event.summary}' to tomorrow's "
                            f"occurrence: {time_until_event:.2f} min until start"
                        )
                    else:
                        # Skip this event if both occurrences are in the past or too far in the future
                        if today_occurrence <= local_now:
                            logger.debug(
                                f"Today's occurrence for '{event.summary}' already passed "
                                f"at {today_occurrence} (local time: {today_occurrence.astimezone(local_now.tzinfo)}), "
                                f"checking tomorrow"
                            )
                        if (
                            tomorrow_occurrence <= local_now
                            or time_until_tomorrow
                            > max(self.notification_intervals) + 60
                        ):
                            logger.debug(
                                f"Tomorrow's occurrence for '{event.summary}' is either "
                                f"in the past or too far in the future, skipping"
                            )
                        continue
                except Exception as e:
                    logger.error(f"Error calculating recurring event time: {e}")
                    # Skip this event if we can't determine a reasonable time
                    continue

            # Skip events that are too far in the future
            if time_until_event > max(self.notification_intervals) + 1:
                # Only log for events within notification range + 1 minute buffer
                continue

            # Log events in the past but process them anyway in case they're recurring events
            # that should be happening today but have an old start_time
            if time_until_event < 0:
                logger.debug(
                    f"Event '{event.summary}' appears to have already started "
                    f"(time_until_event={time_until_event:.2f}), but processing "
                    f"anyway in case it's a recurring event"
                )
            else:
                logger.debug(
                    f"Event '{event.summary}' (ID: {event_id}): "
                    f"{time_until_event:.2f} minutes until start"
                )

            # Check each notification interval
            for interval in self.notification_intervals:
                self._check_notification_interval(
                    event, interval, time_until_event, now
                )

            # Check if we need to open URL (1 minute before event)
            if (
                self.auto_open_urls
                and 0.5 <= time_until_event <= 1.3
                and event.has_url_location()
            ):
                url = event.get_url()
                if url and f"{event_id}_url_opened" not in self.notified_events:
                    logger.info(
                        f"Time to open URL for event '{event.summary}' "
                        f"({time_until_event:.2f} minutes)"
                    )
                    self._schedule_url_open(url, event)
                    self.notified_events[f"{event_id}_url_opened"] = now

        # Clean up old notifications (older than 24 hours)
        self._cleanup_old_notifications(now)

    def _cleanup_old_notifications(self, now: datetime.datetime):
        """Remove old notification records (older than 24 hours)."""
        to_remove = []
        for key, notify_time in self.notified_events.items():
            if (now - notify_time).total_seconds() > 86400:  # 24 hours in seconds
                to_remove.append(key)

        for key in to_remove:
            del self.notified_events[key]

    def _show_notification(self, event: CalendarEvent, minutes_before: int):
        """Show desktop notification for an event.

        Args:
            event: Calendar event to notify about
            minutes_before: Minutes before event start
        """
        try:
            title = (
                f"Meeting in {minutes_before} minute{'s' if minutes_before > 1 else ''}"
            )
            message = f"{event.summary}"

            if event.location:
                message += f"\nLocation: {event.location}"

            # Show platform-specific desktop notification
            success = False

            # Try platform-specific method first
            if self.platform == "Darwin":  # macOS
                success = self._show_macos_notification(title, message)

            # Fall back to plyer if platform-specific method failed or for other platforms
            if not success:
                try:
                    from plyer import notification

                    notification.notify(
                        title=title,
                        message=message,
                        app_name="Calendar Notifications",
                        timeout=10,
                    )
                    success = True
                    logger.debug(f"Used plyer notification for {self.platform}")
                except Exception as e:
                    logger.error(f"Error using plyer notification: {e}")

            # Play sound if enabled
            if self.sound_enabled and minutes_before in self.sounds:
                self._play_sound(self.sounds[minutes_before])

            logger.info(
                f"Notification sent for event '{event.summary}' ({minutes_before} min)"
            )

        except Exception as e:
            logger.error(f"Error showing notification: {e}")
            logger.exception("Detailed notification error")

    def _show_macos_notification(self, title: str, message: str) -> bool:
        """Show macOS notification using osascript.

        Args:
            title: Notification title
            message: Notification message

        Returns:
            bool: Whether the notification was successfully shown
        """
        try:
            # Escape double quotes in the message and title for AppleScript
            title = title.replace('"', '\\"')
            message = message.replace('"', '\\"')

            # Create AppleScript command to show notification
            apple_script = f'display notification "{message}" with title "{title}"'

            # Run the AppleScript command
            cmd = ["osascript", "-e", apple_script]
            subprocess.run(cmd, check=True, capture_output=True)

            logger.debug(f"macOS notification sent: {title} - {message}")
            return True
        except Exception as e:
            logger.error(f"Error showing macOS notification: {e}")
            logger.exception("Detailed macOS notification error")
            return False

    def _play_sound(self, sound_file: str):
        """Play notification sound.

        Args:
            sound_file: Path to sound file to play
        """
        try:
            logger.debug(f"Attempting to play sound: {sound_file}")
            if os.path.exists(sound_file):
                logger.info(f"Playing notification sound: {sound_file}")
                wave_obj = sa.WaveObject.from_wave_file(sound_file)
                wave_obj.play()
                # Non-blocking, let it play in background
            else:
                logger.error(f"Sound file not found: {sound_file}")
        except Exception as e:
            logger.error(f"Error playing sound: {e}")
            logger.exception("Detailed sound playback error")

    def _schedule_url_open(self, url: str, event: CalendarEvent):
        """Schedule opening URL in browser.

        Args:
            url: URL to open
            event: Calendar event with the URL
        """

        def url_opener():
            try:
                logger.info(f"Opening URL for event '{event.summary}': {url}")
                webbrowser.open(url)
            except Exception as e:
                logger.error(f"Error opening URL: {e}")

        # Run in separate thread to avoid blocking
        self._url_opener_thread = threading.Thread(target=url_opener)
        self._url_opener_thread.daemon = True
        self._url_opener_thread.start()

    def stop(self):
        """Stop notification manager."""
        self._stop_flag.set()
        if self._url_opener_thread and self._url_opener_thread.is_alive():
            self._url_opener_thread.join(timeout=1.0)

    def _check_notification_interval(self, event, interval, time_until_event, now):
        """Check if an event needs notification for a specific interval.

        Args:
            event: Calendar event to check
            interval: Notification interval in minutes
            time_until_event: Minutes until event start
            now: Current datetime

        Returns:
            bool: Whether notification was sent
        """
        event_id = event.uid
        interval_id = f"{event_id}_{interval}"

        # Use a wider window to avoid missing notifications with per-minute checks
        window = 0.5

        # Log detailed timing information
        logger.debug(
            f"  Checking {interval} minute notification: "
            f"range [{interval-window:.2f} - {interval+window:.2f}], "
            f"current: {time_until_event:.2f}"
        )

        # If time until event is close to notification interval and not already notified
        if (interval - window) <= time_until_event <= (
            interval + window
        ) and interval_id not in self.notified_events:
            logger.info(
                f"Event '{event.summary}' trigger time={time_until_event:.2f} minutes, "
                f"sending {interval} minute notification"
            )
            self._show_notification(event, interval)
            self.notified_events[interval_id] = now
            return True
        elif interval_id in self.notified_events:
            logger.debug(f"  Notification for {interval} minutes already sent")
        else:
            logger.debug(f"  Not in notification time range for {interval} minutes")

        return False
