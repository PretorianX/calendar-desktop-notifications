"""Tests for the CalDAVClient class."""

import datetime
from unittest.mock import MagicMock, patch

import pytz

from src.calendar_sync.caldav_client import CalDAVClient, CalendarEvent


class TestCalendarEvent:
    """Tests for the CalendarEvent class."""

    def test_has_url_location(self):
        """Test has_url_location method."""
        # Test with URL locations
        event_http = CalendarEvent(
            uid="1",
            summary="Test Event",
            start_time=datetime.datetime.now(pytz.UTC),
            end_time=datetime.datetime.now(pytz.UTC),
            location="http://example.com",
        )
        assert event_http.has_url_location() is True

        event_https = CalendarEvent(
            uid="2",
            summary="Test Event",
            start_time=datetime.datetime.now(pytz.UTC),
            end_time=datetime.datetime.now(pytz.UTC),
            location="https://example.com",
        )
        assert event_https.has_url_location() is True

        event_www = CalendarEvent(
            uid="3",
            summary="Test Event",
            start_time=datetime.datetime.now(pytz.UTC),
            end_time=datetime.datetime.now(pytz.UTC),
            location="www.example.com",
        )
        assert event_www.has_url_location() is True

        # Test with non-URL locations
        event_nonurl = CalendarEvent(
            uid="4",
            summary="Test Event",
            start_time=datetime.datetime.now(pytz.UTC),
            end_time=datetime.datetime.now(pytz.UTC),
            location="Conference Room 1",
        )
        assert event_nonurl.has_url_location() is False

        # Test with None location
        event_none = CalendarEvent(
            uid="5",
            summary="Test Event",
            start_time=datetime.datetime.now(pytz.UTC),
            end_time=datetime.datetime.now(pytz.UTC),
            location=None,
        )
        assert event_none.has_url_location() is False

    def test_get_url(self):
        """Test get_url method."""
        # Test with https URL
        event_https = CalendarEvent(
            uid="1",
            summary="Test Event",
            start_time=datetime.datetime.now(pytz.UTC),
            end_time=datetime.datetime.now(pytz.UTC),
            location="https://example.com",
        )
        assert event_https.get_url() == "https://example.com"

        # Test with www URL
        event_www = CalendarEvent(
            uid="2",
            summary="Test Event",
            start_time=datetime.datetime.now(pytz.UTC),
            end_time=datetime.datetime.now(pytz.UTC),
            location="www.example.com",
        )
        assert event_www.get_url() == "https://www.example.com"

        # Test with non-URL
        event_nonurl = CalendarEvent(
            uid="3",
            summary="Test Event",
            start_time=datetime.datetime.now(pytz.UTC),
            end_time=datetime.datetime.now(pytz.UTC),
            location="Conference Room 1",
        )
        assert event_nonurl.get_url() is None


