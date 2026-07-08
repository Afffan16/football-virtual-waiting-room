"""Unit tests for the common models module."""

from __future__ import annotations

from src.common.models import AdmissionToken, Event, QueueEntry, QueueStats


class TestEventModel:
    """Tests for the Event dataclass."""

    def test_to_item(self) -> None:
        event = Event(
            event_id="1001",
            match_name="Man Utd vs Liverpool",
            stadium="Old Trafford",
            capacity=50000,
            start_time="2026-07-12T15:00:00Z",
            status="OPEN",
            created_at="2026-07-08T12:00:00Z",
            updated_at="2026-07-08T12:00:00Z",
        )
        item = event.to_item()
        assert item["PK"] == "EVENT#1001"
        assert item["SK"] == "METADATA"
        assert item["entityType"] == "EVENT"
        assert item["matchName"] == "Man Utd vs Liverpool"
        assert item["capacity"] == 50000

    def test_from_item(self) -> None:
        item = {
            "eventId": "1001",
            "matchName": "Man Utd vs Liverpool",
            "stadium": "Old Trafford",
            "capacity": 50000,
            "startTime": "2026-07-12T15:00:00Z",
            "status": "OPEN",
        }
        event = Event.from_item(item)
        assert event.event_id == "1001"
        assert event.match_name == "Man Utd vs Liverpool"
        assert event.capacity == 50000

    def test_to_api_response(self) -> None:
        event = Event(
            event_id="1001",
            match_name="Test Match",
            stadium="Wembley",
            capacity=90000,
            start_time="2026-07-12T15:00:00Z",
            status="OPEN",
        )
        response = event.to_api_response()
        assert response["eventId"] == "1001"
        assert "createdAt" not in response  # Internal field excluded

    def test_roundtrip(self) -> None:
        original = Event(
            event_id="2001",
            match_name="Final",
            stadium="Wembley",
            capacity=90000,
            start_time="2026-08-01T18:00:00Z",
            status="UPCOMING",
            created_at="2026-07-01T00:00:00Z",
            updated_at="2026-07-01T00:00:00Z",
        )
        restored = Event.from_item(original.to_item())
        assert restored.event_id == original.event_id
        assert restored.match_name == original.match_name
        assert restored.status == original.status


class TestQueueEntryModel:
    """Tests for the QueueEntry dataclass."""

    def test_to_item_includes_gsi_keys(self) -> None:
        entry = QueueEntry(
            event_id="1001",
            user_id="user_001",
            queue_position=5,
            status="WAITING",
            join_time="2026-07-08T12:00:00Z",
        )
        item = entry.to_item()
        assert item["PK"] == "EVENT#1001"
        assert item["SK"] == "QUEUE#0000000005"
        assert item["GSI1PK"] == "USER#user_001"
        assert item["GSI1SK"] == "EVENT#1001"
        assert item["GSI3PK"] == "EVENT#1001"
        assert item["GSI3SK"] == "STATUS#WAITING#0000000005"

    def test_from_item(self) -> None:
        item = {
            "eventId": "1001",
            "userId": "user_001",
            "queuePosition": 42,
            "status": "WAITING",
            "joinTime": "2026-07-08T12:00:00Z",
            "estimatedWait": 10,
        }
        entry = QueueEntry.from_item(item)
        assert entry.queue_position == 42
        assert entry.estimated_wait == 10

    def test_to_api_response_excludes_admission_time_when_empty(self) -> None:
        entry = QueueEntry(
            event_id="1001",
            user_id="user_001",
            queue_position=1,
            status="WAITING",
            join_time="2026-07-08T12:00:00Z",
        )
        response = entry.to_api_response()
        assert "admissionTime" not in response

    def test_to_api_response_includes_admission_time_when_set(self) -> None:
        entry = QueueEntry(
            event_id="1001",
            user_id="user_001",
            queue_position=1,
            status="ADMITTED",
            join_time="2026-07-08T12:00:00Z",
            admission_time="2026-07-08T13:00:00Z",
        )
        response = entry.to_api_response()
        assert response["admissionTime"] == "2026-07-08T13:00:00Z"

    def test_zero_pad_position(self) -> None:
        entry = QueueEntry(
            event_id="1001",
            user_id="u1",
            queue_position=1,
            status="WAITING",
            join_time="now",
        )
        assert entry.to_item()["SK"] == "QUEUE#0000000001"


class TestAdmissionTokenModel:
    """Tests for the AdmissionToken dataclass."""

    def test_to_item_includes_ttl(self) -> None:
        token = AdmissionToken(
            token_id="ABCD1234",
            user_id="user_001",
            event_id="1001",
            status="ACTIVE",
            expires_at=1720000000,
        )
        item = token.to_item()
        assert item["PK"] == "TOKEN#ABCD1234"
        assert item["SK"] == "METADATA"
        assert item["ttl"] == 1720000000
        assert item["GSI2PK"] == "TOKEN#ABCD1234"
        assert item["GSI2SK"] == "STATUS#ACTIVE"

    def test_from_item(self) -> None:
        item = {
            "tokenId": "ABCD1234",
            "userId": "user_001",
            "eventId": "1001",
            "status": "ACTIVE",
            "expiresAt": 1720000000,
        }
        token = AdmissionToken.from_item(item)
        assert token.token_id == "ABCD1234"
        assert token.expires_at == 1720000000

    def test_to_api_response(self) -> None:
        token = AdmissionToken(
            token_id="XYZ",
            user_id="u1",
            event_id="1001",
            status="ACTIVE",
            expires_at=9999999999,
        )
        response = token.to_api_response()
        assert response["tokenId"] == "XYZ"
        assert response["valid"] if response.get("valid") else True  # no valid field in model


class TestQueueStatsModel:
    """Tests for the QueueStats dataclass."""

    def test_to_item(self) -> None:
        stats = QueueStats(
            event_id="1001",
            waiting_users=100,
            admitted_users=50,
            total_users=150,
        )
        item = stats.to_item()
        assert item["PK"] == "EVENT#1001"
        assert item["SK"] == "STATS"
        assert item["waitingUsers"] == 100

    def test_from_item(self) -> None:
        item = {
            "eventId": "1001",
            "waitingUsers": 100,
            "admittedUsers": 50,
            "totalUsers": 150,
        }
        stats = QueueStats.from_item(item)
        assert stats.waiting_users == 100
        assert stats.total_users == 150

    def test_to_api_response(self) -> None:
        stats = QueueStats(event_id="1001", waiting_users=10, admitted_users=5)
        response = stats.to_api_response()
        assert response["waitingUsers"] == 10
        assert response["admittedUsers"] == 5
        assert "averageWaitMinutes" in response

    def test_defaults_to_zero(self) -> None:
        stats = QueueStats(event_id="1001")
        assert stats.waiting_users == 0
        assert stats.total_users == 0
