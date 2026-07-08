"""Unit tests for the common utility module."""

from __future__ import annotations

import json
import time

from src.common.utils import (
    epoch_minutes_from_now,
    estimate_wait_minutes,
    format_queue_position,
    generate_token_id,
    get_path_parameter,
    get_query_parameter,
    parse_body,
    utc_now_epoch,
    utc_now_iso,
    validate_required_fields,
)


class TestUtcNowIso:
    """Tests for utc_now_iso()."""

    def test_returns_iso_format(self) -> None:
        result = utc_now_iso()
        assert result.endswith("Z")
        assert "T" in result

    def test_returns_string(self) -> None:
        assert isinstance(utc_now_iso(), str)


class TestUtcNowEpoch:
    """Tests for utc_now_epoch()."""

    def test_returns_int(self) -> None:
        assert isinstance(utc_now_epoch(), int)

    def test_returns_reasonable_value(self) -> None:
        result = utc_now_epoch()
        assert result > 1_700_000_000  # After 2023


class TestEpochMinutesFromNow:
    """Tests for epoch_minutes_from_now()."""

    def test_adds_minutes(self) -> None:
        before = int(time.time())
        result = epoch_minutes_from_now(10)
        expected_min = before + 600
        assert result >= expected_min
        assert result <= expected_min + 2  # Allow 2s tolerance

    def test_zero_minutes(self) -> None:
        before = int(time.time())
        result = epoch_minutes_from_now(0)
        assert abs(result - before) <= 1


class TestGenerateTokenId:
    """Tests for generate_token_id()."""

    def test_returns_string(self) -> None:
        assert isinstance(generate_token_id(), str)

    def test_returns_uppercase_hex(self) -> None:
        token = generate_token_id()
        assert token == token.upper()
        assert len(token) == 32

    def test_unique(self) -> None:
        tokens = {generate_token_id() for _ in range(100)}
        assert len(tokens) == 100


class TestFormatQueuePosition:
    """Tests for format_queue_position()."""

    def test_pads_to_ten_digits(self) -> None:
        assert format_queue_position(1) == "0000000001"
        assert format_queue_position(42) == "0000000042"

    def test_large_number(self) -> None:
        assert format_queue_position(1234567890) == "1234567890"

    def test_zero(self) -> None:
        assert format_queue_position(0) == "0000000000"


class TestEstimateWaitMinutes:
    """Tests for estimate_wait_minutes()."""

    def test_first_position(self) -> None:
        result = estimate_wait_minutes(1)
        assert result >= 1

    def test_accounts_for_admitted(self) -> None:
        result_high = estimate_wait_minutes(100, admitted_so_far=0)
        result_low = estimate_wait_minutes(100, admitted_so_far=90)
        assert result_low < result_high

    def test_minimum_one_minute(self) -> None:
        assert estimate_wait_minutes(1, admitted_so_far=0) >= 1


class TestParseBody:
    """Tests for parse_body()."""

    def test_parses_json_string(self) -> None:
        event = {"body": '{"key": "value"}'}
        assert parse_body(event) == {"key": "value"}

    def test_none_body(self) -> None:
        assert parse_body({"body": None}) == {}

    def test_missing_body(self) -> None:
        assert parse_body({}) == {}

    def test_invalid_json(self) -> None:
        assert parse_body({"body": "not json"}) == {}

    def test_dict_body(self) -> None:
        event = {"body": {"key": "value"}}
        assert parse_body(event) == {"key": "value"}


class TestGetPathParameter:
    """Tests for get_path_parameter()."""

    def test_extracts_parameter(self) -> None:
        event = {"pathParameters": {"eventId": "1001"}}
        assert get_path_parameter(event, "eventId") == "1001"

    def test_missing_parameter(self) -> None:
        event = {"pathParameters": {"eventId": "1001"}}
        assert get_path_parameter(event, "userId") is None

    def test_none_path_parameters(self) -> None:
        event = {"pathParameters": None}
        assert get_path_parameter(event, "eventId") is None


class TestGetQueryParameter:
    """Tests for get_query_parameter()."""

    def test_extracts_parameter(self) -> None:
        event = {"queryStringParameters": {"eventId": "1001"}}
        assert get_query_parameter(event, "eventId") == "1001"

    def test_missing_parameter(self) -> None:
        event = {"queryStringParameters": {}}
        assert get_query_parameter(event, "eventId") is None

    def test_none_query_parameters(self) -> None:
        event = {"queryStringParameters": None}
        assert get_query_parameter(event, "eventId") is None


class TestValidateRequiredFields:
    """Tests for validate_required_fields()."""

    def test_all_present(self) -> None:
        data = {"eventId": "1001", "userId": "user_001"}
        assert validate_required_fields(data, ["eventId", "userId"]) is None

    def test_missing_field(self) -> None:
        data = {"eventId": "1001"}
        result = validate_required_fields(data, ["eventId", "userId"])
        assert result is not None
        assert "userId" in result

    def test_empty_field(self) -> None:
        data = {"eventId": "1001", "userId": ""}
        result = validate_required_fields(data, ["eventId", "userId"])
        assert result is not None
        assert "userId" in result

    def test_empty_required_list(self) -> None:
        assert validate_required_fields({}, []) is None
