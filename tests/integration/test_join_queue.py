"""Integration tests for the Join Queue Lambda handler."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import MockLambdaContext, make_apigw_event


class TestJoinQueueHandler:
    """Tests for join_queue.app.lambda_handler."""

    def test_join_queue_success(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from join_queue.app import lambda_handler

        event = make_apigw_event(body={"eventId": "1001", "userId": "user_001"})
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["queuePosition"] == 1
        assert body["status"] == "WAITING"
        assert "estimatedWaitMinutes" in body

    def test_join_queue_missing_fields(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from join_queue.app import lambda_handler

        event = make_apigw_event(body={"eventId": "1001"})
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "userId" in body["error"]["message"]

    def test_join_queue_event_not_found(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from join_queue.app import lambda_handler

        event = make_apigw_event(body={"eventId": "9999", "userId": "user_001"})
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 404

    def test_join_queue_event_not_open(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from join_queue.app import lambda_handler

        # Change event status to CLOSED
        seeded_table.update_item(
            Key={"PK": "EVENT#1001", "SK": "METADATA"},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "CLOSED"},
        )

        event = make_apigw_event(body={"eventId": "1001", "userId": "user_001"})
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 403

    def test_join_queue_duplicate_returns_existing(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from join_queue.app import lambda_handler

        event = make_apigw_event(body={"eventId": "1001", "userId": "user_001"})

        # First join
        response1 = lambda_handler(event, lambda_context)
        assert response1["statusCode"] == 201

        # Second join — should return existing entry
        response2 = lambda_handler(event, lambda_context)
        assert response2["statusCode"] == 201
        body = json.loads(response2["body"])
        assert body["message"] == "Already registered."

    def test_join_queue_increments_position(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from join_queue.app import lambda_handler

        event1 = make_apigw_event(body={"eventId": "1001", "userId": "user_001"})
        event2 = make_apigw_event(body={"eventId": "1001", "userId": "user_002"})

        r1 = lambda_handler(event1, lambda_context)
        r2 = lambda_handler(event2, lambda_context)

        pos1 = json.loads(r1["body"])["queuePosition"]
        pos2 = json.loads(r2["body"])["queuePosition"]
        assert pos2 > pos1

    def test_join_queue_empty_body(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from join_queue.app import lambda_handler

        event = make_apigw_event(body=None)
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 400

    def test_join_queue_updates_stats(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from join_queue.app import lambda_handler

        event = make_apigw_event(body={"eventId": "1001", "userId": "user_001"})
        lambda_handler(event, lambda_context)

        # Check stats were updated
        stats = seeded_table.get_item(Key={"PK": "EVENT#1001", "SK": "STATS"})["Item"]
        assert int(stats["totalUsers"]) >= 1
        assert int(stats["waitingUsers"]) >= 1
