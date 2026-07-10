"""
DynamoDB helper functions for the Football Virtual Waiting Room.

Provides a reusable DynamoDB resource, along with helper functions for
common operations (put_item, get_item, query, update_item) with built-in
error handling and structured logging.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, Optional

import boto3
from boto3.dynamodb.types import TypeSerializer
from botocore.config import Config
from botocore.exceptions import ClientError

from common.constants import (
    ENTITY_EVENT,
    ENTITY_STATS,
    EVENT_CLOSED,
    EVENT_PREFIX,
    GSI1PK,
    GSI1SK,
    GSI1_NAME,
    GSI3_NAME,
    METADATA_SK,
    QUEUE_PREFIX,
    QUEUE_REGISTRATION_PREFIX,
    STATS_SHARD_COUNT,
    STATS_SHARD_PREFIX,
    STATS_SK,
    STATUS_REGISTRATION_CLOSED,
    STATUS_WAITING,
    TABLE_NAME,
    TOKEN_PREFIX,
    USER_PREFIX,
)
from common.logger import logger

# ---------------------------------------------------------------------------
# DynamoDB Resource (reused across Lambda invocations for connection pooling)
# ---------------------------------------------------------------------------
_dynamodb = boto3.resource(
    "dynamodb",
    config=Config(
        retries={
            "max_attempts": 8,
            "mode": "adaptive",
        }
    ),
)
_table = _dynamodb.Table(TABLE_NAME)
_serializer = TypeSerializer()


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


def transact_put_items(items: list[tuple[dict[str, Any], str | None]]) -> bool:
    """Write multiple items atomically.

    Returns ``False`` when a transaction is cancelled by a conditional check,
    and raises for other DynamoDB errors.
    """
    def _build_transact_items(serialize: bool = False) -> list[dict[str, Any]]:
        transact_items: list[dict[str, Any]] = []
        for item, condition_expression in items:
            request_item = (
                {key: _serializer.serialize(value) for key, value in item.items()}
                if serialize
                else item
            )
            put_request: dict[str, Any] = {
                "TableName": TABLE_NAME,
                "Item": request_item,
            }
            if condition_expression:
                put_request["ConditionExpression"] = condition_expression
            transact_items.append({"Put": put_request})
        return transact_items

    def _is_shape_error(exc: ClientError) -> bool:
        message = exc.response.get("Error", {}).get("Message", "")
        reasons = exc.response.get("CancellationReasons", [])
        reason_messages = " ".join(reason.get("Message", "") for reason in reasons)
        return (
            any(reason.get("Code") in {"TypeError", "ValidationError"} for reason in reasons)
            and (
                "Type mismatch" in reason_messages
                or "parameter values were invalid" in reason_messages
                or "Parameter validation failed" in message
            )
        )

    def _is_conditional_cancellation(exc: ClientError) -> bool:
        reasons = exc.response.get("CancellationReasons", [])
        reason_codes = [
            reason.get("Code")
            for reason in reasons
            if reason.get("Code") and reason.get("Code") != "None"
        ]
        if reason_codes:
            return all(code == "ConditionalCheckFailed" for code in reason_codes)

        message = exc.response.get("Error", {}).get("Message", "")
        return "ConditionalCheckFailed" in message

    try:
        # The DynamoDB resource's client applies the same document
        # transformation as table operations. Send plain Python values here;
        # pre-serializing turns key values into maps and causes ValidationError.
        _table.meta.client.transact_write_items(TransactItems=_build_transact_items())
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "TransactionCanceledException" and _is_shape_error(exc):
            try:
                _table.meta.client.transact_write_items(TransactItems=_build_transact_items(serialize=True))
                return True
            except ClientError as retry_exc:
                exc = retry_exc

        if (
            exc.response["Error"]["Code"] == "TransactionCanceledException"
            and _is_conditional_cancellation(exc)
        ):
            logger.info(
                "DynamoDB transact_put_items cancelled by conditional check.",
                extra={"cancellationReasons": exc.response.get("CancellationReasons", [])},
            )
            return False
        logger.exception("DynamoDB transact_put_items error")
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


def delete_item(pk: str, sk: str) -> bool:
    """Delete a single item by primary key."""
    try:
        _table.delete_item(Key={"PK": pk, "SK": sk})
        return True
    except ClientError:
        logger.exception("DynamoDB delete_item error")
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


def scan_items(
    filter_expression: Any = None,
    projection_expression: str | None = None,
    expression_names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Scan the table and return all matching items."""
    try:
        kwargs: dict[str, Any] = {}
        if filter_expression is not None:
            kwargs["FilterExpression"] = filter_expression
        if projection_expression:
            kwargs["ProjectionExpression"] = projection_expression
        if expression_names:
            kwargs["ExpressionAttributeNames"] = expression_names

        items: list[dict[str, Any]] = []
        while True:
            response = _table.scan(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                return items
            kwargs["ExclusiveStartKey"] = last_key
    except ClientError:
        logger.exception("DynamoDB scan error")
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


def stats_shard_id(seed: str) -> int:
    """Return a stable stats shard number for a user/event seed."""
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(digest, 16) % STATS_SHARD_COUNT


def increment_stats(
    event_id: str,
    increments: dict[str, int],
    shard_seed: str | None = None,
) -> Optional[dict[str, Any]]:
    """Increment per-event counters on a sharded STATS item.

    Sharding avoids making the root ``EVENT#id / STATS`` item a write hot spot
    during high-volume queue joins.
    """
    if not increments:
        return None

    shard = stats_shard_id(shard_seed or event_id)
    pk = f"{EVENT_PREFIX}{event_id}"
    sk = f"{STATS_SHARD_PREFIX}{shard:02d}"

    expression_names = {f"#n{i}": name for i, name in enumerate(increments)}
    expression_values: dict[str, Any] = {
        f":v{i}": value
        for i, value in enumerate(increments.values())
    }
    expression_values.update({
        ":entity": ENTITY_STATS,
        ":eventId": event_id,
    })

    add_parts = [
        f"{name_ref} {value_ref}"
        for name_ref, value_ref in zip(expression_names, [f":v{i}" for i in range(len(increments))])
    ]

    return update_item(
        pk=pk,
        sk=sk,
        update_expression=(
            "SET entityType = :entity, eventId = :eventId "
            f"ADD {', '.join(add_parts)}"
        ),
        expression_values=expression_values,
        expression_names=expression_names,
    )


# ============================================================================
# Convenience Lookups
# ============================================================================


def get_event(event_id: str) -> Optional[dict[str, Any]]:
    """Retrieve event metadata by Event ID."""
    return get_item(f"{EVENT_PREFIX}{event_id}", METADATA_SK)


def list_events() -> list[dict[str, Any]]:
    """Return all event metadata records."""
    from boto3.dynamodb.conditions import Attr

    return sorted(
        scan_items(filter_expression=Attr("entityType").eq(ENTITY_EVENT)),
        key=lambda item: item.get("startTime", ""),
    )


def get_event_stats(event_id: str) -> Optional[dict[str, Any]]:
    """Retrieve aggregate queue statistics for an event.

    The root ``STATS`` item stores low-frequency metadata such as
    ``currentlyServingPosition``. High-frequency counters are summed from
    sharded stats items.
    """
    from boto3.dynamodb.conditions import Key

    pk = f"{EVENT_PREFIX}{event_id}"
    base = get_item(pk, STATS_SK)
    if not base:
        return None

    items = query_items(
        key_condition=Key("PK").eq(pk) & Key("SK").begins_with(STATS_SHARD_PREFIX),
    )

    stats = dict(base)
    for attr in (
        "waitingUsers",
        "admittedUsers",
        "expiredUsers",
        "cancelledUsers",
        "completedUsers",
        "totalUsers",
        "avgWaitTime",
        "closedUsers",
    ):
        stats[attr] = int(base.get(attr, 0))

    for item in items:
        for attr in (
            "waitingUsers",
            "admittedUsers",
            "expiredUsers",
            "cancelledUsers",
            "completedUsers",
            "totalUsers",
            "closedUsers",
        ):
            stats[attr] += int(item.get(attr, 0))

    return stats


def get_token(token_id: str) -> Optional[dict[str, Any]]:
    """Retrieve an admission token by Token ID."""
    return get_item(f"{TOKEN_PREFIX}{token_id}", METADATA_SK)


def query_user_queue(user_id: str, event_id: str) -> Optional[dict[str, Any]]:
    """Look up a user's active queue entry through the registration guard."""
    registration = get_item(f"{USER_PREFIX}{user_id}", f"{QUEUE_REGISTRATION_PREFIX}{event_id}")
    if not registration:
        return None

    queue_pk = registration.get("queuePK")
    queue_sk = registration.get("queueSK")
    if queue_pk and queue_sk:
        queue_item = get_item(queue_pk, queue_sk)
        if queue_item:
            return queue_item

    return registration


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


def query_queue_entries(
    event_id: str,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return queue entries for admin views using GSI3."""
    from boto3.dynamodb.conditions import Key

    prefix = f"STATUS#{status}#" if status else "STATUS#"
    return query_items(
        key_condition=(
            Key("GSI3PK").eq(f"{EVENT_PREFIX}{event_id}")
            & Key("GSI3SK").begins_with(prefix)
        ),
        index_name=GSI3_NAME,
        limit=limit,
    )


def close_waiting_registrations(event_id: str, max_items: int = 100000) -> int:
    """Mark waiting queue entries as closed when no more registration slots remain."""
    closed_count = 0
    now = datetime.now(UTC).isoformat()

    while closed_count < max_items:
        waiting_items = query_queue_entries(
            event_id,
            status=STATUS_WAITING,
            limit=min(500, max_items - closed_count),
        )
        if not waiting_items:
            break

        changed_this_page = 0
        for item in waiting_items:
            queue_position = item.get("queuePosition", "")
            user_id = item.get("userId", "")
            if not queue_position or not user_id:
                continue

            updated = update_item(
                pk=f"{EVENT_PREFIX}{event_id}",
                sk=f"{QUEUE_PREFIX}{queue_position}",
                update_expression=(
                    "SET #status = :new_status, updatedAt = :now, GSI3SK = :gsi3sk "
                    "REMOVE #gsi1pk, #gsi1sk"
                ),
                expression_values={
                    ":new_status": STATUS_REGISTRATION_CLOSED,
                    ":now": now,
                    ":current_status": STATUS_WAITING,
                    ":gsi3sk": f"STATUS#{STATUS_REGISTRATION_CLOSED}#{queue_position}",
                },
                expression_names={
                    "#status": "status",
                    "#gsi1pk": GSI1PK,
                    "#gsi1sk": GSI1SK,
                },
                condition_expression="#status = :current_status",
            )
            if not updated:
                continue

            update_item(
                pk=f"{USER_PREFIX}{user_id}",
                sk=f"{QUEUE_REGISTRATION_PREFIX}{event_id}",
                update_expression="SET #status = :new_status, updatedAt = :now",
                expression_values={":new_status": STATUS_REGISTRATION_CLOSED, ":now": now},
                expression_names={"#status": "status"},
            )
            closed_count += 1
            changed_this_page += 1

        if changed_this_page == 0:
            break

    if closed_count:
        increment_stats(
            event_id,
            {"waitingUsers": -closed_count, "closedUsers": closed_count},
            shard_seed=f"closed#{event_id}",
        )

    update_item(
        pk=f"{EVENT_PREFIX}{event_id}",
        sk=METADATA_SK,
        update_expression="SET #status = :status, updatedAt = :now",
        expression_values={":status": EVENT_CLOSED, ":now": now},
        expression_names={"#status": "status"},
    )
    return closed_count
