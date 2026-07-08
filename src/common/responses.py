"""
Standard API response builders for the Football Virtual Waiting Room.

Provides consistent HTTP response formatting across all Lambda functions,
including CORS headers and structured error payloads.
"""

from __future__ import annotations

import json
from typing import Any


# Default CORS headers applied to every response.
_CORS_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": (
        "Content-Type,X-Amz-Date,Authorization,"
        "X-Api-Key,X-Amz-Security-Token,Idempotency-Key"
    ),
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def _build_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Build a standard API Gateway proxy response."""
    return {
        "statusCode": status_code,
        "headers": _CORS_HEADERS,
        "body": json.dumps(body, default=str),
    }


# ---- Success responses ----


def success(body: dict[str, Any]) -> dict[str, Any]:
    """HTTP 200 — OK."""
    return _build_response(200, body)


def created(body: dict[str, Any]) -> dict[str, Any]:
    """HTTP 201 — Created."""
    return _build_response(201, body)


def no_content() -> dict[str, Any]:
    """HTTP 204 — No Content."""
    return {
        "statusCode": 204,
        "headers": _CORS_HEADERS,
        "body": "",
    }


# ---- Error responses ----


def bad_request(message: str = "Invalid request.") -> dict[str, Any]:
    """HTTP 400 — Bad Request."""
    return _build_response(400, {
        "error": {"code": "BAD_REQUEST", "message": message},
    })


def unauthorized(message: str = "Unauthorized.") -> dict[str, Any]:
    """HTTP 401 — Unauthorized."""
    return _build_response(401, {
        "error": {"code": "UNAUTHORIZED", "message": message},
    })


def forbidden(message: str = "Forbidden.") -> dict[str, Any]:
    """HTTP 403 — Forbidden."""
    return _build_response(403, {
        "error": {"code": "FORBIDDEN", "message": message},
    })


def not_found(message: str = "Resource not found.") -> dict[str, Any]:
    """HTTP 404 — Not Found."""
    return _build_response(404, {
        "error": {"code": "RESOURCE_NOT_FOUND", "message": message},
    })


def conflict(message: str = "Resource already exists.") -> dict[str, Any]:
    """HTTP 409 — Conflict."""
    return _build_response(409, {
        "error": {"code": "CONFLICT", "message": message},
    })


def too_many_requests(message: str = "Too many requests.") -> dict[str, Any]:
    """HTTP 429 — Too Many Requests."""
    return _build_response(429, {
        "error": {"code": "TOO_MANY_REQUESTS", "message": message},
    })


def internal_error(message: str = "Internal server error.") -> dict[str, Any]:
    """HTTP 500 — Internal Server Error."""
    return _build_response(500, {
        "error": {"code": "INTERNAL_ERROR", "message": message},
    })
