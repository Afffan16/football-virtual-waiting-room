# DynamoDB Physical Table Schema

Author: Muhammad Affan bin Aamir

Version: 1.0

---

# Purpose

This document defines the physical DynamoDB table used by the Football Virtual Waiting Room.

The solution follows a **Single Table Design**, storing all application entities in one table while differentiating them using structured partition keys, sort keys, and item attributes.

The schema is optimized for the access patterns identified earlier and leaves room for future horizontal scaling techniques such as write sharding.

---

# Table Information

| Property | Value |
|----------|-------|
| Table Name | FootballWaitingRoom |
| Billing Mode | On-Demand |
| Primary Key | PK + SK |
| Streams | Enabled (NEW_AND_OLD_IMAGES) |
| TTL | Enabled |
| Point-in-Time Recovery | Enabled |
| Server-Side Encryption | Enabled |

---

# Primary Key

The table uses a composite primary key.

Partition Key

```
PK
```

Sort Key

```
SK
```

---

# Key Naming Convention

To support multiple entity types inside one table, every key follows a predictable prefix strategy.

Examples

```
EVENT#1001

USER#501

QUEUE#501

TOKEN#ABC123

SESSION#XYZ

STATS
```

---

# Entity Layout

## Event Item

PK

```
EVENT#1001
```

SK

```
METADATA
```

Example Attributes

| Attribute | Description |
|-----------|-------------|
| eventId | Unique event identifier |
| matchName | Name of football match |
| stadium | Stadium |
| capacity | Maximum tickets |
| startTime | Match start |
| status | Event status |

---

## Queue Entry

PK

```
EVENT#1001
```

SK

```
QUEUE#00000123
```

Example Attributes

| Attribute | Description |
|-----------|-------------|
| userId | User |
| queuePosition | Immutable queue position |
| joinTime | Registration time |
| status | WAITING / ADMITTED / COMPLETED |
| estimatedWait | Estimated wait |
| shardId | Optional future optimization |

---

## User Item

PK

```
USER#501
```

SK

```
PROFILE
```

Attributes

| Attribute | Description |
|-----------|-------------|
| userId | User identifier |
| name | Full name |
| email | Email |
| createdAt | Registration timestamp |

---

## Session Item

PK

```
USER#501
```

SK

```
SESSION#ACTIVE
```

Attributes

| Attribute | Description |
|-----------|-------------|
| sessionId | Session identifier |
| lastActivity | Last heartbeat |
| device | Device information |
| ttl | Expiration timestamp |

---

## Admission Token

PK

```
TOKEN#ABC123
```

SK

```
METADATA
```

Attributes

| Attribute | Description |
|-----------|-------------|
| tokenId | Token |
| userId | Owner |
| eventId | Associated event |
| expiresAt | TTL |
| status | ACTIVE / USED / EXPIRED |

---

## Statistics Item

PK

```
EVENT#1001
```

SK

```
STATS
```

Attributes

| Attribute | Description |
|-----------|-------------|
| waitingUsers | Current queue size |
| admittedUsers | Users admitted |
| expiredUsers | Expired sessions |
| avgWaitTime | Average wait |

---

# Shared Attributes

Some attributes appear on multiple item types.

| Attribute | Purpose |
|-----------|---------|
| createdAt | Creation timestamp |
| updatedAt | Last modification |
| status | Current state |
| ttl | Expiration |
| entityType | Logical item type |

---

# Queue Status Values

```
WAITING

ADMITTED

COMPLETED

EXPIRED

CANCELLED
```

---

# Token Status Values

```
ACTIVE

USED

EXPIRED
```

---

# Event Status Values

```
UPCOMING

OPEN

CLOSED

FINISHED
```

---

# TTL Configuration

TTL Attribute

```
ttl
```

Applied To

- Session Items
- Admission Tokens

Benefits

- Automatic cleanup
- Lower storage costs
- No scheduled cleanup jobs

---

# Example Items

## Event

```json
{
  "PK": "EVENT#1001",
  "SK": "METADATA",
  "entityType": "EVENT",
  "matchName": "Manchester United vs Liverpool",
  "capacity": 50000,
  "status": "OPEN"
}
```

---

## Queue Entry

```json
{
  "PK": "EVENT#1001",
  "SK": "QUEUE#00000123",
  "entityType": "QUEUE",
  "userId": "501",
  "queuePosition": 123,
  "status": "WAITING",
  "joinTime": "2026-07-08T12:00:00Z"
}
```

---

## Token

```json
{
  "PK": "TOKEN#ABC123",
  "SK": "METADATA",
  "entityType": "TOKEN",
  "userId": "501",
  "status": "ACTIVE",
  "expiresAt": 1783525200,
  "ttl": 1783525200
}
```

---

# Item Collection

Example item collection for Event 1001

```
EVENT#1001
│
├── METADATA
├── STATS
├── QUEUE#000001
├── QUEUE#000002
├── QUEUE#000003
├── QUEUE#000004
└── QUEUE#000005
```

---

# Design Considerations

## Why Single Table?

- Fewer network requests
- Better performance
- Lower operational complexity
- Native DynamoDB best practice

---

## Why Composite Keys?

Composite keys enable:

- Ordered queue retrieval
- Efficient event grouping
- Multiple entity types
- Range queries

---

## Why Immutable Queue Positions?

Instead of moving every user forward when someone leaves:

- Queue positions remain fixed.
- Only status changes.

This significantly reduces write operations.

---

## Future Scalability

If write throughput becomes extremely high:

Queue entries can transition from

```
PK = EVENT#1001
```

to

```
PK = EVENT#1001#SHARD#07
```

without changing the external API contract.

---

# Summary

This schema provides:

- Single-table architecture
- Query-first design
- Efficient grouping
- Ordered queue traversal
- Automatic cleanup
- Minimal storage duplication
- Future-ready scalability