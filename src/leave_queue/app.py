"""
Leave Queue Lambda — Allows a user to voluntarily leave the queue.

Endpoint: POST /queue/leave

This function:
  1. Validates the request body (eventId, userId required).
  2. Looks up the user's queue entry via GSI1.
  3. Verifies the entry is in WAITING status.
  4. Updates the queue entry status to CANCELLED.
  5. Decrements the waitingUsers counter and increments cancelledUsers.
  6. Returns HTTP 200 on success.
"""

from __future__ import annotations

from typing import Any

from common.constants import (
    EVENT_PREFIX,
    QUEUE_PREFIX,
    QUEUE_POSITION_PAD_LENGTH,
    STATS_SK,
    STATUS_CANCELLED,
    STATUS_WAITING,
)
from common.dynamodb import atomic_increment, query_user_queue, update_item
from common.logger import logger
from common.responses import bad_request, conflict, internal_error, not_found, success
from common.utils import parse_body, utc_now_iso, validate_required_fields


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """API Gateway proxy handler for POST /queue/leave."""
    try:
        # ----- Parse & validate -----
        body = parse_body(event)
        validation_error = validate_required_fields(body, ["eventId", "userId"])
        if validation_error:
            return bad_request(validation_error)

        event_id: str = body["eventId"]
        user_id: str = body["userId"]

        logger.append_keys(eventId=event_id, userId=user_id)
        logger.info("Processing leave queue request")

        # ----- Look up existing queue entry -----
        item = query_user_queue(user_id, event_id)
        if not item:
            return not_found(f"No queue entry found for user '{user_id}' in event '{event_id}'.")

        current_status = item.get("status", "")
        if current_status != STATUS_WAITING:
            return conflict(f"Cannot leave queue — current status is '{current_status}'.")

        # ----- Build primary key for update -----
        queue_position = int(item.get("queuePosition", 0))
        padded = str(queue_position).zfill(QUEUE_POSITION_PAD_LENGTH)
        pk = f"{EVENT_PREFIX}{event_id}"
        sk = f"{QUEUE_PREFIX}{padded}"

        now = utc_now_iso()

        # ----- Update status to CANCELLED -----
        result = update_item(
            pk=pk,
            sk=sk,
            update_expression="SET #status = :new_status, updatedAt = :now, GSI3SK = :gsi3sk",
            expression_values={
                ":new_status": STATUS_CANCELLED,
                ":now": now,
                ":current_status": STATUS_WAITING,
                ":gsi3sk": f"STATUS#{STATUS_CANCELLED}#{padded}",
            },
            expression_names={"#status": "status"},
            condition_expression="#status = :current_status",
        )

        if result is None:
            return conflict("Queue entry status has already changed.")

        # ----- Update statistics -----
        stats_pk = f"{EVENT_PREFIX}{event_id}"
        atomic_increment(stats_pk, STATS_SK, "waitingUsers", increment=-1)
        atomic_increment(stats_pk, STATS_SK, "cancelledUsers", increment=1)

        logger.info("User successfully left queue", extra={"queuePosition": queue_position})

        return success({"message": "You have left the queue."})

    except Exception:
        logger.exception("Unexpected error in leave_queue")
        return internal_error()
