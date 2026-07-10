"""
Admit Users Lambda - admits a batch of waiting users from the queue.

Endpoint: POST /queue/admit
"""

from __future__ import annotations

from typing import Any

from boto3.dynamodb.conditions import Key

from common.auth import is_admin_authorized
from common.constants import (
    DEFAULT_BATCH_SIZE,
    ENTITY_TOKEN,
    EVENT_PREFIX,
    GSI2PK,
    GSI2SK,
    GSI3_NAME,
    MAX_BATCH_SIZE,
    METADATA_SK,
    PURCHASING_CAPACITY,
    QUEUE_PREFIX,
    QUEUE_REGISTRATION_PREFIX,
    STATS_SK,
    STATUS_ADMITTED,
    STATUS_WAITING,
    TOKEN_ACTIVE,
    TOKEN_PREFIX,
    TOKEN_TTL_MINUTES,
    USER_PREFIX,
)
from common.dynamodb import (
    get_event_stats,
    increment_stats,
    put_item,
    query_items,
    update_item,
)
from common.logger import logger
from common.responses import bad_request, forbidden, internal_error, success
from common.utils import (
    epoch_minutes_from_now,
    generate_token_id,
    parse_body,
    utc_now_iso,
    validate_required_fields,
)


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """API Gateway proxy handler for POST /queue/admit."""
    try:
        if not is_admin_authorized(event):
            logger.warning("Unauthorized admit attempt - missing or invalid admin credentials")
            return forbidden("Admin authorization required.")

        body = parse_body(event)
        validation_error = validate_required_fields(body, ["eventId"])
        if validation_error:
            return bad_request(validation_error)

        event_id: str = body["eventId"]
        try:
            batch_size: int = int(body.get("batchSize", DEFAULT_BATCH_SIZE))
            purchasing_capacity: int = int(body.get("purchasingCapacity", PURCHASING_CAPACITY))
        except (TypeError, ValueError):
            return bad_request("batchSize and purchasingCapacity must be numbers.")

        capacity_mode: bool = bool(body.get("capacityMode", False))
        if capacity_mode:
            stats_now = get_event_stats(event_id) or {}
            currently_admitted = int(stats_now.get("admittedUsers", 0))
            available_slots = max(0, purchasing_capacity - currently_admitted)
            if available_slots == 0:
                return success({
                    "admittedUsers": 0,
                    "remainingQueue": int(stats_now.get("waitingUsers", 0)),
                    "admittedUserIds": [],
                    "capacityFull": True,
                    "activePurchasers": currently_admitted,
                    "purchasingCapacity": purchasing_capacity,
                })
            batch_size = available_slots

        if batch_size < 1:
            return bad_request("batchSize must be at least 1. Use /queue/admin/list to inspect the queue.")

        batch_size = min(batch_size, MAX_BATCH_SIZE)
        logger.append_keys(eventId=event_id, batchSize=batch_size)
        logger.info("Processing admit users request")

        waiting_items = query_items(
            index_name=GSI3_NAME,
            key_condition=(
                Key("GSI3PK").eq(f"{EVENT_PREFIX}{event_id}")
                & Key("GSI3SK").begins_with(f"STATUS#{STATUS_WAITING}#")
            ),
            limit=batch_size,
        )

        if not waiting_items:
            stats = get_event_stats(event_id) or {}
            return success({
                "admittedUsers": 0,
                "remainingQueue": int(stats.get("waitingUsers", 0)),
                "admittedUserIds": [],
            })

        admitted_count = 0
        admitted_user_ids: list[str] = []
        now = utc_now_iso()
        token_expires_at = epoch_minutes_from_now(TOKEN_TTL_MINUTES)
        last_admitted_position = ""

        for item in waiting_items:
            user_id = item.get("userId", "")
            queue_position = item.get("queuePosition", "")
            if not user_id or not queue_position:
                continue

            updated = update_item(
                pk=f"{EVENT_PREFIX}{event_id}",
                sk=f"{QUEUE_PREFIX}{queue_position}",
                update_expression="SET #status = :new_status, admissionTime = :now, updatedAt = :now, GSI3SK = :gsi3sk",
                expression_values={
                    ":new_status": STATUS_ADMITTED,
                    ":now": now,
                    ":current_status": STATUS_WAITING,
                    ":gsi3sk": f"STATUS#{STATUS_ADMITTED}#{queue_position}",
                },
                expression_names={"#status": "status"},
                condition_expression="#status = :current_status",
            )
            if not updated:
                logger.info("Skipping user because status changed", extra={"userId": user_id})
                continue

            update_item(
                pk=f"{USER_PREFIX}{user_id}",
                sk=f"{QUEUE_REGISTRATION_PREFIX}{event_id}",
                update_expression="SET #status = :new_status, updatedAt = :now",
                expression_values={":new_status": STATUS_ADMITTED, ":now": now},
                expression_names={"#status": "status"},
            )

            token_id = generate_token_id()
            put_item({
                "PK": f"{TOKEN_PREFIX}{token_id}",
                "SK": METADATA_SK,
                "entityType": ENTITY_TOKEN,
                "tokenId": token_id,
                "userId": user_id,
                "eventId": event_id,
                "status": TOKEN_ACTIVE,
                "expiresAt": token_expires_at,
                "ttl": token_expires_at,
                "createdAt": now,
                GSI2PK: f"{TOKEN_PREFIX}{token_id}",
                GSI2SK: f"STATUS#{TOKEN_ACTIVE}",
            })

            admitted_count += 1
            admitted_user_ids.append(user_id)
            last_admitted_position = queue_position

        if admitted_count > 0:
            increment_stats(
                event_id,
                {"waitingUsers": -admitted_count, "admittedUsers": admitted_count},
                shard_seed=f"admit#{last_admitted_position}",
            )
            update_item(
                pk=f"{EVENT_PREFIX}{event_id}",
                sk=STATS_SK,
                update_expression="SET currentlyServingPosition = :serving",
                expression_values={":serving": last_admitted_position},
            )

        stats = get_event_stats(event_id) or {}
        return success({
            "admittedUsers": admitted_count,
            "remainingQueue": int(stats.get("waitingUsers", 0)),
            "admittedUserIds": admitted_user_ids,
            "activePurchasers": int(stats.get("admittedUsers", 0)),
            "purchasingCapacity": purchasing_capacity if capacity_mode else PURCHASING_CAPACITY,
        })

    except Exception:
        logger.exception("Unexpected error in admit_users")
        return internal_error()
