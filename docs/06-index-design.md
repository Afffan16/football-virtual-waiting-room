# Global Secondary Index (GSI) Design

Author: Muhammad Affan bin Aamir

Version: 1.0

---

# Purpose

This document defines the Global Secondary Indexes (GSIs) used by the Football Virtual Waiting Room.

The primary table schema is optimized around event-based access. However, some application queries require looking up data from different perspectives, such as by User ID or Token ID.

GSIs enable these alternate access patterns without requiring table scans.

The design intentionally minimizes the number of GSIs to reduce storage costs, write amplification, and operational complexity.

---

# Index Design Philosophy

Every GSI must satisfy at least one application access pattern.

Indexes are **not** created for convenience.

Each additional index increases:

- Write cost
- Storage cost
- Replication overhead

Therefore, only essential indexes are included.

---

# Overview

| Index | Purpose |
|--------|---------|
| GSI1 | Find Queue Entry by User |
| GSI2 | Find Admission Token |
| GSI3 | Administrative Event Queries (Optional) |

---

# GSI1 — User Queue Lookup

## Purpose

Allows the application to retrieve a user's queue entry without knowing its physical location in the table.

This supports:

- Queue Status
- Resume Session
- Mobile Refresh
- User Dashboard

---

## Partition Key

```
GSI1PK = USER#<UserId>
```

---

## Sort Key

```
GSI1SK = EVENT#<EventId>
```

---

## Example

```
GSI1PK = USER#501

GSI1SK = EVENT#1001
```

---

## Returns

Queue Position

Status

Join Time

Estimated Wait

Event

---

## Supported Access Patterns

✓ Check Queue Status

✓ Resume Waiting Room

✓ View Active Queues

---

## Query Example

```
Query

PK = USER#501
```

---

# GSI2 — Token Lookup

## Purpose

Admission tokens must be validated before allowing users to enter the ticket purchasing system.

Token validation must be extremely fast.

---

## Partition Key

```
GSI2PK = TOKEN#ABC123
```

---

## Sort Key

```
GSI2SK = STATUS
```

---

## Returns

- Token Status
- User
- Event
- Expiration

---

## Supported Access Patterns

✓ Validate Token

✓ Check Expiration

✓ Detect Replay

---

## Query Example

```
Get Token

TOKEN#ABC123
```

---

# GSI3 — Administrative Queue View (Optional)

## Purpose

Provides administrative access to queue data.

Not used by customer-facing APIs.

Useful for:

- Operations Dashboard
- Monitoring
- Analytics

---

## Partition Key

```
GSI3PK = EVENT#1001
```

---

## Sort Key

```
STATUS#WAITING
```

---

## Example

```
EVENT#1001

↓

WAITING
WAITING
WAITING
WAITING
ADMITTED
EXPIRED
```

---

## Supported Queries

Waiting Users

Admitted Users

Completed Users

Expired Users

---

## Benefits

Avoids filtering large datasets.

Supports operational dashboards.

---

# Sparse Indexes

Some indexes only contain specific item types.

Example

GSI2 contains only

```
TOKEN
```

items.

Benefits

- Smaller index
- Lower storage
- Faster queries

---

# Projected Attributes

Only necessary attributes should be projected into each GSI.

---

## GSI1 Projection

Projected Fields

- Queue Position
- Queue Status
- Event ID
- Join Time

Reason

Supports queue lookup without fetching the base item.

---

## GSI2 Projection

Projected Fields

- Status
- Expiration
- User ID

Reason

Enables token validation in one request.

---

## GSI3 Projection

Projected Fields

- Queue Position
- Status
- User ID

Reason

Supports administrative dashboards.

---

# Read Patterns

| Operation | Index |
|------------|-------|
| Queue Status | GSI1 |
| Resume Session | GSI1 |
| Token Validation | GSI2 |
| Admin Dashboard | GSI3 |

---

# Cost Considerations

Each GSI duplicates projected attributes.

To minimize cost:

- Keep projections small.
- Use sparse indexes.
- Avoid unnecessary indexes.
- Prefer GetItem where possible.

---

# Why Not More GSIs?

The following queries can already be satisfied using the primary key:

- Event Details
- Queue Traversal
- Statistics
- Session Retrieval

Creating additional GSIs would increase write costs without providing meaningful performance improvements.

---

# High Availability

GSIs inherit DynamoDB's:

- Automatic replication
- Fault tolerance
- Horizontal scaling

No additional infrastructure is required.

---

# Future Enhancements

If the system evolves, additional GSIs may support:

- VIP Queues
- Premium Ticket Holders
- Regional Waiting Rooms
- Multi-Event Dashboards
- Fraud Detection
- Queue History

These should only be added when justified by new access patterns.

---

# Summary

The proposed index strategy balances performance, scalability, and cost.

| Index | Purpose |
|--------|---------|
| GSI1 | User Queue Lookup |
| GSI2 | Token Validation |
| GSI3 | Administrative Monitoring |

This design satisfies all identified access patterns while minimizing write amplification and storage overhead.