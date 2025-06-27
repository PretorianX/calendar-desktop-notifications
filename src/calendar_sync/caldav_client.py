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
            logger.debug(f"Date range in UTC: {start_date.astimezone(pytz.UTC)} to {end_date.astimezone(pytz.UTC)}")
            caldav_events = self.calendar.date_search(
                start=start_date,
                end=end_date,
                expand=True  # Expand recurring events
            )
            
            logger.info(f"Found {len(caldav_events)} events in the date range")

            # Convert to our event format
            for caldav_event in caldav_events:
                vobj = caldav_event.vobject_instance
                
                # Handle VCALENDAR with multiple VEVENT components (e.g., recurring event modifications)
                vevent_list = []
                if hasattr(vobj, 'vevent_list') and vobj.vevent_list:
                    vevent_list = vobj.vevent_list
                    logger.debug(f"Found VCALENDAR with {len(vevent_list)} VEVENT components")
                elif hasattr(vobj, 'vevent'):
                    vevent_list = [vobj.vevent]
                else:
                    logger.warning("No VEVENT found in VCALENDAR")
                    continue
                
                # Process each VEVENT component
                for event_data in vevent_list:
                    # Debug: Log all available attributes on the event
                    logger.debug(f"Event attributes: {[attr for attr in dir(event_data) if not attr.startswith('_')]}")
                    
                    # Debug: Log key iCalendar fields for this event
                    logger.debug(f"Event UID: {event_data.uid.value if hasattr(event_data, 'uid') else 'N/A'}")
                    logger.debug(f"Event Summary: {event_data.summary.value if hasattr(event_data, 'summary') else 'N/A'}")
                    logger.debug(f"Event DTSTART: {event_data.dtstart.value if hasattr(event_data, 'dtstart') else 'N/A'}")
                    logger.debug(f"Event DTEND: {event_data.dtend.value if hasattr(event_data, 'dtend') else 'N/A'}")
                    logger.debug(f"Event RECURRENCE-ID: {event_data.recurrence_id.value if hasattr(event_data, 'recurrence_id') else 'None'}")
                    logger.debug(f"Event RRULE: {event_data.rrule.value if hasattr(event_data, 'rrule') else 'None'}")
                    logger.debug(f"Event SEQUENCE: {event_data.sequence.value if hasattr(event_data, 'sequence') else 'N/A'}")

                    # Get event UID
                    uid = str(event_data.uid.value)

                    # Debug: Check for RECURRENCE-ID which might override DTSTART for modified recurring events
                    if hasattr(event_data, 'recurrence_id'):
                        logger.debug(
                            f"Event {uid} has RECURRENCE-ID: {event_data.recurrence_id.value} "
                            f"(type: {type(event_data.recurrence_id.value)}, "
                            f"tzinfo: {getattr(event_data.recurrence_id.value, 'tzinfo', 'N/A')})"
                        )

                    # Get summary (title)
                    summary = (
                        str(event_data.summary.value)
                        if hasattr(event_data, "summary")
                        else "No Title"
                    )

                    # Get start time
                    start_time = event_data.dtstart.value
                    
                    # Debug: Log the raw datetime value and its timezone
                    logger.debug(
                        f"Raw DTSTART value: {start_time} "
                        f"(type: {type(start_time)}, tzinfo: {getattr(start_time, 'tzinfo', 'N/A')})"
                    )
                    
                    # For modified recurring events, use RECURRENCE-ID as the actual start time
                    if hasattr(event_data, 'recurrence_id'):
                        try:
                            recurrence_id_time = event_data.recurrence_id.value
                            if isinstance(recurrence_id_time, datetime.datetime):
                                logger.debug(
                                    f"Event has RECURRENCE-ID: {recurrence_id_time}. "
                                    f"Using RECURRENCE-ID as actual start time instead of DTSTART."
                                )
                                start_time = recurrence_id_time
                            else:
                                logger.debug(f"RECURRENCE-ID is not a datetime object: {type(recurrence_id_time)}")
                        except (AttributeError, TypeError) as e:
                            logger.debug(f"Could not access RECURRENCE-ID value: {e}")
                    
                    if not isinstance(start_time, datetime.datetime):
                        # Convert date to datetime if needed
                        start_time = datetime.datetime.combine(
                            start_time, datetime.time.min, tzinfo=pytz.UTC
                        )
                    elif start_time.tzinfo is None:
                        # Add UTC timezone if naive
                        start_time = start_time.replace(tzinfo=pytz.UTC)

                    # Debug: Log the processed datetime value
                    logger.debug(
                        f"Processed DTSTART: {start_time} "
                        f"(tzinfo: {start_time.tzinfo})"
                    )

                    # Get end time - calculate from start time if this is a modified instance
                    if hasattr(event_data, "dtend"):
                        end_time = event_data.dtend.value
                        
                        # If we used RECURRENCE-ID for start time, calculate end time based on original duration
                        if hasattr(event_data, 'recurrence_id'):
                            original_start = event_data.dtstart.value
                            original_end = event_data.dtend.value
                            if (isinstance(original_start, datetime.datetime) and 
                                isinstance(original_end, datetime.datetime) and
                                isinstance(start_time, datetime.datetime)):
                                duration = original_end - original_start
                                end_time = start_time + duration
                                logger.debug(f"Calculated end time for modified instance: {end_time} (duration: {duration})")
                            else:
                                logger.debug("Could not calculate duration for modified instance - using original end time")
                        
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
                    
                    # Add metadata for recurring event handling
                    # Events with RECURRENCE-ID are modified instances and should not be treated as recurring
                    if hasattr(event_data, 'recurrence_id'):
                        event.is_modified_instance = True
                        event.recurrence_id = event_data.recurrence_id.value
                        logger.debug(f"Event {uid} is a modified instance of a recurring event (RECURRENCE-ID: {event.recurrence_id})")
                    else:
                        event.is_modified_instance = False

                    events.append(event)

            # Filter out events that are more than 1 day in the past
            # This removes old instances of recurring events that might appear in the same VCALENDAR
            now = datetime.datetime.now().astimezone()
            cutoff_time = now - datetime.timedelta(hours=24)
            
            filtered_events = []
            for event in events:
                if event.start_time > cutoff_time:
                    filtered_events.append(event)
                else:
                    logger.debug(f"Filtering out old event instance: {event.summary} at {event.start_time} (more than 24h in the past)")
            
            # Sort events by start time
            filtered_events.sort(key=lambda e: e.start_time)
            
            logger.info(f"Filtered from {len(events)} to {len(filtered_events)} events after removing old instances")

            return filtered_events

        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return []
