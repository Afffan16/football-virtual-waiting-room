"""Integration tests for the Event Lookup Lambda handler."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import MockLambdaContext, make_apigw_event


class TestEventLookupHandler:
    """Tests for event_lookup.app.lambda_handler."""

    def test_event_lookup_success(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from event_lookup.app import lambda_handler

        event = make_apigw_event(
            path_parameters={"eventId": "1001"},
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["eventId"] == "1001"
        assert body["matchName"] == "Manchester United vs Liverpool"
        assert body["stadium"] == "Old Trafford"
        assert body["status"] == "OPEN"

    def test_event_lookup_not_found(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from event_lookup.app import lambda_handler

        event = make_apigw_event(
            path_parameters={"eventId": "9999"},
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 404

    def test_event_lookup_missing_path_param(self, seeded_table: Any, lambda_context: MockLambdaContext) -> None:
        from event_lookup.app import lambda_handler

        event = make_apigw_event(
            path_parameters=None,
            http_method="GET",
        )
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 400
