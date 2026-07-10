"""Admin event creation Lambda."""

from __future__ import annotations

from typing import Any

from common.auth import is_admin_authorized
from common.constants import ENTITY_STATS, EVENT_OPEN, EVENT_PREFIX, METADATA_SK, STATS_SK
from common.dynamodb import transact_put_items
from common.logger import logger
from common.models import Event
from common.responses import bad_request, conflict, created, forbidden, internal_error
from common.utils import parse_body, utc_now_iso, validate_required_fields


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """API Gateway proxy handler for POST /event."""
    try:
        if not is_admin_authorized(event):
            return forbidden("Admin authorization required.")

        body = parse_body(event)
        validation_error = validate_required_fields(
            body,
            ["eventId", "matchName", "stadium", "capacity", "startTime"],
        )
        if validation_error:
            return bad_request(validation_error)

        event_id = str(body["eventId"]).strip()
        match_name = str(body["matchName"]).strip()
        stadium = str(body["stadium"]).strip()
        start_time = str(body["startTime"]).strip()
        status = str(body.get("status", EVENT_OPEN)).strip().upper() or EVENT_OPEN

        try:
            capacity = int(body["capacity"])
        except (TypeError, ValueError):
            return bad_request("capacity must be a number.")

        if not event_id or not match_name or not stadium or not start_time:
            return bad_request("eventId, matchName, stadium, and startTime cannot be empty.")
        if len(event_id) > 64 or len(match_name) > 160 or len(stadium) > 120:
            return bad_request("eventId, matchName, or stadium exceeds maximum allowed length.")
        if capacity < 1:
            return bad_request("capacity must be at least 1.")
        if status not in {"UPCOMING", "OPEN", "CLOSED", "FINISHED"}:
            return bad_request("status must be UPCOMING, OPEN, CLOSED, or FINISHED.")

        now = utc_now_iso()
        event_item = Event(
            event_id=event_id,
            match_name=match_name,
            stadium=stadium,
            capacity=capacity,
            start_time=start_time,
            status=status,
            created_at=now,
            updated_at=now,
        ).to_item()
        stats_item = {
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
        }

        success = transact_put_items([
            (event_item, "attribute_not_exists(PK) AND attribute_not_exists(SK)"),
            (stats_item, "attribute_not_exists(PK) AND attribute_not_exists(SK)"),
        ])
        if not success:
            return conflict(f"Event '{event_id}' already exists.")

        logger.info("Admin created event", extra={"eventId": event_id})
        return created(Event.from_item(event_item).to_api_response())

    except Exception:
        logger.exception("Unexpected error in admin event create")
        return internal_error()
