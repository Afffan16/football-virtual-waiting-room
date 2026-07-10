"""Load tests — simulate concurrent user registrations and measure throughput.

These tests validate that the system handles batch operations correctly
and that atomic counters produce unique positions under load.

NOTE: These run against moto (mocked DynamoDB), so they test correctness
under load rather than actual AWS throughput. For real performance testing,
deploy and use a tool like Artillery or Locust against the live API.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import MockLambdaContext, make_admin_apigw_event, make_apigw_event


class TestLoadJoinQueue:
    """Simulate load on the Join Queue endpoint."""

    def test_100_users_all_get_unique_positions(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        """Register 100 users and verify every queue position is unique."""
        from src.join_queue.app import lambda_handler

        positions: set[int] = set()
        count = 100

        for i in range(1, count + 1):
            event = make_apigw_event(body={"eventId": "1001", "userId": f"load_user_{i:04d}"})
            response = lambda_handler(event, lambda_context)
            assert response["statusCode"] == 201, f"User {i} failed to join"

            body = json.loads(response["body"])
            positions.add(body["queuePosition"])

        # Every user must have a unique position
        assert len(positions) == count

    def test_50_users_join_and_stats_consistent(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        """Register 50 users and verify stats counters are consistent."""
        from src.join_queue.app import lambda_handler

        count = 50
        for i in range(1, count + 1):
            event = make_apigw_event(body={"eventId": "1001", "userId": f"stat_user_{i:04d}"})
            lambda_handler(event, lambda_context)

        from src.common.dynamodb import get_event_stats
        stats = get_event_stats("1001")
        assert int(stats["totalUsers"]) == count
        assert int(stats["waitingUsers"]) == count


class TestLoadAdmitUsers:
    """Simulate batch admission under load."""

    def test_admit_in_batches(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        """Register 30 users, then admit them in batches of 10."""
        from src.admit_users.app import lambda_handler as admit_handler
        from src.join_queue.app import lambda_handler as join_handler

        total = 30
        batch_size = 10

        for i in range(1, total + 1):
            event = make_apigw_event(body={"eventId": "1001", "userId": f"batch_user_{i:04d}"})
            join_handler(event, lambda_context)

        total_admitted = 0
        for _ in range(total // batch_size):
            event = make_admin_apigw_event(body={"eventId": "1001", "batchSize": batch_size})
            response = admit_handler(event, lambda_context)
            body = json.loads(response["body"])
            total_admitted += body["admittedUsers"]

        assert total_admitted == total

        # Verify stats
        from src.common.dynamodb import get_event_stats
        stats = get_event_stats("1001")
        assert int(stats["admittedUsers"]) == total


class TestLoadEndToEndFlow:
    """Simulate a full end-to-end user journey at scale."""

    def test_join_admit_validate_flow(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        """Register 10 users, admit them, and validate their tokens."""
        from src.admit_users.app import lambda_handler as admit_handler
        from src.join_queue.app import lambda_handler as join_handler
        from src.validate_token.app import lambda_handler as validate_handler

        # 1. Join 10 users
        for i in range(1, 11):
            event = make_apigw_event(body={"eventId": "1001", "userId": f"e2e_user_{i:03d}"})
            response = join_handler(event, lambda_context)
            assert response["statusCode"] == 201

        # 2. Admit all
        admit_event = make_admin_apigw_event(body={"eventId": "1001", "batchSize": 10})
        admit_response = admit_handler(admit_event, lambda_context)
        admit_body = json.loads(admit_response["body"])
        assert admit_body["admittedUsers"] == 10

        # 3. Find tokens and validate them
        from boto3.dynamodb.conditions import Attr
        token_items = seeded_table.scan(
            FilterExpression=Attr("entityType").eq("TOKEN"),
        )["Items"]

        assert len(token_items) == 10

        for token_item in token_items:
            token_id = token_item["tokenId"]
            event = make_apigw_event(body={"token": token_id})
            response = validate_handler(event, lambda_context)
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["valid"] is True
