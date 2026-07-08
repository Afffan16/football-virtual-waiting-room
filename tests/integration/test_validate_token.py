"""Integration tests for the Validate Token Lambda handler."""

from __future__ import annotations

import json
import time
from typing import Any

import pytest

from tests.conftest import MockLambdaContext, make_apigw_event


def _create_token(seeded_table: Any, token_id: str = "TEST_TOKEN_1", expired: bool = False) -> None:
    """Helper to insert a token directly into DynamoDB."""
    expires_at = int(time.time()) + (900 if not expired else -900)
    seeded_table.put_item(Item={
        "PK": f"TOKEN#{token_id}",
        "SK": "METADATA",
        "entityType": "TOKEN",
        "tokenId": token_id,
        "userId": "user_001",
        "eventId": "1001",
        "status": "ACTIVE",
        "expiresAt": expires_at,
        "ttl": expires_at,
        "createdAt": "2026-07-08T12:00:00Z",
        "GSI2PK": f"TOKEN#{token_id}",
        "GSI2SK": "STATUS#ACTIVE",
    })


class TestValidateTokenHandler:
    """Tests for validate_token.app.lambda_handler."""

    def test_validate_token_success(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from validate_token.app import lambda_handler

        _create_token(seeded_table)

        event = make_apigw_event(body={"token": "TEST_TOKEN_1"})
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["valid"] is True
        assert body["userId"] == "user_001"
        assert body["eventId"] == "1001"

    def test_validate_token_not_found(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from validate_token.app import lambda_handler

        event = make_apigw_event(body={"token": "NONEXISTENT"})
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 401

    def test_validate_token_expired(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from validate_token.app import lambda_handler

        _create_token(seeded_table, token_id="EXPIRED_TOKEN", expired=True)

        event = make_apigw_event(body={"token": "EXPIRED_TOKEN"})
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "expired" in body["error"]["message"].lower()

    def test_validate_token_used_status(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from validate_token.app import lambda_handler

        _create_token(seeded_table, token_id="USED_TOKEN")
        # Manually set status to USED
        seeded_table.update_item(
            Key={"PK": "TOKEN#USED_TOKEN", "SK": "METADATA"},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "USED"},
        )

        event = make_apigw_event(body={"token": "USED_TOKEN"})
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 401

    def test_validate_token_missing_field(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from validate_token.app import lambda_handler

        event = make_apigw_event(body={})
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 400
