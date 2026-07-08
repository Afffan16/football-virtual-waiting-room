"""
DynamoDB helper functions for the Football Virtual Waiting Room.

Provides a reusable DynamoDB resource, along with helper functions for
common operations (put_item, get_item, query, update_item) with built-in
error handling and structured logging.
"""

from __future__ import annotations

from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from common.constants import (
    EVENT_PREFIX,
    GSI1_NAME,
    GSI2_NAME,
    GSI3_NAME,
    METADATA_SK,
    QUEUE_PREFIX,
    STATS_SK,
    TABLE_NAME,
    TOKEN_PREFIX,
    USER_PREFIX,
)
from common.logger import logger

# ---------------------------------------------------------------------------
# DynamoDB Resource (reused across Lambda invocations for connection pooling)
# ---------------------------------------------------------------------------
_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(TABLE_NAME)


def get_table():
    """Return the shared DynamoDB Table resource."""
    return _table


# ============================================================================
# Core Operations
# ============================================================================


def put_item(item: dict[str, Any], condition_expression: str | None = None) -> bool:
    """Write an item to the table.

    Returns ``True`` on success, ``False`` if the condition fails
    (``ConditionalCheckFailedException``).

    Raises on any other client error.
    """
    try:
        kwargs: dict[str, Any] = {"Item": item}
        if condition_expression:
            kwargs["ConditionExpression"] = condition_expression
        _table.put_item(**kwargs)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.info("Conditional put_item failed — item already exists.")
            return False
        logger.exception("DynamoDB put_item error")
        raise


def get_item(pk: str, sk: str) -> Optional[dict[str, Any]]:
    """Retrieve a single item by its composite primary key.

    Returns the item dict, or ``None`` if not found.
    """
    try:
        response = _table.get_item(Key={"PK": pk, "SK": sk})
        return response.get("Item")
    except ClientError:
        logger.exception("DynamoDB get_item error")
        raise


def query_items(
    key_condition: Any,
    index_name: str | None = None,
    limit: int | None = None,
    scan_index_forward: bool = True,
    filter_expression: Any = None,
) -> list[dict[str, Any]]:
    """Run a Query against the table or a GSI.

    Returns a list of item dicts (may be empty).
    """
    try:
        kwargs: dict[str, Any] = {"KeyConditionExpression": key_condition}
        if index_name:
            kwargs["IndexName"] = index_name
        if limit:
            kwargs["Limit"] = limit
        if not scan_index_forward:
            kwargs["ScanIndexForward"] = False
        if filter_expression:
            kwargs["FilterExpression"] = filter_expression
        response = _table.query(**kwargs)
        return response.get("Items", [])
    except ClientError:
        logger.exception("DynamoDB query error")
        raise


def update_item(
    pk: str,
    sk: str,
    update_expression: str,
    expression_values: dict[str, Any],
    condition_expression: str | None = None,
    expression_names: dict[str, str] | None = None,
    return_values: str = "ALL_NEW",
) -> Optional[dict[str, Any]]:
    """Update an item and return its new attributes.

    Returns ``None`` if the conditional check fails.
    """
    try:
        kwargs: dict[str, Any] = {
            "Key": {"PK": pk, "SK": sk},
            "UpdateExpression": update_expression,
            "ExpressionAttributeValues": expression_values,
            "ReturnValues": return_values,
        }
        if condition_expression:
            kwargs["ConditionExpression"] = condition_expression
        if expression_names:
            kwargs["ExpressionAttributeNames"] = expression_names
        response = _table.update_item(**kwargs)
        return response.get("Attributes")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.info("Conditional update_item failed.")
            return None
        logger.exception("DynamoDB update_item error")
        raise


def atomic_increment(
    pk: str,
    sk: str,
    attribute: str,
    increment: int = 1,
) -> int:
    """Atomically increment a numeric attribute and return the new value."""
    response = _table.update_item(
        Key={"PK": pk, "SK": sk},
        UpdateExpression=f"ADD #attr :inc",
        ExpressionAttributeNames={"#attr": attribute},
        ExpressionAttributeValues={":inc": increment},
        ReturnValues="ALL_NEW",
    )
    return int(response["Attributes"][attribute])


# ============================================================================
# Convenience Lookups
# ============================================================================


def get_event(event_id: str) -> Optional[dict[str, Any]]:
    """Retrieve event metadata by Event ID."""
    return get_item(f"{EVENT_PREFIX}{event_id}", METADATA_SK)


def get_event_stats(event_id: str) -> Optional[dict[str, Any]]:
    """Retrieve queue statistics for an event."""
    return get_item(f"{EVENT_PREFIX}{event_id}", STATS_SK)


def get_token(token_id: str) -> Optional[dict[str, Any]]:
    """Retrieve an admission token by Token ID."""
    return get_item(f"{TOKEN_PREFIX}{token_id}", METADATA_SK)


def query_user_queue(user_id: str, event_id: str) -> Optional[dict[str, Any]]:
    """Look up a user's queue entry via GSI1."""
    from boto3.dynamodb.conditions import Key

    items = query_items(
        key_condition=Key("GSI1PK").eq(f"{USER_PREFIX}{user_id}")
        & Key("GSI1SK").eq(f"{EVENT_PREFIX}{event_id}"),
        index_name=GSI1_NAME,
        limit=1,
    )
    return items[0] if items else None


def query_waiting_users(
    event_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve the next batch of WAITING users from the queue,
    ordered by queue position (sort key).

    Uses the base table — queries items where PK = EVENT#<id> and
    SK begins_with QUEUE#, then filters for WAITING status.
    """
    from boto3.dynamodb.conditions import Attr, Key

    return query_items(
        key_condition=(
            Key("PK").eq(f"{EVENT_PREFIX}{event_id}")
            & Key("SK").begins_with(QUEUE_PREFIX)
        ),
        limit=limit,
        scan_index_forward=True,
        filter_expression=Attr("status").eq("WAITING"),
    )
