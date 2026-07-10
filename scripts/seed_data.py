"""
Seeding script for the Football Virtual Waiting Room.

Creates all 6 football events and their corresponding empty Statistics items
so every event in the frontend catalog is immediately usable.

Events match the EVENTS_CATALOG in frontend/app.js exactly.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from common.constants import (
    ENTITY_EVENT,
    ENTITY_STATS,
    EVENT_OPEN,
    EVENT_PREFIX,
    METADATA_SK,
    STATS_SK,
    TABLE_NAME,
)
from common.utils import utc_now_iso

# ---------------------------------------------------------------------------
# All 6 events — must match EVENTS_CATALOG in frontend/app.js exactly
# ---------------------------------------------------------------------------
EVENTS = [
    {
        "eventId": "1001",
        "matchName": "Manchester United vs Liverpool",
        "stadium": "Old Trafford",
        "capacity": 50000,
        "startTime": "2026-07-12T15:00:00Z",
    },
    {
        "eventId": "1002",
        "matchName": "Portugal vs Argentina",
        "stadium": "Estádio da Luz",
        "capacity": 65000,
        "startTime": "2026-07-15T20:00:00Z",
    },
    {
        "eventId": "1003",
        "matchName": "Real Madrid vs Barcelona",
        "stadium": "Santiago Bernabéu",
        "capacity": 81044,
        "startTime": "2026-07-18T21:00:00Z",
    },
    {
        "eventId": "1004",
        "matchName": "Bayern Munich vs Dortmund",
        "stadium": "Allianz Arena",
        "capacity": 75000,
        "startTime": "2026-07-20T18:30:00Z",
    },
    {
        "eventId": "1005",
        "matchName": "PSG vs Marseille",
        "stadium": "Parc des Princes",
        "capacity": 47929,
        "startTime": "2026-07-22T21:00:00Z",
    },
    {
        "eventId": "1006",
        "matchName": "Chelsea vs Arsenal",
        "stadium": "Stamford Bridge",
        "capacity": 40343,
        "startTime": "2026-07-25T17:30:00Z",
    },
]


def seed_database() -> None:
    """Seed all 6 events and their stats items into DynamoDB."""
    print(f"Seeding table: {TABLE_NAME}")
    print(f"Events to seed: {len(EVENTS)}\n")

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)
    now = utc_now_iso()

    for evt in EVENTS:
        event_id = evt["eventId"]
        pk = f"{EVENT_PREFIX}{event_id}"

        event_item: dict[str, Any] = {
            "PK": pk,
            "SK": METADATA_SK,
            "entityType": ENTITY_EVENT,
            "eventId": event_id,
            "matchName": evt["matchName"],
            "stadium": evt["stadium"],
            "capacity": evt["capacity"],
            "startTime": evt["startTime"],
            "status": EVENT_OPEN,
            "createdAt": now,
            "updatedAt": now,
        }

        stats_item: dict[str, Any] = {
            "PK": pk,
            "SK": STATS_SK,
            "entityType": ENTITY_STATS,
            "eventId": event_id,
            "waitingUsers": 0,
            "admittedUsers": 0,
            "expiredUsers": 0,
            "cancelledUsers": 0,
            "completedUsers": 0,
            "closedUsers": 0,
            "totalUsers": 0,
            "avgWaitTime": 0,
            "currentlyServingPosition": "",
            "createdAt": now,
            "updatedAt": now,
        }

        try:
            table.put_item(Item=event_item)
            table.put_item(Item=stats_item)
            print(f"  ✅ {event_id} — {evt['matchName']}")
        except ClientError as exc:
            print(f"  ❌ {event_id} failed: {exc}", file=sys.stderr)
            sys.exit(1)

    print(f"\nAll {len(EVENTS)} events seeded successfully.")
    print("Every event is OPEN and accepting queue registrations.")


if __name__ == "__main__":
    seed_database()
