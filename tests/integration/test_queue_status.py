"""Integration tests for the Queue Status Lambda handler."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import MockLambdaContext, make_apigw_event


def _join_user(seeded_table: Any, lambda_context: MockLambdaContext, user_id: str = "user_001") -> None:
    from join_queue.app import lambda_handler

    event = make_apigw_event(body={"eventId": "1001", "userId": user_id})
    lambda_handler(event, lambda_context)


class TestQueueStatusHandler:
    """Tests for queue_status.app.lambda_handler."""

    def test_queue_status_success(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from queue_status.app import lambda_handler

        _join_user(seeded_table, lambda_context)

        event = make_apigw_event(
            query_string_parameters={"eventId": "1001", "userId": "user_001"},
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["userId"] == "user_001"
        assert body["status"] == "WAITING"
        assert "queuePosition" in body

    def test_queue_status_missing_params(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from queue_status.app import lambda_handler

        event = make_apigw_event(
            query_string_parameters={"eventId": "1001"},
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 400

    def test_queue_status_user_not_found(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from queue_status.app import lambda_handler

        event = make_apigw_event(
            query_string_parameters={"eventId": "1001", "userId": "ghost"},
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 404

    def test_queue_status_no_query_params(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from queue_status.app import lambda_handler

        event = make_apigw_event(
            query_string_parameters=None,
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 400
