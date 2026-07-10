"""
Join Queue Lambda - registers a user in the Football Virtual Waiting Room.

Endpoint: POST /queue/join
"""

from __future__ import annotations

from typing import Any

from common.constants import (
    ENTITY_QUEUE,
    ENTITY_QUEUE_REGISTRATION,
    EVENT_OPEN,
    EVENT_PREFIX,
    GSI1PK,
    GSI1SK,
    GSI3PK,
    GSI3SK,
    QUEUE_PREFIX,
    QUEUE_REGISTRATION_PREFIX,
    STATUS_WAITING,
    USER_PREFIX,
)
from common.dynamodb import (
    get_event,
    get_item,
    increment_stats,
    query_user_queue,
    transact_put_items,
)
from common.logger import logger
from common.responses import bad_request, conflict, created, forbidden, internal_error, not_found
from common.utils import (
    estimate_wait_minutes,
    generate_queue_position,
    parse_body,
    utc_now_iso,
    validate_required_fields,
)

_event_cache: dict[str, dict[str, Any]] = {}


def _get_cached_event(event_id: str) -> dict[str, Any] | None:
    """Return event metadata, caching it across warm Lambda invocations."""
    if event_id not in _event_cache:
        item = get_event(event_id)
        if item:
            _event_cache[event_id] = item
    return _event_cache.get(event_id)


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """API Gateway proxy handler for POST /queue/join."""
    try:
        body = parse_body(event)
        validation_error = validate_required_fields(body, ["eventId", "userId"])
        if validation_error:
            return bad_request(validation_error)

        event_id: str = body["eventId"]
        user_id: str = body["userId"]

        if len(event_id) > 64 or len(user_id) > 128:
            return bad_request("eventId or userId exceeds maximum allowed length.")

        logger.append_keys(eventId=event_id, userId=user_id)
        logger.info("Processing join queue request")

        event_item = _get_cached_event(event_id)
        if not event_item:
            return not_found(f"Event '{event_id}' not found.")

        event_status = event_item.get("status", "")
        if event_status != EVENT_OPEN:
            return forbidden(f"Event '{event_id}' is not accepting registrations (status: {event_status}).")

        new_position = generate_queue_position()
        estimated_wait = estimate_wait_minutes(new_position)
        now = utc_now_iso()

        queue_item: dict[str, Any] = {
            "PK": f"{EVENT_PREFIX}{event_id}",
            "SK": f"{QUEUE_PREFIX}{new_position}",
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
            GSI1PK: f"{USER_PREFIX}{user_id}",
            GSI1SK: f"{EVENT_PREFIX}{event_id}",
            GSI3PK: f"{EVENT_PREFIX}{event_id}",
            GSI3SK: f"STATUS#{STATUS_WAITING}#{new_position}",
        }

        registration_item: dict[str, Any] = {
            "PK": f"{USER_PREFIX}{user_id}",
            "SK": f"{QUEUE_REGISTRATION_PREFIX}{event_id}",
            "entityType": ENTITY_QUEUE_REGISTRATION,
            "eventId": event_id,
            "userId": user_id,
            "queuePosition": new_position,
            "queuePK": queue_item["PK"],
            "queueSK": queue_item["SK"],
            "status": STATUS_WAITING,
            "estimatedWait": estimated_wait,
            "createdAt": now,
            "updatedAt": now,
        }

        success = transact_put_items([
            (registration_item, "attribute_not_exists(PK) AND attribute_not_exists(SK)"),
            (queue_item, "attribute_not_exists(PK) AND attribute_not_exists(SK)"),
        ])
        if not success:
            existing = query_user_queue(user_id, event_id)
            if not existing:
                existing = get_item(f"{USER_PREFIX}{user_id}", f"{QUEUE_REGISTRATION_PREFIX}{event_id}")
            if existing:
                logger.info("User already registered - returning existing entry")
                return created({
                    "message": "Already registered.",
                    "queuePosition": existing.get("queuePosition", ""),
                    "status": existing.get("status", STATUS_WAITING),
                    "estimatedWaitMinutes": int(existing.get("estimatedWait", estimated_wait)),
                })
            return conflict("Queue registration already exists.")

        increment_stats(
            event_id,
            {"waitingUsers": 1, "totalUsers": 1},
            shard_seed=user_id,
        )

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
