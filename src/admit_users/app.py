"""
Admit Users Lambda — Admits a batch of waiting users from the queue.

Endpoint: POST /queue/admit

This function:
  1. Validates the request body (eventId required, optional batchSize).
  2. Queries GSI3 to find the next N users in WAITING status, ordered by queue position.
  3. Loops through each user to:
     a. Transition their status from WAITING to ADMITTED.
     b. Generate a temporary admission token with a TTL.
  4. Updates the aggregate stats (waitingUsers decrement, admittedUsers increment).
  5. Returns the number of admitted users and remaining queue size.
"""

from __future__ import annotations

import os
from typing import Any

from common.constants import (
    DEFAULT_BATCH_SIZE,
    ENTITY_TOKEN,
    EVENT_PREFIX,
    GSI2PK,
    GSI2SK,
    GSI3_NAME,
    METADATA_SK,
    QUEUE_PREFIX,
    QUEUE_POSITION_PAD_LENGTH,
    STATS_SK,
    STATUS_ADMITTED,
    STATUS_WAITING,
    TOKEN_ACTIVE,
    TOKEN_PREFIX,
    TOKEN_TTL_MINUTES,
)
from common.dynamodb import (
    atomic_increment,
    get_event_stats,
    put_item,
    query_items,
    update_item,
)
from common.logger import logger
from common.responses import bad_request, internal_error, success
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
        # ----- Parse & validate -----
        body = parse_body(event)
        validation_error = validate_required_fields(body, ["eventId"])
        if validation_error:
            return bad_request(validation_error)

        event_id: str = body["eventId"]
        batch_size: int = int(body.get("batchSize", DEFAULT_BATCH_SIZE))

        logger.append_keys(eventId=event_id, batchSize=batch_size)
        logger.info("Processing admit users request")

        # ----- Query WAITING users using GSI3 -----
        # This retrieves users in WAITING status ordered by queue position
        from boto3.dynamodb.conditions import Key
        waiting_items = query_items(
            index_name=GSI3_NAME,
            key_condition=(
                Key("GSI3PK").eq(f"{EVENT_PREFIX}{event_id}")
                & Key("GSI3SK").begins_with(f"STATUS#{STATUS_WAITING}#")
            ),
            limit=batch_size,
        )

        if not waiting_items:
            logger.info("No waiting users found in the queue")
            # Retrieve current stats to return remaining queue size
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
        # ----- Process each waiting user -----
        for item in waiting_items:
            user_id = item.get("userId")
            queue_position = item.get("queuePosition", "")
            padded = queue_position

            # 1. Update queue entry status to ADMITTED conditionally
            pk = f"{EVENT_PREFIX}{event_id}"
            sk = f"{QUEUE_PREFIX}{padded}"
            updated = update_item(
                pk=pk,
                sk=sk,
                update_expression="SET #status = :new_status, admissionTime = :now, updatedAt = :now, GSI3SK = :gsi3sk",
                expression_values={
                    ":new_status": STATUS_ADMITTED,
                    ":now": now,
                    ":current_status": STATUS_WAITING,
                    ":gsi3sk": f"STATUS#{STATUS_ADMITTED}#{padded}",
                },
                expression_names={"#status": "status"},
                condition_expression="#status = :current_status",
            )

            if not updated:
                logger.info(f"Skipping user {user_id} (position {queue_position}) — status changed by another process")
                continue

            # 2. Generate admission token
            token_id = generate_token_id()
            token_item: dict[str, Any] = {
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
                # GSI2 — Token Lookup
                GSI2PK: f"{TOKEN_PREFIX}{token_id}",
                GSI2SK: f"STATUS#{TOKEN_ACTIVE}",
            }

            put_item(token_item)

            admitted_count += 1
            admitted_user_ids.append(user_id)
            last_admitted_position = queue_position

        # ----- Update statistics -----
        stats_pk = f"{EVENT_PREFIX}{event_id}"
        if admitted_count > 0:
            update_item(
                pk=stats_pk,
                sk=STATS_SK,
                update_expression="ADD admittedUsers :inc SET currentlyServingPosition = :serving",
                expression_values={":inc": admitted_count, ":serving": last_admitted_position}
            )

        # ----- Get remaining queue count -----
        stats = get_event_stats(event_id) or {}
        remaining_queue = int(stats.get("waitingUsers", 0))

        logger.info(f"Successfully admitted {admitted_count} users", extra={"admittedCount": admitted_count, "remainingQueue": remaining_queue})

        return success({
            "admittedUsers": admitted_count,
            "remainingQueue": remaining_queue,
            "admittedUserIds": admitted_user_ids,
        })

    except Exception:
        logger.exception("Unexpected error in admit_users")
        return internal_error()
