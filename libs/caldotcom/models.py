"""Pydantic models for Cal.com domain entities."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict


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
