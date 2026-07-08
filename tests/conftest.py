"""
Shared pytest fixtures for the Football Virtual Waiting Room test suite.

Provides a mock DynamoDB table with the same schema as template.yaml,
pre-seeded test data, and environment variable configuration.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Generator

import boto3
import pytest
from moto import mock_aws

# Ensure src/ is on the path so Lambda code can import `from common.*`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ---------------------------------------------------------------------------
# Environment Variables (set BEFORE importing application code)
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables expected by the application."""
    monkeypatch.setenv("TABLE_NAME", "FootballWaitingRoom")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("TOKEN_TTL_MINUTES", "15")
    monkeypatch.setenv("SESSION_TTL_MINUTES", "30")
    monkeypatch.setenv("DEFAULT_BATCH_SIZE", "50")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


# ---------------------------------------------------------------------------
# DynamoDB Mock Table
# ---------------------------------------------------------------------------
TABLE_NAME = "FootballWaitingRoom"


def _create_table(dynamodb_resource: Any) -> Any:
    """Create the mock DynamoDB table matching template.yaml schema."""
    table = dynamodb_resource.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
            {"AttributeName": "GSI2PK", "AttributeType": "S"},
            {"AttributeName": "GSI2SK", "AttributeType": "S"},
            {"AttributeName": "GSI3PK", "AttributeType": "S"},
            {"AttributeName": "GSI3SK", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI2",
                "KeySchema": [
                    {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI3",
                "KeySchema": [
                    {"AttributeName": "GSI3PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI3SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    table.meta.client.get_waiter("table_exists").wait(TableName=TABLE_NAME)
    return table


@pytest.fixture()
def dynamodb_table() -> Generator[Any, None, None]:
    """Provide a mocked DynamoDB table.

    Patches the common.dynamodb module's internal table reference
    so all application code uses the mock.
    """
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = _create_table(dynamodb)

        # Patch the shared table reference used by all Lambda functions
        import src.common.dynamodb as db_module
        db_module._dynamodb = dynamodb
        db_module._table = table

        yield table


@pytest.fixture()
def seeded_table(dynamodb_table: Any) -> Any:
    """Provide a DynamoDB table pre-seeded with a default event and stats."""
    now = "2026-07-08T12:00:00Z"

    # Event item
    dynamodb_table.put_item(Item={
        "PK": "EVENT#1001",
        "SK": "METADATA",
        "entityType": "EVENT",
        "eventId": "1001",
        "matchName": "Manchester United vs Liverpool",
        "stadium": "Old Trafford",
        "capacity": 50000,
        "startTime": "2026-07-12T15:00:00Z",
        "status": "OPEN",
        "createdAt": now,
        "updatedAt": now,
    })

    # Stats item
    dynamodb_table.put_item(Item={
        "PK": "EVENT#1001",
        "SK": "STATS",
        "entityType": "STATS",
        "eventId": "1001",
        "waitingUsers": 0,
        "admittedUsers": 0,
        "expiredUsers": 0,
        "cancelledUsers": 0,
        "completedUsers": 0,
        "totalUsers": 0,
        "avgWaitTime": 0,
        "createdAt": now,
        "updatedAt": now,
    })

    return dynamodb_table


# ---------------------------------------------------------------------------
# Helper: Build API Gateway proxy event
# ---------------------------------------------------------------------------
def make_apigw_event(
    body: dict[str, Any] | None = None,
    path_parameters: dict[str, str] | None = None,
    query_string_parameters: dict[str, str] | None = None,
    http_method: str = "POST",
) -> dict[str, Any]:
    """Build a minimal API Gateway proxy integration event."""
    event: dict[str, Any] = {
        "httpMethod": http_method,
        "headers": {"Content-Type": "application/json"},
        "pathParameters": path_parameters,
        "queryStringParameters": query_string_parameters,
        "body": json.dumps(body) if body else None,
        "requestContext": {
            "requestId": "test-request-id",
            "stage": "Prod",
        },
    }
    return event


# ---------------------------------------------------------------------------
# Mock Lambda Context (required by @logger.inject_lambda_context)
# ---------------------------------------------------------------------------
class MockLambdaContext:
    """Minimal mock of the AWS Lambda context object."""

    function_name = "test-function"
    memory_limit_in_mb = 256
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
    aws_request_id = "test-request-id-0001"
    log_group_name = "/aws/lambda/test-function"
    log_stream_name = "2026/07/08/[$LATEST]test"

    def get_remaining_time_in_millis(self) -> int:
        return 30000


@pytest.fixture()
def lambda_context() -> MockLambdaContext:
    """Provide a mock Lambda context for handler invocations."""
    return MockLambdaContext()

