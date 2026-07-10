"""Integration tests for the Leave Queue Lambda handler."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import MockLambdaContext, make_apigw_event


def _join_user(seeded_table: Any, lambda_context: MockLambdaContext, user_id: str = "user_001") -> dict[str, Any]:
    """Helper to register a user before testing leave."""
    from join_queue.app import lambda_handler

    event = make_apigw_event(body={"eventId": "1001", "userId": user_id})
    response = lambda_handler(event, lambda_context)
    return json.loads(response["body"])


class TestLeaveQueueHandler:
    """Tests for leave_queue.app.lambda_handler."""

    def test_leave_queue_success(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from leave_queue.app import lambda_handler

        _join_user(seeded_table, lambda_context)

        event = make_apigw_event(body={"eventId": "1001", "userId": "user_001"})
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "left" in body["message"].lower() or "queue" in body["message"].lower()

    def test_leave_queue_missing_fields(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from leave_queue.app import lambda_handler

        event = make_apigw_event(body={"eventId": "1001"})
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 400

    def test_leave_queue_user_not_found(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from leave_queue.app import lambda_handler

        event = make_apigw_event(body={"eventId": "1001", "userId": "nonexistent"})
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 404

    def test_leave_queue_already_cancelled(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from leave_queue.app import lambda_handler

        _join_user(seeded_table, lambda_context)

        leave_event = make_apigw_event(body={"eventId": "1001", "userId": "user_001"})

        # First leave succeeds
        r1 = lambda_handler(leave_event, lambda_context)
        assert r1["statusCode"] == 200

        # Second leave fails — already CANCELLED
        r2 = lambda_handler(leave_event, lambda_context)
        assert r2["statusCode"] == 409

    def test_leave_queue_updates_stats(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from leave_queue.app import lambda_handler

        _join_user(seeded_table, lambda_context)

        event = make_apigw_event(body={"eventId": "1001", "userId": "user_001"})
        lambda_handler(event, lambda_context)

        from common.dynamodb import get_event_stats
        stats = get_event_stats("1001")
        assert int(stats["cancelledUsers"]) >= 1
