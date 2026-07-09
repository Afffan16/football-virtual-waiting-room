"""
Queue Status Lambda — Retrieves a user's current queue position.

Endpoint: GET /queue/status?eventId=...&userId=...

This function:
  1. Extracts eventId and userId from query parameters.
  2. Queries GSI1 to locate the user's queue entry.
  3. Returns the queue position, status, and estimated wait time.
"""

from __future__ import annotations

from typing import Any

from common.dynamodb import query_user_queue
from common.logger import logger
from common.models import QueueEntry
from common.responses import bad_request, internal_error, not_found, success
from common.utils import get_query_parameter


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """API Gateway proxy handler for GET /queue/status."""
    try:
        # ----- Extract query parameters -----
        event_id = get_query_parameter(event, "eventId")
        user_id = get_query_parameter(event, "userId")

        if not event_id or not user_id:
            return bad_request("Query parameters 'eventId' and 'userId' are required.")

        # ----- Sanitize input lengths -----
        if len(event_id) > 64 or len(user_id) > 128:
            return bad_request("eventId or userId exceeds maximum allowed length.")

        logger.append_keys(eventId=event_id, userId=user_id)
        logger.info("Processing queue status request")

        # ----- Query GSI1 for user's queue entry -----
        item = query_user_queue(user_id, event_id)
        if not item:
            return not_found(f"No queue entry found for user '{user_id}' in event '{event_id}'.")

        # ----- Build response -----
        entry = QueueEntry.from_item(item)
        logger.info("Queue status retrieved", extra={"queuePosition": entry.queue_position, "status": entry.status})

        return success(entry.to_api_response())

    except Exception:
        logger.exception("Unexpected error in queue_status")
        return internal_error()
