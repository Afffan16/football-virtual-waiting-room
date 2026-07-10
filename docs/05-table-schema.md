# 🗄️ DynamoDB Physical Table Schema

**Author:** Muhammad Affan bin Aamir · **Version:** 1.0 · **Document:** `docs/05-table-schema.md`

← [Back: Data Model](04-data-model.md) · Next: [Index Design →](06-index-design.md)

---

## Table of Contents

- [Purpose](#purpose)
- [Table Information](#table-information)
- [Primary Key](#primary-key)
- [Key Naming Convention](#key-naming-convention)
- [Entity Layout](#entity-layout)
- [Shared Attributes](#shared-attributes)
- [Status Value Reference](#status-value-reference)
- [TTL Configuration](#ttl-configuration)
- [Example Items](#example-items)
- [Item Collection](#item-collection)
- [Design Considerations](#design-considerations)
- [Future Scalability](#future-scalability)

---

## Purpose

This document defines the **physical** DynamoDB table used by the Football Virtual Waiting Room — the concrete implementation of the logical model from [`04-data-model.md`](04-data-model.md).

The solution follows a **Single Table Design**, storing all application entities in one table while differentiating them using structured partition keys, sort keys, and item attributes. The schema is optimized for the access patterns identified in [`03-access-patterns.md`](03-access-patterns.md) and includes the current write-sharding and registration-guard patterns used by the deployed Lambdas.

---

## Table Information

| Property | Value |
|---|---|
| Table Name | CloudFormation-managed table, exported as `FootballWaitingRoomTableName` |
| Billing Mode | On-Demand (`PAY_PER_REQUEST`) |
| Primary Key | `PK` + `SK` |
| Streams | Enabled (`NEW_AND_OLD_IMAGES`) |
| TTL | Enabled |
| Point-in-Time Recovery | Enabled |
| Server-Side Encryption | Enabled |

---

## Primary Key

A composite primary key:

| | |
|---|---|
| **Partition Key** | `PK` |
| **Sort Key** | `SK` |

---

## Key Naming Convention

Every key follows a predictable prefix strategy, so multiple entity types can share one table without collisions:

```
EVENT#1001
USER#501
QUEUE#EVENT#1001
QUEUE#2026-07-10T18:01:22.123456Z#8f4a
TOKEN#ABC123
SESSION#XYZ
STATS
```

---

## Entity Layout

### Event Item

| | |
|---|---|
| **PK** | `EVENT#1001` |
| **SK** | `METADATA` |

| Attribute | Description |
|---|---|
| `eventId` | Unique event identifier |
| `matchName` | Name of football match |
| `stadium` | Stadium |
| `capacity` | Maximum tickets |
| `startTime` | Match start |
| `status` | Event status |

### Queue Registration Guard

| | |
|---|---|
| **PK** | `USER#501` |
| **SK** | `QUEUE#EVENT#1001` |

| Attribute | Description |
|---|---|
| `eventId` | Event registered for |
| `userId` | User identifier |
| `queuePK` | Physical queue row partition key |
| `queueSK` | Physical queue row sort key |
| `status` | Active registration status |

### Queue Entry

| | |
|---|---|
| **PK** | `EVENT#1001` |
| **SK** | `QUEUE#2026-07-10T18:01:22.123456Z#8f4a` |

| Attribute | Description |
|---|---|
| `userId` | User |
| `queuePosition` | Immutable queue position |
| `joinTime` | Registration time |
| `status` | `WAITING` / `ADMITTED` / `COMPLETED` / `CANCELLED` / `EXPIRED` / `REGISTRATION_CLOSED` |
| `estimatedWait` | Estimated wait |
| `shardId` | Stats shard used for high-write events |

### User Item

| | |
|---|---|
| **PK** | `USER#501` |
| **SK** | `PROFILE` |

| Attribute | Description |
|---|---|
| `userId` | User identifier |
| `name` | Full name |
| `email` | Email |
| `createdAt` | Registration timestamp |

### Session Item

| | |
|---|---|
| **PK** | `USER#501` |
| **SK** | `SESSION#ACTIVE` |

| Attribute | Description |
|---|---|
| `sessionId` | Session identifier |
| `lastActivity` | Last heartbeat |
| `device` | Device information |
| `ttl` | Expiration timestamp |

### Admission Token

| | |
|---|---|
| **PK** | `TOKEN#ABC123` |
| **SK** | `METADATA` |

| Attribute | Description |
|---|---|
| `tokenId` | Token |
| `userId` | Owner |
| `eventId` | Associated event |
| `expiresAt` | TTL |
| `status` | `ACTIVE` / `USED` / `EXPIRED` |

### Statistics Item

| | |
|---|---|
| **PK** | `EVENT#1001` |
| **SK** | `STATS` |

| Attribute | Description |
|---|---|
| `waitingUsers` | Current queue size |
| `admittedUsers` | Users admitted |
| `expiredUsers` | Expired sessions |
| `closedUsers` | Users closed when capacity is full |
| `avgWaitTime` | Average wait |

---

## Shared Attributes

Some attributes appear across multiple item types:

| Attribute | Purpose |
|---|---|
| `createdAt` | Creation timestamp |
| `updatedAt` | Last modification |
| `status` | Current state |
| `ttl` | Expiration |
| `entityType` | Logical item type |

---

## Status Value Reference

| Domain | Values |
|---|---|
| **Queue Status** | `WAITING` · `ADMITTED` · `COMPLETED` · `EXPIRED` · `CANCELLED` · `REGISTRATION_CLOSED` |
| **Token Status** | `ACTIVE` · `USED` · `EXPIRED` |
| **Event Status** | `UPCOMING` · `OPEN` · `CLOSED` · `FINISHED` |

---

## TTL Configuration

| | |
|---|---|
| **TTL Attribute** | `ttl` |
| **Applied To** | Session Items, Admission Tokens |
| **Benefits** | Automatic cleanup · lower storage costs · no scheduled cleanup jobs |

---

## Example Items

```json
// Event
{
  "PK": "EVENT#1001",
  "SK": "METADATA",
  "entityType": "EVENT",
  "matchName": "Manchester United vs Liverpool",
  "capacity": 50000,
  "status": "OPEN"
}
```

```json
// Queue Entry
{
  "PK": "EVENT#1001",
  "SK": "QUEUE#2026-07-10T18:01:22.123456Z#8f4a",
  "entityType": "QUEUE",
  "userId": "501",
  "queuePosition": 123,
  "status": "WAITING",
  "joinTime": "2026-07-08T12:00:00Z"
}
```

```json
// Admission Token (TTL-managed)
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

## Item Collection

A single `Query` on `PK = EVENT#1001` returns the entire item collection for that event in one request:

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

## Design Considerations

### Why Single Table?

- Fewer network requests
- Better performance
- Lower operational complexity
- Native DynamoDB best practice

### Why Composite Keys?

- Ordered queue retrieval
- Efficient event grouping
- Multiple entity types in one table
- Range queries

### Why Immutable Queue Positions?

Instead of moving every user forward when someone leaves the queue, positions stay fixed and only `status` changes — significantly reducing write operations. Full reasoning in [`04-data-model.md#queue-position-strategy`](04-data-model.md#queue-position-strategy).

---

## Future Scalability

If write throughput becomes extremely high, queue entries can transition from:

```diff
- PK = EVENT#1001
+ PK = EVENT#1001#SHARD#07
```

**without changing the external API contract.** This is the write-sharding strategy introduced in [`04-data-model.md#sharding-strategy`](04-data-model.md#sharding-strategy) — the schema is deliberately structured so this migration is additive, not a breaking change.

---

## Summary

| Property | Delivered |
|---|---|
| Single-table architecture | ✅ |
| Query-first design | ✅ |
| Efficient grouping | ✅ |
| Ordered queue traversal | ✅ |
| Automatic cleanup | ✅ |
| Minimal storage duplication | ✅ |
| Future-ready scalability | ✅ |

Next: [`06-index-design.md`](06-index-design.md) defines the Global Secondary Indexes (GSI1–GSI3) that support the access patterns this schema alone can't serve directly.
