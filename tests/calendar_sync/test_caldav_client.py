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
