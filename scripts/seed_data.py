"""
Seeding script for the Football Virtual Waiting Room.

Creates a default football event (Event ID: 1001) and its corresponding
empty Queue Statistics item in the DynamoDB table so that the application
is ready to accept registrations.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Add src directory to python path to access common module
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


def seed_database() -> None:
    """Seed the DynamoDB table with a default event and stats item."""
    print(f"Initializing seeding for table: {TABLE_NAME}...")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    now = utc_now_iso()
    event_id = "1001"
    event_pk = f"{EVENT_PREFIX}{event_id}"

    # 1. Default Event Item
    event_item: dict[str, Any] = {
        "PK": event_pk,
        "SK": METADATA_SK,
        "entityType": ENTITY_EVENT,
        "eventId": event_id,
        "matchName": "Manchester United vs Liverpool",
        "stadium": "Old Trafford",
        "capacity": 50000,
        "startTime": "2026-07-12T15:00:00Z",
        "status": EVENT_OPEN,
        "createdAt": now,
        "updatedAt": now,
    }

    # 2. Empty Statistics Item
    stats_item: dict[str, Any] = {
        "PK": event_pk,
        "SK": STATS_SK,
        "entityType": ENTITY_STATS,
        "eventId": event_id,
        "waitingUsers": 0,
        "admittedUsers": 0,
        "expiredUsers": 0,
        "cancelledUsers": 0,
        "completedUsers": 0,
        "totalUsers": 0,
        "avgWaitTime": 0,
        "createdAt": now,
        "updatedAt": now,
    }

    try:
        # Write Event
        print(f"Writing Event item ({event_pk} / {METADATA_SK})...")
        table.put_item(Item=event_item)

        # Write Stats
        print(f"Writing Statistics item ({event_pk} / {STATS_SK})...")
        table.put_item(Item=stats_item)

        print("\nDatabase seeding completed successfully! ✅")
        print(f"Event ID '{event_id}' ('{event_item['matchName']}') is now OPEN and accepting registrations.")

    except ClientError as exc:
        print(f"\nError seeding database: {exc}", file=sys.stderr)
        print("Please check your AWS CLI configuration, credentials, and region.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    seed_database()
