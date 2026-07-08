"""
Event Lookup Lambda — Returns metadata for a specific football event.

Endpoint: GET /event/{eventId}

This function:
  1. Extracts the eventId from path parameters.
  2. Retrieves the event item using the DynamoDB helper.
  3. Returns the event information.
"""

from __future__ import annotations

from typing import Any

from common.dynamodb import get_event
from common.logger import logger
from common.models import Event
from common.responses import bad_request, internal_error, not_found, success
from common.utils import get_path_parameter


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """API Gateway proxy handler for GET /event/{eventId}."""
    try:
        # ----- Extract path parameters -----
        event_id = get_path_parameter(event, "eventId")
        if not event_id:
            return bad_request("Path parameter 'eventId' is required.")

        logger.append_keys(eventId=event_id)
        logger.info("Processing event lookup request")

        # ----- Look up event -----
        item = get_event(event_id)
        if not item:
            return not_found(f"Event '{event_id}' not found.")

        # ----- Build response -----
        event_obj = Event.from_item(item)
        logger.info("Event details retrieved")

        return success(event_obj.to_api_response())

    except Exception:
        logger.exception("Unexpected error in event_lookup")
        return internal_error()
