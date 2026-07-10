"""API-level tests — validate response structure and contracts.

These tests verify the shape of API responses matches what clients
expect, ensuring backward compatibility.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import MockLambdaContext, make_admin_apigw_event, make_apigw_event


class TestJoinQueueApiContract:
    """Verify Join Queue response structure."""

    def test_success_response_shape(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.join_queue.app import lambda_handler

        event = make_apigw_event(body={"eventId": "1001", "userId": "api_user_001"})
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert "message" in body
        assert "queuePosition" in body
        assert "status" in body
        assert "estimatedWaitMinutes" in body
        assert isinstance(body["queuePosition"], str)
        assert isinstance(body["estimatedWaitMinutes"], int)

    def test_error_response_shape(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.join_queue.app import lambda_handler

        event = make_apigw_event(body={})
        response = lambda_handler(event, lambda_context)

        body = json.loads(response["body"])
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]


class TestQueueStatusApiContract:
    """Verify Queue Status response structure."""

    def test_success_response_shape(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.join_queue.app import lambda_handler as join_handler
        from src.queue_status.app import lambda_handler

        # Join first
        join_event = make_apigw_event(body={"eventId": "1001", "userId": "api_user_001"})
        join_handler(join_event, lambda_context)

        event = make_apigw_event(
            query_string_parameters={"eventId": "1001", "userId": "api_user_001"},
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)

        body = json.loads(response["body"])
        assert "eventId" in body
        assert "userId" in body
        assert "queuePosition" in body
        assert "status" in body
        assert "estimatedWaitMinutes" in body


class TestEventLookupApiContract:
    """Verify Event Lookup response structure."""

    def test_success_response_shape(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.event_lookup.app import lambda_handler

        event = make_apigw_event(
            path_parameters={"eventId": "1001"},
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)

        body = json.loads(response["body"])
        assert "eventId" in body
        assert "matchName" in body
        assert "stadium" in body
        assert "capacity" in body
        assert "startTime" in body
        assert "status" in body


class TestStatisticsApiContract:
    """Verify Statistics response structure."""

    def test_success_response_shape(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.statistics.app import lambda_handler

        event = make_apigw_event(
            path_parameters={"eventId": "1001"},
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)

        body = json.loads(response["body"])
        assert "eventId" in body
        assert "waitingUsers" in body
        assert "admittedUsers" in body
        assert "totalUsers" in body
        assert "averageWaitMinutes" in body


class TestLeaveQueueApiContract:
    """Verify Leave Queue response structure."""

    def test_success_response_shape(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.join_queue.app import lambda_handler as join_handler
        from src.leave_queue.app import lambda_handler

        join_event = make_apigw_event(body={"eventId": "1001", "userId": "api_user_001"})
        join_handler(join_event, lambda_context)

        event = make_apigw_event(body={"eventId": "1001", "userId": "api_user_001"})
        response = lambda_handler(event, lambda_context)

        body = json.loads(response["body"])
        assert "message" in body


class TestAdmitUsersApiContract:
    """Verify Admit Users response structure."""

    def test_success_response_shape(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.admit_users.app import lambda_handler

        event = make_admin_apigw_event(body={"eventId": "1001", "batchSize": 5})
        response = lambda_handler(event, lambda_context)

        body = json.loads(response["body"])
        assert "admittedUsers" in body
        assert "remainingQueue" in body
        assert "admittedUserIds" in body
        assert isinstance(body["admittedUsers"], int)
        assert isinstance(body["admittedUserIds"], list)


class TestCorsOnAllEndpoints:
    """Verify CORS headers are present on every endpoint's response."""

    def test_join_queue_cors(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.join_queue.app import lambda_handler
        r = lambda_handler(make_apigw_event(body={"eventId": "1001", "userId": "u1"}), lambda_context)
        assert r["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_queue_status_cors(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.queue_status.app import lambda_handler
        r = lambda_handler(make_apigw_event(query_string_parameters=None, http_method="GET"), lambda_context)
        assert r["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_event_lookup_cors(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.event_lookup.app import lambda_handler
        r = lambda_handler(make_apigw_event(path_parameters=None, http_method="GET"), lambda_context)
        assert r["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_statistics_cors(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.statistics.app import lambda_handler
        r = lambda_handler(make_apigw_event(path_parameters=None, http_method="GET"), lambda_context)
        assert r["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_leave_queue_cors(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.leave_queue.app import lambda_handler
        r = lambda_handler(make_apigw_event(body={}), lambda_context)
        assert r["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_admit_users_cors(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.admit_users.app import lambda_handler
        r = lambda_handler(make_apigw_event(body={}), lambda_context)
        assert r["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_validate_token_cors(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from src.validate_token.app import lambda_handler
        r = lambda_handler(make_apigw_event(body={}), lambda_context)
        assert r["headers"]["Access-Control-Allow-Origin"] == "*"
