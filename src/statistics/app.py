"""
Statistics Lambda — Returns aggregate queue statistics for an event.

Endpoint: GET /event/{eventId}/stats

This function:
  1. Extracts the eventId from path parameters.
  2. Retrieves the STATS item using the DynamoDB helper.
  3. Returns the aggregated queue statistics.
"""

from __future__ import annotations

from typing import Any

from common.dynamodb import get_event_stats
from common.logger import logger
from common.models import QueueStats
from common.responses import bad_request, internal_error, not_found, success
from common.utils import get_path_parameter


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """API Gateway proxy handler for GET /event/{eventId}/stats."""
    try:
        # ----- Extract path parameters -----
        event_id = get_path_parameter(event, "eventId")
        if not event_id:
            return bad_request("Path parameter 'eventId' is required.")

        logger.append_keys(eventId=event_id)
        logger.info("Processing queue statistics request")

        # ----- Look up event stats -----
        item = get_event_stats(event_id)
        if not item:
            return not_found(f"Statistics not found for event '{event_id}'.")

        # ----- Build response -----
        stats = QueueStats.from_item(item)
        logger.info("Queue statistics retrieved")

        return success(stats.to_api_response())

    except Exception:
        logger.exception("Unexpected error in statistics")
        return internal_error()
