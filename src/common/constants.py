"""
Application constants for the Football Virtual Waiting Room.

Centralizes table names, key prefixes, status enums, GSI names,
TTL defaults, and other configuration values used across all
Lambda functions.
"""

import os

# ---------------------------------------------------------------------------
# DynamoDB Configuration
# ---------------------------------------------------------------------------
TABLE_NAME: str = os.environ.get("TABLE_NAME", "FootballWaitingRoom")

# ---------------------------------------------------------------------------
# Key Prefixes — Single Table Design
# ---------------------------------------------------------------------------
EVENT_PREFIX: str = "EVENT#"
USER_PREFIX: str = "USER#"
QUEUE_PREFIX: str = "QUEUE#"
TOKEN_PREFIX: str = "TOKEN#"
SESSION_PREFIX: str = "SESSION#"

# Sort Key Constants
METADATA_SK: str = "METADATA"
STATS_SK: str = "STATS"
PROFILE_SK: str = "PROFILE"
SESSION_ACTIVE_SK: str = "SESSION#ACTIVE"

# ---------------------------------------------------------------------------
# GSI Names
# ---------------------------------------------------------------------------
GSI1_NAME: str = "GSI1"  # User Queue Lookup
GSI2_NAME: str = "GSI2"  # Token Lookup
GSI3_NAME: str = "GSI3"  # Administrative Queue View

# GSI Key Attribute Names
GSI1PK: str = "GSI1PK"
GSI1SK: str = "GSI1SK"
GSI2PK: str = "GSI2PK"
GSI2SK: str = "GSI2SK"
GSI3PK: str = "GSI3PK"
GSI3SK: str = "GSI3SK"

# ---------------------------------------------------------------------------
# Entity Types
# ---------------------------------------------------------------------------
ENTITY_EVENT: str = "EVENT"
ENTITY_USER: str = "USER"
ENTITY_QUEUE: str = "QUEUE"
ENTITY_TOKEN: str = "TOKEN"
ENTITY_SESSION: str = "SESSION"
ENTITY_STATS: str = "STATS"

# ---------------------------------------------------------------------------
# Queue Status Values
# ---------------------------------------------------------------------------
STATUS_WAITING: str = "WAITING"
STATUS_ADMITTED: str = "ADMITTED"
STATUS_COMPLETED: str = "COMPLETED"
STATUS_EXPIRED: str = "EXPIRED"
STATUS_CANCELLED: str = "CANCELLED"

VALID_QUEUE_STATUSES: set[str] = {
    STATUS_WAITING,
    STATUS_ADMITTED,
    STATUS_COMPLETED,
    STATUS_EXPIRED,
    STATUS_CANCELLED,
}

# ---------------------------------------------------------------------------
# Token Status Values
# ---------------------------------------------------------------------------
TOKEN_ACTIVE: str = "ACTIVE"
TOKEN_USED: str = "USED"
TOKEN_EXPIRED: str = "EXPIRED"

# ---------------------------------------------------------------------------
# Event Status Values
# ---------------------------------------------------------------------------
EVENT_UPCOMING: str = "UPCOMING"
EVENT_OPEN: str = "OPEN"
EVENT_CLOSED: str = "CLOSED"
EVENT_FINISHED: str = "FINISHED"

# ---------------------------------------------------------------------------
# TTL Defaults (minutes)
# ---------------------------------------------------------------------------
TOKEN_TTL_MINUTES: int = int(os.environ.get("TOKEN_TTL_MINUTES", "15"))
SESSION_TTL_MINUTES: int = int(os.environ.get("SESSION_TTL_MINUTES", "30"))

# ---------------------------------------------------------------------------
# Admission Defaults
# ---------------------------------------------------------------------------
DEFAULT_BATCH_SIZE: int = int(os.environ.get("DEFAULT_BATCH_SIZE", "50"))

# ---------------------------------------------------------------------------
# Stretch Goal — Active Purchaser Cap
# ---------------------------------------------------------------------------
# Maximum number of fans allowed in the ADMITTED/purchasing state at once.
# When admitted users complete or expire, the admit endpoint auto-refills
# up to this limit. Set via SAM parameter PurchasingCapacity.
PURCHASING_CAPACITY: int = int(os.environ.get("PURCHASING_CAPACITY", "1000"))

# ---------------------------------------------------------------------------
# Queue Position Formatting
# ---------------------------------------------------------------------------
QUEUE_POSITION_PAD_LENGTH: int = 10  # Zero-pad to 10 digits

# ---------------------------------------------------------------------------
# Estimated Wait Configuration
# ---------------------------------------------------------------------------
ESTIMATED_SECONDS_PER_POSITION: int = 5  # Rough estimate for wait calculation
