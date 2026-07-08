"""
Data models for the Football Virtual Waiting Room.

Provides dataclass representations of the six entity types stored in
the DynamoDB single-table design. These models handle serialization
to/from DynamoDB item dictionaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from common.constants import (
    ENTITY_EVENT,
    ENTITY_QUEUE,
    ENTITY_STATS,
    ENTITY_TOKEN,
    EVENT_PREFIX,
    GSI1PK,
    GSI1SK,
    GSI2PK,
    GSI2SK,
    GSI3PK,
    GSI3SK,
    METADATA_SK,
    QUEUE_PREFIX,
    QUEUE_POSITION_PAD_LENGTH,
    STATS_SK,
    TOKEN_PREFIX,
    USER_PREFIX,
)


# ============================================================================
# Event
# ============================================================================


@dataclass
class Event:
    """Represents a football match event."""

    event_id: str
    match_name: str
    stadium: str
    capacity: int
    start_time: str
    status: str
    created_at: str = ""
    updated_at: str = ""

    def to_item(self) -> dict[str, Any]:
        """Serialize to a DynamoDB item dictionary."""
        return {
            "PK": f"{EVENT_PREFIX}{self.event_id}",
            "SK": METADATA_SK,
            "entityType": ENTITY_EVENT,
            "eventId": self.event_id,
            "matchName": self.match_name,
            "stadium": self.stadium,
            "capacity": self.capacity,
            "startTime": self.start_time,
            "status": self.status,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_item(cls, item: dict[str, Any]) -> Event:
        """Deserialize from a DynamoDB item dictionary."""
        return cls(
            event_id=item.get("eventId", ""),
            match_name=item.get("matchName", ""),
            stadium=item.get("stadium", ""),
            capacity=int(item.get("capacity", 0)),
            start_time=item.get("startTime", ""),
            status=item.get("status", ""),
            created_at=item.get("createdAt", ""),
            updated_at=item.get("updatedAt", ""),
        )

    def to_api_response(self) -> dict[str, Any]:
        """Return the public-facing API representation."""
        return {
            "eventId": self.event_id,
            "matchName": self.match_name,
            "stadium": self.stadium,
            "capacity": self.capacity,
            "startTime": self.start_time,
            "status": self.status,
        }


# ============================================================================
# Queue Entry
# ============================================================================


@dataclass
class QueueEntry:
    """Represents a user's position in an event queue."""

    event_id: str
    user_id: str
    queue_position: int
    status: str
    join_time: str
    estimated_wait: int = 0
    admission_time: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_item(self) -> dict[str, Any]:
        """Serialize to a DynamoDB item dictionary."""
        padded_position = str(self.queue_position).zfill(QUEUE_POSITION_PAD_LENGTH)
        return {
            "PK": f"{EVENT_PREFIX}{self.event_id}",
            "SK": f"{QUEUE_PREFIX}{padded_position}",
            "entityType": ENTITY_QUEUE,
            "eventId": self.event_id,
            "userId": self.user_id,
            "queuePosition": self.queue_position,
            "status": self.status,
            "joinTime": self.join_time,
            "estimatedWait": self.estimated_wait,
            "admissionTime": self.admission_time,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            # GSI1 — User Queue Lookup
            GSI1PK: f"{USER_PREFIX}{self.user_id}",
            GSI1SK: f"{EVENT_PREFIX}{self.event_id}",
            # GSI3 — Admin Queue View (status-based sort)
            GSI3PK: f"{EVENT_PREFIX}{self.event_id}",
            GSI3SK: f"STATUS#{self.status}#{padded_position}",
        }

    @classmethod
    def from_item(cls, item: dict[str, Any]) -> QueueEntry:
        """Deserialize from a DynamoDB item dictionary."""
        return cls(
            event_id=item.get("eventId", ""),
            user_id=item.get("userId", ""),
            queue_position=int(item.get("queuePosition", 0)),
            status=item.get("status", ""),
            join_time=item.get("joinTime", ""),
            estimated_wait=int(item.get("estimatedWait", 0)),
            admission_time=item.get("admissionTime", ""),
            created_at=item.get("createdAt", ""),
            updated_at=item.get("updatedAt", ""),
        )

    def to_api_response(self) -> dict[str, Any]:
        """Return the public-facing API representation."""
        response: dict[str, Any] = {
            "eventId": self.event_id,
            "userId": self.user_id,
            "queuePosition": self.queue_position,
            "status": self.status,
            "estimatedWaitMinutes": self.estimated_wait,
        }
        if self.admission_time:
            response["admissionTime"] = self.admission_time
        return response


