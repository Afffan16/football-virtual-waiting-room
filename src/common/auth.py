"""Authentication helpers for admin-only operations."""

from __future__ import annotations

import hmac
import os
from typing import Any

from common.constants import ADMIN_EMAIL, ADMIN_PASSWORD
from common.logger import logger


def is_admin_authorized(event: dict[str, Any]) -> bool:
    """Return True if an API Gateway event carries valid admin credentials.

    Production deployments should prefer ``x-admin-api-key`` with a secret
    injected by SAM. The email/password fallback supports the static demo
    frontend login flow requested for this project.
    """
    headers: dict[str, str] = {
        k.lower(): v
        for k, v in (event.get("headers") or {}).items()
    }

    expected_api_key = os.environ.get("ADMIN_API_KEY", "")
    provided_key = headers.get("x-admin-api-key", "")
    if expected_api_key and hmac.compare_digest(provided_key, expected_api_key):
        return True

    provided_email = headers.get("x-admin-email", "")
    provided_password = headers.get("x-admin-password", "")
    if provided_email and provided_password:
        return (
            hmac.compare_digest(provided_email, ADMIN_EMAIL)
            and hmac.compare_digest(provided_password, ADMIN_PASSWORD)
        )

    if not expected_api_key:
        logger.warning("ADMIN_API_KEY is not set; only demo admin credentials can authorize admin requests")

    return False
