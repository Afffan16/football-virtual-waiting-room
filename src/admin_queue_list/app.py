"""Admin queue listing Lambda."""

from __future__ import annotations

from typing import Any

from common.auth import is_admin_authorized
from common.constants import VALID_QUEUE_STATUSES
from common.dynamodb import get_event_stats, query_queue_entries
from common.logger import logger
from common.responses import bad_request, forbidden, internal_error, success
from common.utils import get_query_parameter


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """API Gateway proxy handler for GET /queue/admin/list."""
    try:
        if not is_admin_authorized(event):
            return forbidden("Admin authorization required.")

        event_id = get_query_parameter(event, "eventId")
        if not event_id:
            return bad_request("Query parameter 'eventId' is required.")

        status = get_query_parameter(event, "status")
        if status == "ALL":
            status = None
        if status and status not in VALID_QUEUE_STATUSES:
            return bad_request("status must be one of WAITING, ADMITTED, COMPLETED, EXPIRED, CANCELLED, or ALL.")

        try:
            limit = int(get_query_parameter(event, "limit") or "100")
        except ValueError:
            return bad_request("limit must be a number.")
        limit = max(1, min(limit, 500))

        logger.append_keys(eventId=event_id)
        items = query_queue_entries(event_id, status=status, limit=limit)
        stats = get_event_stats(event_id) or {}

        entries = [
            {
                "eventId": item.get("eventId", ""),
                "userId": item.get("userId", ""),
                "queuePosition": item.get("queuePosition", ""),
                "status": item.get("status", ""),
                "joinTime": item.get("joinTime", ""),
                "estimatedWaitMinutes": int(item.get("estimatedWait", 0)),
                "admissionTime": item.get("admissionTime", ""),
            }
            for item in items
        ]

        return success({
            "eventId": event_id,
            "entries": entries,
            "count": len(entries),
            "stats": {
                "waitingUsers": int(stats.get("waitingUsers", 0)),
                "admittedUsers": int(stats.get("admittedUsers", 0)),
                "cancelledUsers": int(stats.get("cancelledUsers", 0)),
                "expiredUsers": int(stats.get("expiredUsers", 0)),
                "completedUsers": int(stats.get("completedUsers", 0)),
                "totalUsers": int(stats.get("totalUsers", 0)),
            },
        })

    except Exception:
        logger.exception("Unexpected error in admin_queue_list")
        return internal_error()