# ============================================================================
# Admission Token
# ============================================================================


@dataclass
class AdmissionToken:
    """Represents a temporary admission credential."""

    token_id: str
    user_id: str
    event_id: str
    status: str
    expires_at: int  # Unix epoch timestamp
    created_at: str = ""

    def to_item(self) -> dict[str, Any]:
        """Serialize to a DynamoDB item dictionary."""
        return {
            "PK": f"{TOKEN_PREFIX}{self.token_id}",
            "SK": METADATA_SK,
            "entityType": ENTITY_TOKEN,
            "tokenId": self.token_id,
            "userId": self.user_id,
            "eventId": self.event_id,
            "status": self.status,
            "expiresAt": self.expires_at,
            "ttl": self.expires_at,
            "createdAt": self.created_at,
            # GSI2 — Token Lookup
            GSI2PK: f"{TOKEN_PREFIX}{self.token_id}",
            GSI2SK: f"STATUS#{self.status}",
        }

    @classmethod
    def from_item(cls, item: dict[str, Any]) -> AdmissionToken:
        """Deserialize from a DynamoDB item dictionary."""
        return cls(
            token_id=item.get("tokenId", ""),
            user_id=item.get("userId", ""),
            event_id=item.get("eventId", ""),
            status=item.get("status", ""),
            expires_at=int(item.get("expiresAt", 0)),
            created_at=item.get("createdAt", ""),
        )

    def to_api_response(self) -> dict[str, Any]:
        """Return the public-facing API representation."""
        return {
            "tokenId": self.token_id,
            "userId": self.user_id,
            "eventId": self.event_id,
            "status": self.status,
            "expiresAt": self.expires_at,
        }


# ============================================================================
# Queue Statistics
# ============================================================================


@dataclass
class QueueStats:
    """Aggregate counters for an event queue."""

    event_id: str
    waiting_users: int = 0
    admitted_users: int = 0
    expired_users: int = 0
    cancelled_users: int = 0
    completed_users: int = 0
    total_users: int = 0
    avg_wait_time: int = 0

    def to_item(self) -> dict[str, Any]:
        """Serialize to a DynamoDB item dictionary."""
        return {
            "PK": f"{EVENT_PREFIX}{self.event_id}",
            "SK": STATS_SK,
            "entityType": ENTITY_STATS,
            "eventId": self.event_id,
            "waitingUsers": self.waiting_users,
            "admittedUsers": self.admitted_users,
            "expiredUsers": self.expired_users,
            "cancelledUsers": self.cancelled_users,
            "completedUsers": self.completed_users,
            "totalUsers": self.total_users,
            "avgWaitTime": self.avg_wait_time,
        }

    @classmethod
    def from_item(cls, item: dict[str, Any]) -> QueueStats:
        """Deserialize from a DynamoDB item dictionary."""
        return cls(
            event_id=item.get("eventId", ""),
            waiting_users=int(item.get("waitingUsers", 0)),
            admitted_users=int(item.get("admittedUsers", 0)),
            expired_users=int(item.get("expiredUsers", 0)),
            cancelled_users=int(item.get("cancelledUsers", 0)),
            completed_users=int(item.get("completedUsers", 0)),
            total_users=int(item.get("totalUsers", 0)),
            avg_wait_time=int(item.get("avgWaitTime", 0)),
        )

    def to_api_response(self) -> dict[str, Any]:
        """Return the public-facing API representation."""
        return {
            "eventId": self.event_id,
            "waitingUsers": self.waiting_users,
            "admittedUsers": self.admitted_users,
            "expiredUsers": self.expired_users,
            "cancelledUsers": self.cancelled_users,
            "completedUsers": self.completed_users,
            "totalUsers": self.total_users,
            "averageWaitMinutes": self.avg_wait_time,
        }
