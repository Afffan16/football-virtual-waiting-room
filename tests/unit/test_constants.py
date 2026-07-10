"""Unit tests for common/constants.py — verifies all constants are defined and consistent."""

from __future__ import annotations

from common.constants import (
    DEFAULT_BATCH_SIZE,
    ENTITY_EVENT,
    ENTITY_QUEUE,
    ENTITY_SESSION,
    ENTITY_STATS,
    ENTITY_TOKEN,
    ENTITY_USER,
    ESTIMATED_SECONDS_PER_POSITION,
    EVENT_CLOSED,
    EVENT_FINISHED,
    EVENT_OPEN,
    EVENT_PREFIX,
    EVENT_UPCOMING,
    GSI1_NAME,
    GSI1PK,
    GSI1SK,
    GSI2_NAME,
    GSI2PK,
    GSI2SK,
    GSI3_NAME,
    GSI3PK,
    GSI3SK,
    METADATA_SK,
    PROFILE_SK,
    QUEUE_POSITION_PAD_LENGTH,
    QUEUE_PREFIX,
    QUEUE_SHARD_COUNT,
    QUEUE_SHARD_PREFIX,
    SESSION_ACTIVE_SK,
    SESSION_PREFIX,
    SESSION_TTL_MINUTES,
    STATS_SK,
    STATUS_ADMITTED,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_EXPIRED,
    STATUS_REGISTRATION_CLOSED,
    STATUS_WAITING,
    TABLE_NAME,
    TOKEN_ACTIVE,
    TOKEN_EXPIRED,
    TOKEN_PREFIX,
    TOKEN_TTL_MINUTES,
    TOKEN_USED,
    USER_PREFIX,
    VALID_QUEUE_STATUSES,
)


class TestKeyPrefixes:
    """Verify all key prefixes end with #."""

    def test_event_prefix(self) -> None:
        assert EVENT_PREFIX == "EVENT#"

    def test_user_prefix(self) -> None:
        assert USER_PREFIX == "USER#"

    def test_queue_prefix(self) -> None:
        assert QUEUE_PREFIX == "QUEUE#"

    def test_queue_shard_prefix(self) -> None:
        assert QUEUE_SHARD_PREFIX == "SHARD#"

    def test_token_prefix(self) -> None:
        assert TOKEN_PREFIX == "TOKEN#"

    def test_session_prefix(self) -> None:
        assert SESSION_PREFIX == "SESSION#"


class TestSortKeyConstants:
    """Verify sort key constants."""

    def test_metadata_sk(self) -> None:
        assert METADATA_SK == "METADATA"

    def test_stats_sk(self) -> None:
        assert STATS_SK == "STATS"


class TestGSINames:
    """Verify GSI names and key attribute names."""

    def test_gsi1(self) -> None:
        assert GSI1_NAME == "GSI1"
        assert GSI1PK == "GSI1PK"
        assert GSI1SK == "GSI1SK"

    def test_gsi2(self) -> None:
        assert GSI2_NAME == "GSI2"
        assert GSI2PK == "GSI2PK"
        assert GSI2SK == "GSI2SK"

    def test_gsi3(self) -> None:
        assert GSI3_NAME == "GSI3"
        assert GSI3PK == "GSI3PK"
        assert GSI3SK == "GSI3SK"


class TestStatusValues:
    """Verify status enums."""

    def test_queue_statuses_set(self) -> None:
        assert STATUS_WAITING in VALID_QUEUE_STATUSES
        assert STATUS_ADMITTED in VALID_QUEUE_STATUSES
        assert STATUS_COMPLETED in VALID_QUEUE_STATUSES
        assert STATUS_EXPIRED in VALID_QUEUE_STATUSES
        assert STATUS_CANCELLED in VALID_QUEUE_STATUSES
        assert STATUS_REGISTRATION_CLOSED in VALID_QUEUE_STATUSES
        assert len(VALID_QUEUE_STATUSES) == 6

    def test_token_statuses(self) -> None:
        assert TOKEN_ACTIVE == "ACTIVE"
        assert TOKEN_USED == "USED"
        assert TOKEN_EXPIRED == "EXPIRED"

    def test_event_statuses(self) -> None:
        assert EVENT_UPCOMING == "UPCOMING"
        assert EVENT_OPEN == "OPEN"
        assert EVENT_CLOSED == "CLOSED"
        assert EVENT_FINISHED == "FINISHED"


class TestDefaults:
    """Verify sensible default values."""

    def test_queue_pad_length(self) -> None:
        assert QUEUE_POSITION_PAD_LENGTH == 10

    def test_queue_shard_count(self) -> None:
        assert QUEUE_SHARD_COUNT >= 2

    def test_estimated_seconds_positive(self) -> None:
        assert ESTIMATED_SECONDS_PER_POSITION > 0

    def test_table_name_is_string(self) -> None:
        assert isinstance(TABLE_NAME, str)
        assert len(TABLE_NAME) > 0

    def test_token_ttl_positive(self) -> None:
        assert TOKEN_TTL_MINUTES > 0

    def test_session_ttl_positive(self) -> None:
        assert SESSION_TTL_MINUTES > 0

    def test_default_batch_size_positive(self) -> None:
        assert DEFAULT_BATCH_SIZE > 0
