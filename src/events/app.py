"""List football events for the frontend catalog."""

from __future__ import annotations

from typing import Any

from common.dynamodb import list_events
from common.logger import logger
from common.models import Event
from common.responses import internal_error, success


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """API Gateway proxy handler for GET /events."""
    try:
        items = list_events()
        return success({
            "events": [Event.from_item(item).to_api_response() for item in items],
            "count": len(items),
        })
    except Exception:
        logger.exception("Unexpected error in events list")
        return internal_error()