class TestCalDAVClient:
    """Tests for the CalDAVClient class."""

    @patch("caldav.DAVClient")
    def test_connect_success(self, mock_dav_client):
        """Test successful connection to CalDAV server."""
        # Mock setup
        mock_principal = MagicMock()
        mock_calendar = MagicMock()
        mock_calendar.name = "Test Calendar"

        mock_principal.calendars.return_value = [mock_calendar]
        mock_dav_client.return_value.principal.return_value = mock_principal

        # Create client and connect
        client = CalDAVClient(
            url="https://example.com/caldav",
            username="test",
            password="test123",
            calendar_name="Test Calendar",
        )

        result = client.connect()

        # Verify
        assert result is True
        assert client.calendar == mock_calendar
        mock_dav_client.assert_called_once_with(
            url="https://example.com/caldav", username="test", password="test123"
        )

    @patch("caldav.DAVClient")
    def test_connect_no_calendars(self, mock_dav_client):
        """Test connection failure when no calendars found."""
        # Mock setup
        mock_principal = MagicMock()
        mock_principal.calendars.return_value = []
        mock_dav_client.return_value.principal.return_value = mock_principal

        # Create client and connect
        client = CalDAVClient(
            url="https://example.com/caldav", username="test", password="test123"
        )

        result = client.connect()

        # Verify
        assert result is False
        assert client.calendar is None

    @patch("caldav.DAVClient")
    def test_connect_calendar_not_found(self, mock_dav_client):
        """Test connection failure when specific calendar not found."""
        # Mock setup
        mock_principal = MagicMock()
        mock_calendar = MagicMock()
        mock_calendar.name = "Other Calendar"

        mock_principal.calendars.return_value = [mock_calendar]
        mock_dav_client.return_value.principal.return_value = mock_principal

        # Create client and connect
        client = CalDAVClient(
            url="https://example.com/caldav",
            username="test",
            password="test123",
            calendar_name="Test Calendar",
        )

        result = client.connect()

        # Verify
        assert result is False
        assert client.calendar is None

    @patch("caldav.DAVClient")
    def test_get_events_uses_date_search_method(self, mock_dav_client):
        """Test that get_events uses the calendar.date_search method."""
        # Mock setup
        mock_principal = MagicMock()
        mock_calendar = MagicMock()
        mock_calendar.name = "Test Calendar"

        # Mock calendar events
        mock_event = MagicMock()
        mock_event.vobject_instance.vevent.uid.value = "test-uid"
        mock_event.vobject_instance.vevent.summary.value = "Test Event"

        # Setup start and end times with timezone
        start_time = datetime.datetime.now(pytz.UTC)
        mock_event.vobject_instance.vevent.dtstart.value = start_time

        end_time = start_time + datetime.timedelta(hours=1)
        mock_event.vobject_instance.vevent.dtend.value = end_time

        # Setup the date_search method return
        mock_calendar.date_search.return_value = [mock_event]

        # Setup the principal and calendar hierarchy
        mock_principal.calendars.return_value = [mock_calendar]
        mock_dav_client.return_value.principal.return_value = mock_principal

        # Create client, connect, and get events
        client = CalDAVClient(
            url="https://example.com/caldav",
            username="test",
            password="test123",
            calendar_name="Test Calendar",
        )

        client.connect()

        # Use today's date for searching
        today = datetime.datetime.now(pytz.UTC)
        tomorrow = today + datetime.timedelta(days=1)

        events = client.get_events(today, tomorrow)

        # Verify date_search was called with correct parameters
        mock_calendar.date_search.assert_called_once_with(
            start=today, end=tomorrow, expand=True
        )

        # Verify the returned events
        assert len(events) == 1
        assert events[0].uid == "test-uid"
        assert events[0].summary == "Test Event"

    @patch("caldav.DAVClient")
    def test_get_events_marks_declined_for_current_user(self, mock_dav_client):
        """Events declined by the current user should be marked as declined."""
        # Mock setup
        mock_principal = MagicMock()
        mock_calendar = MagicMock()
        mock_calendar.name = "Test Calendar"

        mock_event = MagicMock()
        mock_event.vobject_instance.vevent.uid.value = "declined-uid"
        mock_event.vobject_instance.vevent.summary.value = "Declined Event"

        start_time = datetime.datetime.now(pytz.UTC)
        end_time = start_time + datetime.timedelta(hours=1)
        mock_event.vobject_instance.vevent.dtstart.value = start_time
        mock_event.vobject_instance.vevent.dtend.value = end_time

        attendee = MagicMock()
        attendee.value = "mailto:test@example.com"
        attendee.params = {"PARTSTAT": ["DECLINED"]}
        mock_event.vobject_instance.vevent.attendee_list = [attendee]

        mock_calendar.date_search.return_value = [mock_event]
        mock_principal.calendars.return_value = [mock_calendar]
        mock_dav_client.return_value.principal.return_value = mock_principal

        client = CalDAVClient(
            url="https://example.com/caldav",
            username="test@example.com",
            password="test123",
            calendar_name="Test Calendar",
        )
        client.connect()

        today = datetime.datetime.now(pytz.UTC)
        tomorrow = today + datetime.timedelta(days=1)
        events = client.get_events(today, tomorrow)

        assert len(events) == 1
        assert events[0].uid == "declined-uid"
        assert events[0].is_declined is True
        assert events[0].participation_status == "DECLINED"

    @patch("caldav.DAVClient")
    def test_get_events_with_timezone_aware_dates(self, mock_dav_client):
        """Test that get_events correctly handles timezone-aware dates."""
        # Mock setup
        mock_principal = MagicMock()
        mock_calendar = MagicMock()
        mock_calendar.name = "Test Calendar"

        # Mock calendar event with timezone-aware datetime
        mock_event = MagicMock()
        mock_event.vobject_instance.vevent.uid.value = (
            "7c7d0461-1bf3-458c-9fd2-81449b161736"
        )
        mock_event.vobject_instance.vevent.summary.value = "PM - Architect sync"

        # Create timezone-aware datetime for Europe/Athens timezone
        athens_tz = pytz.timezone("Europe/Athens")
        start_time = athens_tz.localize(datetime.datetime(2025, 6, 27, 15, 0, 0))
        end_time = athens_tz.localize(datetime.datetime(2025, 6, 27, 16, 0, 0))

        mock_event.vobject_instance.vevent.dtstart.value = start_time
        mock_event.vobject_instance.vevent.dtend.value = end_time

        # Add location and description
        mock_event.vobject_instance.vevent.location.value = (
            "https://meet.namecheap.net/spacemail-pm-architects"
        )
        mock_event.vobject_instance.vevent.description.value = (
            "https://jts.totest.chat:8443/spacemail-pm-architects"
        )

        # Setup the date_search method return
        mock_calendar.date_search.return_value = [mock_event]

        # Setup the principal and calendar hierarchy
        mock_principal.calendars.return_value = [mock_calendar]
        mock_dav_client.return_value.principal.return_value = mock_principal

        # Create client, connect, and get events
        client = CalDAVClient(
            url="https://example.com/caldav",
            username="test",
            password="test123",
            calendar_name="Test Calendar",
        )

        client.connect()

        # Use search dates
        search_start = datetime.datetime(2025, 6, 27, 0, 0, 0, tzinfo=pytz.UTC)
        search_end = datetime.datetime(2025, 6, 28, 0, 0, 0, tzinfo=pytz.UTC)

        events = client.get_events(search_start, search_end)

        # Verify the returned events have correct timezone information
        assert len(events) == 1
        event = events[0]
        assert event.uid == "7c7d0461-1bf3-458c-9fd2-81449b161736"
        assert event.summary == "PM - Architect sync"

        # Verify timezone is preserved (should be Athens time)
        assert event.start_time.tzinfo.zone == "Europe/Athens"
        assert event.end_time.tzinfo.zone == "Europe/Athens"

        # Verify actual times are correct
        assert event.start_time.hour == 15  # 3 PM Athens time
        assert event.end_time.hour == 16  # 4 PM Athens time

        assert event.location == "https://meet.namecheap.net/spacemail-pm-architects"
        assert (
            event.description == "https://jts.totest.chat:8443/spacemail-pm-architects"
        )

    @patch("caldav.DAVClient")
    def test_get_events_with_naive_dates_gets_utc_timezone(self, mock_dav_client):
        """Test that get_events correctly handles naive datetime objects by adding UTC timezone."""
        # Mock setup
        mock_principal = MagicMock()
        mock_calendar = MagicMock()
        mock_calendar.name = "Test Calendar"

        # Mock calendar event with naive datetime (no timezone info)
        mock_event = MagicMock()
        mock_event.vobject_instance.vevent.uid.value = "naive-event-uid"
        mock_event.vobject_instance.vevent.summary.value = "Naive Event"

        # Create naive datetime (no timezone)
        naive_start = datetime.datetime(2025, 6, 27, 15, 0, 0)
        naive_end = datetime.datetime(2025, 6, 27, 16, 0, 0)

        mock_event.vobject_instance.vevent.dtstart.value = naive_start
        mock_event.vobject_instance.vevent.dtend.value = naive_end

        # Setup the date_search method return
        mock_calendar.date_search.return_value = [mock_event]

        # Setup the principal and calendar hierarchy
        mock_principal.calendars.return_value = [mock_calendar]
        mock_dav_client.return_value.principal.return_value = mock_principal

        # Create client, connect, and get events
        client = CalDAVClient(
            url="https://example.com/caldav",
            username="test",
            password="test123",
            calendar_name="Test Calendar",
        )

        client.connect()

        # Use search dates
        search_start = datetime.datetime(2025, 6, 27, 0, 0, 0, tzinfo=pytz.UTC)
        search_end = datetime.datetime(2025, 6, 28, 0, 0, 0, tzinfo=pytz.UTC)

        events = client.get_events(search_start, search_end)

        # Verify the returned events have UTC timezone added
        assert len(events) == 1
        event = events[0]
        assert event.uid == "naive-event-uid"
        assert event.summary == "Naive Event"

        # Verify UTC timezone was added to naive datetimes
        assert event.start_time.tzinfo == pytz.UTC
        assert event.end_time.tzinfo == pytz.UTC

        # Verify actual times are preserved
        assert event.start_time.hour == 15
        assert event.end_time.hour == 16

    @patch("caldav.DAVClient")
    def test_parse_real_vcalendar_event(self, mock_dav_client):
        """Test parsing of a real VCALENDAR event to verify datetime handling."""
        # Mock setup
        mock_principal = MagicMock()
        mock_calendar = MagicMock()
        mock_calendar.name = "Test Calendar"

        # Mock calendar event with the exact data from the user's issue
        mock_event = MagicMock()
        mock_event.vobject_instance.vevent.uid.value = (
            "7c7d0461-1bf3-458c-9fd2-81449b161736"
        )
        mock_event.vobject_instance.vevent.summary.value = "PM - Architect sync"

        # Create timezone-aware datetime for Europe/Athens timezone exactly as it appears in the iCal
        # DTSTART;TZID=Europe/Athens:20250627T150000
        # DTEND;TZID=Europe/Athens:20250627T160000
        athens_tz = pytz.timezone("Europe/Athens")
        event_start = athens_tz.localize(datetime.datetime(2025, 6, 27, 15, 0, 0))
        event_end = athens_tz.localize(datetime.datetime(2025, 6, 27, 16, 0, 0))

        mock_event.vobject_instance.vevent.dtstart.value = event_start
        mock_event.vobject_instance.vevent.dtend.value = event_end

        # Add location and description from the real event
        mock_event.vobject_instance.vevent.location.value = (
            "https://meet.namecheap.net/spacemail-pm-architects"
        )
        mock_event.vobject_instance.vevent.description.value = (
            "https://jts.totest.chat:8443/spacemail-pm-architects"
        )

        # Make sure we have attributes for the optional fields
        mock_event.vobject_instance.vevent.__dict__["location"] = (
            mock_event.vobject_instance.vevent.location
        )
        mock_event.vobject_instance.vevent.__dict__["description"] = (
            mock_event.vobject_instance.vevent.description
        )

        # Setup the date_search method return
        mock_calendar.date_search.return_value = [mock_event]

        # Setup the principal and calendar hierarchy
        mock_principal.calendars.return_value = [mock_calendar]
        mock_dav_client.return_value.principal.return_value = mock_principal

        # Create client, connect, and get events
        client = CalDAVClient(
            url="https://example.com/caldav",
            username="test",
            password="test123",
            calendar_name="Test Calendar",
        )

        client.connect()

        # Use search dates that would include this event
        search_start = datetime.datetime(2025, 6, 27, 0, 0, 0, tzinfo=pytz.UTC)
        search_end = datetime.datetime(2025, 6, 28, 0, 0, 0, tzinfo=pytz.UTC)

        events = client.get_events(search_start, search_end)

        # Verify we got the event correctly parsed
        assert len(events) == 1
        event = events[0]

        # Verify the core event details
        assert event.uid == "7c7d0461-1bf3-458c-9fd2-81449b161736"
        assert event.summary == "PM - Architect sync"
        assert event.location == "https://meet.namecheap.net/spacemail-pm-architects"
        assert (
            event.description == "https://jts.totest.chat:8443/spacemail-pm-architects"
        )

        # Verify the datetime values are correct and preserve timezone
        # This should be 15:00 Athens time, NOT the creation time
        assert event.start_time == event_start
        assert event.end_time == event_end

        # Verify timezone is preserved
        assert event.start_time.tzinfo.zone == "Europe/Athens"
        assert event.end_time.tzinfo.zone == "Europe/Athens"

        # Verify the actual time values (not creation time)
        assert event.start_time.hour == 15  # 3 PM Athens time, NOT creation time
        assert event.start_time.minute == 0
        assert event.end_time.hour == 16  # 4 PM Athens time
        assert event.end_time.minute == 0

        # Verify the date
        assert event.start_time.year == 2025
        assert event.start_time.month == 6
        assert event.start_time.day == 27

    @patch("caldav.DAVClient")
    def test_timezone_preservation_for_recurring_events(self, mock_dav_client):
        """Test that recurring events preserve their original timezone when calculating today's occurrence."""
        # Mock setup
        mock_principal = MagicMock()
        mock_calendar = MagicMock()
        mock_calendar.name = "Test Calendar"

        # Mock calendar event that looks like a recurring event with Europe/Athens timezone
        # This simulates an event that was created in the past but recurs today
        mock_event = MagicMock()
        mock_event.vobject_instance.vevent.uid.value = "recurring-event-uid"
        mock_event.vobject_instance.vevent.summary.value = "Daily Standup"

        # Create an event that appears to be from yesterday but in Athens timezone
        athens_tz = pytz.timezone("Europe/Athens")
        yesterday = datetime.datetime.now(athens_tz) - datetime.timedelta(days=1)
        event_start = yesterday.replace(hour=15, minute=0, second=0, microsecond=0)
        event_end = event_start + datetime.timedelta(hours=1)

        mock_event.vobject_instance.vevent.dtstart.value = event_start
        mock_event.vobject_instance.vevent.dtend.value = event_end

        # Setup the date_search method return
        mock_calendar.date_search.return_value = [mock_event]

        # Setup the principal and calendar hierarchy
        mock_principal.calendars.return_value = [mock_calendar]
        mock_dav_client.return_value.principal.return_value = mock_principal

        # Create client, connect, and get events
        client = CalDAVClient(
            url="https://example.com/caldav",
            username="test",
            password="test123",
            calendar_name="Test Calendar",
        )

        client.connect()

        # Use search dates that would include this event
        search_start = datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=1)
        search_end = datetime.datetime.now(pytz.UTC) + datetime.timedelta(days=1)

        events = client.get_events(search_start, search_end)

        # Verify we got the event correctly parsed
        assert len(events) == 1
        event = events[0]

        # Verify the core event details
        assert event.uid == "recurring-event-uid"
        assert event.summary == "Daily Standup"

        # The key test: verify that the timezone is preserved from the original event
        # This should be Europe/Athens timezone, not the local system timezone
        assert event.start_time.tzinfo.zone == "Europe/Athens"
        assert event.end_time.tzinfo.zone == "Europe/Athens"

        # Verify the original time is preserved
        assert event.start_time.hour == 15  # 3 PM Athens time
        assert event.start_time.minute == 0
