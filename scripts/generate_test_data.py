"""
Generate Test Data Script — Football Virtual Waiting Room.

Simulates registration of multiple users into the queue for load testing
and functional validation.
"""

from __future__ import annotations
import sys
from typing import Any

import boto3

# Add src to python path to access common module if run from repository root
sys.path.append("src")

from src.common.constants import (
    ENTITY_QUEUE,
    EVENT_PREFIX,
    GSI1PK,
    GSI1SK,
    GSI3PK,
    GSI3SK,
    QUEUE_PREFIX,
    STATS_SK,
    STATUS_WAITING,
    TABLE_NAME,
    USER_PREFIX,
)
from src.common.dynamodb import atomic_increment
from src.common.utils import estimate_wait_minutes, format_queue_position, utc_now_iso


def generate_users(count: int, event_id: str = "1001") -> None:
    """Register a batch of mock users in the waiting room."""
    print(f"Registering {count} test users for event '{event_id}' in table '{TABLE_NAME}'...")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    now = utc_now_iso()
    stats_pk = f"{EVENT_PREFIX}{event_id}"

    # Batch write items in chunks of 25 (DynamoDB BatchWriteItem limit)
    batch_items: list[dict[str, Any]] = []

    for i in range(1, count + 1):
        user_id = f"test-user-{i:04d}"

        # Increment totalUsers counter to get unique queue position
        position = atomic_increment(stats_pk, STATS_SK, "totalUsers")
        padded = format_queue_position(position)
        estimated_wait = estimate_wait_minutes(position)

        queue_item: dict[str, Any] = {
            "PK": f"{EVENT_PREFIX}{event_id}",
            "SK": f"{QUEUE_PREFIX}{padded}",
            "entityType": ENTITY_QUEUE,
            "eventId": event_id,
            "userId": user_id,
            "queuePosition": position,
            "status": STATUS_WAITING,
            "joinTime": now,
            "estimatedWait": estimated_wait,
            "admissionTime": "",
            "createdAt": now,
            "updatedAt": now,
            # GSI1 — User Queue Lookup
            GSI1PK: f"{USER_PREFIX}{user_id}",
            GSI1SK: f"{EVENT_PREFIX}{event_id}",
            # GSI3 — Admin Queue View
            GSI3PK: f"{EVENT_PREFIX}{event_id}",
            GSI3SK: f"STATUS#{STATUS_WAITING}#{padded}",
        }

        batch_items.append(queue_item)

        # Write in batches of 25
        if len(batch_items) == 25:
            write_batch(table, batch_items)
            # Increment waitingUsers stats counter
            atomic_increment(stats_pk, STATS_SK, "waitingUsers", increment=25)
            print(f"Registered {i} / {count} users...")
            batch_items = []

    # Write remaining
    if batch_items:
        write_batch(table, batch_items)
        atomic_increment(stats_pk, STATS_SK, "waitingUsers", increment=len(batch_items))
        print(f"Registered {count} / {count} users...")

    print(f"\nSuccessfully generated {count} test users in the queue! 🚀")


def write_batch(table: Any, items: list[dict[str, Any]]) -> None:
    """Helper to write a batch of items using DynamoDB BatchWriteItem."""
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)


if __name__ == "__main__":
    num_users = 100
    if len(sys.argv) > 1:
        try:
            num_users = int(sys.argv[1])
        except ValueError:
            pass

    generate_users(num_users)
