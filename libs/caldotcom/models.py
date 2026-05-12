"""Pydantic models for Cal.com domain entities."""

from datetime import datetime
from typing import Any, Literal, Optional

import orjson
from pydantic import BaseModel, ConfigDict, model_validator


class EventType(BaseModel):
    """Cal.com EventType model."""

    id: int
    slug: str


class BookingHost(BaseModel):
    """Cal.com booking host participant."""

    id: int
    name: str
    email: str
    displayEmail: str
    username: str
    timeZone: str


class BookingAttendee(BaseModel):
    """Cal.com booking attendee participant."""

    name: str
    email: str
    displayEmail: str
    timeZone: str
    absent: bool
    language: Optional[str] = None
    phoneNumber: Optional[str] = None


class RecordingItem(BaseModel):
    """Cal.com recording metadata."""

    id: str
    roomName: str
    startTs: int
    status: str
    duration: int
    shareToken: str
    maxParticipants: Optional[int] = None
    downloadLink: Optional[str] = None
    error: Optional[str] = None


class Transcript(BaseModel):
    """Cal.com transcript reference."""

    urls: list[str]


class Booking(BaseModel):
    """Cal.com BookingOutput_2024_08_13 model."""

    id: int
    uid: str
    title: str
    description: str
    status: Literal["cancelled", "accepted", "rejected", "pending"]
    start: datetime
    end: datetime
    duration: int
    eventType: EventType
    location: str
    absentHost: bool
    createdAt: datetime
    updatedAt: datetime
    hosts: list[BookingHost]
    attendees: list[BookingAttendee]
    bookingFieldsResponses: dict[str, Any]
    # Optional fields
    cancellationReason: Optional[str] = None
    cancelledByEmail: Optional[str] = None
    reschedulingReason: Optional[str] = None
    rescheduledByEmail: Optional[str] = None
    rescheduledFromUid: Optional[str] = None
    rescheduledToUid: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    rating: Optional[int] = None
    icsUid: Optional[str] = None
    guests: Optional[list[str]] = None

    model_config = ConfigDict(extra="allow")

    def get_booking_id(self) -> str:
        """Return the booking ID (uid)."""
        return self.uid


class Webhook(BaseModel):
    """Cal.com webhook envelope.

    Cal.com delivers webhooks wrapped in ``{"body": "<json string>"}``. The
    inner payload has two shapes depending on ``triggerEvent``:

    - Booking events (``BOOKING_CREATED``, ``BOOKING_RESCHEDULED``,
      ``BOOKING_CANCELLED``, ``BOOKING_NO_SHOW_UPDATED``, ``PING``) wrap booking
      fields under a nested ``payload`` key.
    - Meeting events (``MEETING_STARTED``, ``MEETING_ENDED``) put booking
      fields flat at the top level alongside ``triggerEvent``.

    The validator normalizes both shapes so downstream consumers see a uniform
    ``triggerEvent`` / ``createdAt`` / ``payload`` structure.
    """

    model_config = ConfigDict(extra="allow")

    triggerEvent: str
    createdAt: datetime
    payload: dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def _unwrap_and_normalize(cls, data: Any) -> Any:
        if isinstance(data, dict) and "body" in data and "triggerEvent" not in data:
            body = data["body"]
            if isinstance(body, (bytes, bytearray, memoryview)):
                data = orjson.loads(body)
            elif isinstance(body, str):
                data = orjson.loads(body)

        if isinstance(data, dict) and "triggerEvent" in data and "payload" not in data:
            trigger = data.get("triggerEvent")
            created = data.get("createdAt")
            payload = {
                k: v for k, v in data.items() if k not in ("triggerEvent", "createdAt")
            }
            data = {
                "triggerEvent": trigger,
                "createdAt": created,
                "payload": payload,
            }

        return data
