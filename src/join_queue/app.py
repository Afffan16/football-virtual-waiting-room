"""
Join Queue Lambda — Registers a user in the Football Virtual Waiting Room.

Endpoint: POST /queue/join

This function:
  1. Validates the request body (eventId, userId required).
  2. Verifies the event exists and its queue is OPEN.
  3. Uses an atomic counter on the STATS item to assign the next queue position.
  4. Writes the queue entry with a conditional expression to prevent duplicates.
  5. Updates the aggregate statistics (waitingUsers, totalUsers).
  6. Returns HTTP 201 with the assigned queue position.
"""

from __future__ import annotations

from typing import Any

from common.constants import (
    ENTITY_QUEUE,
    ENTITY_STATS,
    EVENT_OPEN,
    EVENT_PREFIX,
    GSI1PK,
    GSI1SK,
    GSI3PK,
    GSI3SK,
    QUEUE_PREFIX,
    QUEUE_POSITION_PAD_LENGTH,
    STATS_SK,
    STATUS_WAITING,
    USER_PREFIX,
)
from common.dynamodb import (
    atomic_increment,
    get_event,
    get_item,
    put_item,
    query_user_queue,
    update_item,
)
from common.logger import logger
from common.responses import bad_request, conflict, created, forbidden, internal_error, not_found
from common.utils import (
    estimate_wait_minutes,
    parse_body,
    utc_now_iso,
    validate_required_fields,
)


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """API Gateway proxy handler for POST /queue/join."""
    try:
        # ----- Parse & validate -----
        body = parse_body(event)
        validation_error = validate_required_fields(body, ["eventId", "userId"])
        if validation_error:
            return bad_request(validation_error)

        event_id: str = body["eventId"]
        user_id: str = body["userId"]

        logger.append_keys(eventId=event_id, userId=user_id)
        logger.info("Processing join queue request")

        # ----- Verify event exists and is open -----
        event_item = get_event(event_id)
        if not event_item:
            return not_found(f"Event '{event_id}' not found.")

        event_status = event_item.get("status", "")
        if event_status != EVENT_OPEN:
            return forbidden(f"Event '{event_id}' is not accepting registrations (status: {event_status}).")

        # ----- Check for duplicate registration via GSI1 -----
        existing = query_user_queue(user_id, event_id)
        if existing:
            logger.info("User already registered — returning existing entry")
            return created({
                "message": "Already registered.",
                "queuePosition": int(existing.get("queuePosition", 0)),
                "status": existing.get("status", STATUS_WAITING),
                "estimatedWaitMinutes": int(existing.get("estimatedWait", 0)),
            })

        # ----- Assign queue position via atomic counter -----
        stats_pk = f"{EVENT_PREFIX}{event_id}"
        new_position = atomic_increment(stats_pk, STATS_SK, "totalUsers")

        # ----- Estimate wait -----
        admitted_so_far = 0
        stats_item = get_item(stats_pk, STATS_SK)
        if stats_item:
            admitted_so_far = int(stats_item.get("admittedUsers", 0))
        estimated_wait = estimate_wait_minutes(new_position, admitted_so_far)

        # ----- Build queue item -----
        now = utc_now_iso()
        padded = str(new_position).zfill(QUEUE_POSITION_PAD_LENGTH)
        queue_item: dict[str, Any] = {
            "PK": f"{EVENT_PREFIX}{event_id}",
            "SK": f"{QUEUE_PREFIX}{padded}",
            "entityType": ENTITY_QUEUE,
            "eventId": event_id,
            "userId": user_id,
            "queuePosition": new_position,
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

        # ----- Write with condition (belt-and-suspenders duplicate guard) -----
        success = put_item(queue_item, condition_expression="attribute_not_exists(PK) AND attribute_not_exists(SK)")
        if not success:
            return conflict("Queue entry already exists for this position.")

        # ----- Update waiting users counter -----
        atomic_increment(stats_pk, STATS_SK, "waitingUsers")

        logger.info("User successfully joined queue", extra={"queuePosition": new_position})

        return created({
            "message": "Successfully joined queue.",
            "queuePosition": new_position,
            "status": STATUS_WAITING,
            "estimatedWaitMinutes": estimated_wait,
        })

    except Exception:
        logger.exception("Unexpected error in join_queue")
        return internal_error()
