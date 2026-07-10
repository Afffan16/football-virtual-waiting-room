"""Clear waiting-room data from the DynamoDB table.

Default behavior keeps event metadata and resets each event's STATS row.
Use --delete-events to remove event metadata as well.
"""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from typing import Any

import boto3


EVENT_PREFIX = "EVENT#"
METADATA_SK = "METADATA"
STATS_SK = "STATS"
ENTITY_EVENT = "EVENT"
ENTITY_STATS = "STATS"


def scan_all(table: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    kwargs: dict[str, Any] = {}
    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return items
        kwargs["ExclusiveStartKey"] = last_key


def batch_delete(table: Any, items: list[dict[str, Any]]) -> None:
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})


def reset_stats(table: Any, event_items: list[dict[str, Any]]) -> None:
    now = datetime.now(UTC).isoformat()
    with table.batch_writer() as batch:
        for event in event_items:
            event_id = event["eventId"]
            batch.put_item(Item={
                "PK": f"{EVENT_PREFIX}{event_id}",
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
            })


def reopen_events(table: Any, event_items: list[dict[str, Any]]) -> None:
    now = datetime.now(UTC).isoformat()
    with table.batch_writer() as batch:
        for event in event_items:
            updated = dict(event)
            updated["status"] = "OPEN"
            updated["updatedAt"] = now
            batch.put_item(Item=updated)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clear event queue records from DynamoDB.")
    parser.add_argument(
        "--table-name",
        default=os.environ.get("TABLE_NAME"),
        required=not os.environ.get("TABLE_NAME"),
        help="DynamoDB table name. Can also be provided as TABLE_NAME.",
    )
    parser.add_argument(
        "--delete-events",
        action="store_true",
        help="Delete event METADATA rows too. Default keeps events and resets stats.",
    )
    parser.add_argument(
        "--reopen-events",
        action="store_true",
        help="Set preserved event metadata back to OPEN after clearing queue data.",
    )
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt.")
    args = parser.parse_args()

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(args.table_name)

    all_items = scan_all(table)
    event_items = [item for item in all_items if item.get("entityType") == ENTITY_EVENT]

    if args.delete_events:
        to_delete = [
            item for item in all_items
            if item.get("PK", "").startswith(EVENT_PREFIX)
            or item.get("entityType") in {"QUEUE_REGISTRATION", "TOKEN"}
        ]
    else:
        to_delete = [
            item for item in all_items
            if item.get("entityType") != ENTITY_EVENT
            and (
                item.get("PK", "").startswith(EVENT_PREFIX)
                or item.get("entityType") in {"QUEUE_REGISTRATION", "TOKEN"}
            )
        ]

    print(f"Table: {args.table_name}")
    print(f"Events found: {len(event_items)}")
    print(f"Items to delete: {len(to_delete)}")
    if not args.delete_events:
        print("Event metadata will be kept and STATS rows will be reset.")
    if args.reopen_events and not args.delete_events:
        print("Preserved events will be set back to OPEN.")

    if not args.yes:
        answer = input("Type CLEAR to continue: ").strip()
        if answer != "CLEAR":
            print("Cancelled.")
            return

    if to_delete:
        batch_delete(table, to_delete)
    if not args.delete_events:
        reset_stats(table, event_items)
        if args.reopen_events:
            reopen_events(table, event_items)

    print("Done.")


if __name__ == "__main__":
    main()
