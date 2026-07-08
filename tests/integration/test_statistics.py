"""Integration tests for the Statistics Lambda handler."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import MockLambdaContext, make_apigw_event


class TestStatisticsHandler:
    """Tests for statistics.app.lambda_handler."""

    def test_statistics_success(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from statistics.app import lambda_handler

        event = make_apigw_event(
            path_parameters={"eventId": "1001"},
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["eventId"] == "1001"
        assert body["waitingUsers"] == 0
        assert body["admittedUsers"] == 0
        assert body["totalUsers"] == 0

    def test_statistics_after_joins(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from join_queue.app import lambda_handler as join_handler
        from statistics.app import lambda_handler

        # Register 3 users
        for i in range(1, 4):
            join_event = make_apigw_event(body={"eventId": "1001", "userId": f"user_{i:03d}"})
            join_handler(join_event, lambda_context)

        event = make_apigw_event(
            path_parameters={"eventId": "1001"},
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["totalUsers"] >= 3
        assert body["waitingUsers"] >= 3

    def test_statistics_not_found(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from statistics.app import lambda_handler

        event = make_apigw_event(
            path_parameters={"eventId": "9999"},
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 404

    def test_statistics_missing_path_param(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from statistics.app import lambda_handler

        event = make_apigw_event(
            path_parameters=None,
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 400
