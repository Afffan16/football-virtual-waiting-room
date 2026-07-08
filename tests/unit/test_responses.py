"""Unit tests for the common responses module."""

from __future__ import annotations

import json

from src.common.responses import (
    bad_request,
    conflict,
    created,
    forbidden,
    internal_error,
    no_content,
    not_found,
    success,
    too_many_requests,
    unauthorized,
)


class TestSuccessResponses:
    """Tests for success response builders."""

    def test_success_returns_200(self) -> None:
        response = success({"message": "ok"})
        assert response["statusCode"] == 200

    def test_success_body(self) -> None:
        response = success({"key": "value"})
        body = json.loads(response["body"])
        assert body["key"] == "value"

    def test_created_returns_201(self) -> None:
        response = created({"id": "123"})
        assert response["statusCode"] == 201

    def test_no_content_returns_204(self) -> None:
        response = no_content()
        assert response["statusCode"] == 204
        assert response["body"] == ""


class TestErrorResponses:
    """Tests for error response builders."""

    def test_bad_request_returns_400(self) -> None:
        response = bad_request("Invalid input")
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "BAD_REQUEST"
        assert body["error"]["message"] == "Invalid input"

    def test_unauthorized_returns_401(self) -> None:
        response = unauthorized()
        assert response["statusCode"] == 401

    def test_forbidden_returns_403(self) -> None:
        response = forbidden()
        assert response["statusCode"] == 403

    def test_not_found_returns_404(self) -> None:
        response = not_found("Event not found")
        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "Event not found" in body["error"]["message"]

    def test_conflict_returns_409(self) -> None:
        response = conflict()
        assert response["statusCode"] == 409

    def test_too_many_requests_returns_429(self) -> None:
        response = too_many_requests()
        assert response["statusCode"] == 429

    def test_internal_error_returns_500(self) -> None:
        response = internal_error()
        assert response["statusCode"] == 500


class TestCorsHeaders:
    """Tests for CORS header presence."""

    def test_cors_origin_header(self) -> None:
        response = success({"ok": True})
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_cors_methods_header(self) -> None:
        response = success({"ok": True})
        assert "GET" in response["headers"]["Access-Control-Allow-Methods"]
        assert "POST" in response["headers"]["Access-Control-Allow-Methods"]

    def test_content_type_json(self) -> None:
        response = success({"ok": True})
        assert response["headers"]["Content-Type"] == "application/json"

    def test_error_also_has_cors(self) -> None:
        response = internal_error()
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
