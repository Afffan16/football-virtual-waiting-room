"""
Shared utility functions for the Football Virtual Waiting Room.

Provides input validation, timestamp generation, queue position
formatting, and other helpers used across Lambda functions.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from common.constants import ESTIMATED_SECONDS_PER_POSITION, QUEUE_POSITION_PAD_LENGTH


# ============================================================================
# Timestamp Utilities
# ============================================================================


def utc_now_iso() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now_epoch() -> int:
    """Return the current UTC time as a Unix epoch timestamp (seconds)."""
    return int(time.time())


def epoch_minutes_from_now(minutes: int) -> int:
    """Return a Unix epoch timestamp *minutes* from now."""
    return int(time.time()) + (minutes * 60)


# ============================================================================
# ID Generation
# ============================================================================


def generate_token_id() -> str:
    """Generate a unique admission token identifier."""
    return uuid.uuid4().hex.upper()


# ============================================================================
# Queue Position Utilities
# ============================================================================


def format_queue_position(position: int) -> str:
    """Zero-pad a queue position for use as a DynamoDB sort key."""
    return str(position).zfill(QUEUE_POSITION_PAD_LENGTH)


def estimate_wait_minutes(position: int, admitted_so_far: int = 0) -> int:
    """Provide a rough estimated wait time in minutes.

    This is a simple linear estimate based on queue position and
    the configured processing rate. In production this would be
    replaced with a more sophisticated model.
    """
    remaining = max(0, position - admitted_so_far)
    wait_seconds = remaining * ESTIMATED_SECONDS_PER_POSITION
    return max(1, wait_seconds // 60)


# ============================================================================
# Request Parsing
# ============================================================================


def parse_body(event: dict[str, Any]) -> dict[str, Any]:
    """Parse the JSON body from an API Gateway proxy event.

    Returns an empty dict if the body is missing or cannot be parsed.
    """
    body = event.get("body")
    if body is None:
        return {}
    if isinstance(body, str):
        try:
            return json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return {}
    return body if isinstance(body, dict) else {}


def get_path_parameter(event: dict[str, Any], name: str) -> Optional[str]:
    """Extract a path parameter from an API Gateway proxy event."""
    params = event.get("pathParameters") or {}
    return params.get(name)


def get_query_parameter(event: dict[str, Any], name: str) -> Optional[str]:
    """Extract a query string parameter from an API Gateway proxy event."""
    params = event.get("queryStringParameters") or {}
    return params.get(name)


# ============================================================================
# Validation
# ============================================================================


def validate_required_fields(
    data: dict[str, Any],
    required: list[str],
) -> Optional[str]:
    """Validate that all *required* fields are present and non-empty.

    Returns an error message string if validation fails, otherwise ``None``.
    """
    missing = [f for f in required if not data.get(f)]
    if missing:
        return f"Missing required fields: {', '.join(missing)}"
    return None
