"""CalDAV client for calendar synchronization."""

import datetime
import logging
from typing import List, Optional

import caldav
import pytz

logger = logging.getLogger(__name__)


class CalendarEvent:
    """Represents a calendar event."""

    def __init__(
        self,
        uid: str,
        summary: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        location: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """Initialize a calendar event."""
        self.uid = uid
        self.summary = summary
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.description = description

    def __str__(self) -> str:
        """Return string representation of the event."""
        return (
            f"{self.summary} ({self.start_time:%Y-%m-%d %H:%M} - {self.end_time:%H:%M})"
        )

    def has_url_location(self) -> bool:
        """Check if the event location contains a URL."""
        if not self.location:
            return False
        location = self.location.strip().lower()
        return location.startswith(("http://", "https://", "www."))

    def get_url(self) -> Optional[str]:
        """Extract URL from location if present."""
        if not self.has_url_location():
            return None

        location = self.location.strip()
        if location.lower().startswith("www."):
            return "https://" + location
        return location


class CalDAVClient:
    """Client for CalDAV calendar operations."""

    def __init__(
        self, url: str, username: str, password: str, calendar_name: str = None
    ):
        """Initialize CalDAV client."""
        # Store original URL without trailing slash for consistency
        self.url = url.rstrip("/") if url else url
        self.username = username
        self.password = password
        self.calendar_name = calendar_name
        self.client = None
        self.calendar = None

    def connect(self) -> bool:
        """Connect to CalDAV server and select calendar."""
        try:
            logger.info(f"Connecting to CalDAV server with URL: {self.url}")
            self.client = caldav.DAVClient(
                url=self.url, username=self.username, password=self.password
            )

            principal = self.client.principal()
            calendars = principal.calendars()

            if not calendars:
                logger.error("No calendars found")
                return False

            if self.calendar_name:
                # Find specific calendar by name
                for cal in calendars:
                    if cal.name == self.calendar_name:
                        self.calendar = cal
                        break

                if not self.calendar:
                    logger.error(f"Calendar '{self.calendar_name}' not found")
                    return False
            else:
                # Use the first calendar if name not specified
                self.calendar = calendars[0]
                logger.info(f"Using calendar: {self.calendar.name}")

            return True

        except Exception as e:
            logger.error(f"Error connecting to CalDAV server: {e}")
            return False

    def get_events(
        self, start_date: datetime.datetime, end_date: datetime.datetime
    ) -> List[CalendarEvent]:
        """Get calendar events between start and end dates."""
        if not self.calendar:
            if not self.connect():
                return []

        events = []
        try:
            # Get events from CalDAV using date_search for reliable filtering
            logger.info(f"Fetching events from {start_date} to {end_date}")
            caldav_events = self.calendar.date_search(
                start=start_date,
                end=end_date,
                expand=True  # Expand recurring events
            )
            
            logger.info(f"Found {len(caldav_events)} events in the date range")

            # Convert to our event format
            for caldav_event in caldav_events:
                event_data = caldav_event.vobject_instance.vevent

                # Get event UID
                uid = str(event_data.uid.value)

                # Get summary (title)
                summary = (
                    str(event_data.summary.value)
                    if hasattr(event_data, "summary")
                    else "No Title"
                )

                # Get start time
                start_time = event_data.dtstart.value
                if not isinstance(start_time, datetime.datetime):
                    # Convert date to datetime if needed
                    start_time = datetime.datetime.combine(
                        start_time, datetime.time.min, tzinfo=pytz.UTC
                    )
                elif start_time.tzinfo is None:
                    # Add UTC timezone if naive
                    start_time = start_time.replace(tzinfo=pytz.UTC)

                # Get end time
                if hasattr(event_data, "dtend"):
                    end_time = event_data.dtend.value
                    if not isinstance(end_time, datetime.datetime):
                        # Convert date to datetime if needed
                        end_time = datetime.datetime.combine(
                            end_time, datetime.time.min, tzinfo=pytz.UTC
                        )
                    elif end_time.tzinfo is None:
                        # Add UTC timezone if naive
                        end_time = end_time.replace(tzinfo=pytz.UTC)
                else:
                    # Default to start time + 1 hour if no end time
                    end_time = start_time + datetime.timedelta(hours=1)

                # Get location if available
                location = None
                if hasattr(event_data, "location"):
                    location = str(event_data.location.value)

                # Get description if available
                description = None
                if hasattr(event_data, "description"):
                    description = str(event_data.description.value)

                # Create event object
                event = CalendarEvent(
                    uid=uid,
                    summary=summary,
                    start_time=start_time,
                    end_time=end_time,
                    location=location,
                    description=description,
                )

                events.append(event)

            # Sort events by start time
            events.sort(key=lambda e: e.start_time)

            return events

        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return []
