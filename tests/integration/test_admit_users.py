"""Integration tests for the Admit Users Lambda handler."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import MockLambdaContext, make_admin_apigw_event, make_apigw_event


def _join_users(seeded_table: Any, lambda_context: MockLambdaContext, count: int = 5) -> None:
    """Helper to register multiple users."""
    from join_queue.app import lambda_handler

    for i in range(1, count + 1):
        event = make_apigw_event(body={"eventId": "1001", "userId": f"user_{i:03d}"})
        lambda_handler(event, lambda_context)


class TestAdmitUsersHandler:
    """Tests for admit_users.app.lambda_handler."""

    def test_admit_users_success(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from admit_users.app import lambda_handler

        _join_users(seeded_table, lambda_context, count=3)

        event = make_admin_apigw_event(body={"eventId": "1001", "batchSize": 2})
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["admittedUsers"] == 2
        assert len(body["admittedUserIds"]) == 2
        assert "remainingQueue" in body

    def test_admit_users_no_waiting(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from admit_users.app import lambda_handler

        event = make_admin_apigw_event(body={"eventId": "1001", "batchSize": 5})
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["admittedUsers"] == 0

    def test_admit_users_missing_event_id(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from admit_users.app import lambda_handler

        event = make_admin_apigw_event(body={"batchSize": 5})
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 400

    def test_admit_users_creates_tokens(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from admit_users.app import lambda_handler

        _join_users(seeded_table, lambda_context, count=1)

        event = make_admin_apigw_event(body={"eventId": "1001", "batchSize": 1})
        lambda_handler(event, lambda_context)

        # Scan for TOKEN items
        from boto3.dynamodb.conditions import Key
        response = seeded_table.scan(
            FilterExpression=Key("entityType").eq("TOKEN"),
        )
        assert len(response["Items"]) >= 1

    def test_admit_users_updates_stats(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from admit_users.app import lambda_handler

        _join_users(seeded_table, lambda_context, count=3)

        event = make_admin_apigw_event(body={"eventId": "1001", "batchSize": 3})
        lambda_handler(event, lambda_context)

        from common.dynamodb import get_event_stats
        stats = get_event_stats("1001")
        assert int(stats["admittedUsers"]) == 3

    def test_admit_all_then_admit_again(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from admit_users.app import lambda_handler

        _join_users(seeded_table, lambda_context, count=2)

        # Admit all
        event = make_admin_apigw_event(body={"eventId": "1001", "batchSize": 10})
        r1 = lambda_handler(event, lambda_context)
        body1 = json.loads(r1["body"])
        assert body1["admittedUsers"] == 2

        # Admit again — should find nobody
        r2 = lambda_handler(event, lambda_context)
        body2 = json.loads(r2["body"])
        assert body2["admittedUsers"] == 0
