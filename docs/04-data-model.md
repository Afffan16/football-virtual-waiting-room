# Data Model Design

Author: Muhammad Affan bin Aamir

Version: 1.0

---

# Purpose

This document defines the logical data model for the Football Virtual Waiting Room.

The solution follows Amazon DynamoDB's **Single Table Design** methodology, where multiple related entity types are stored within a single table and differentiated using structured keys and item attributes.

The model is optimized for the access patterns identified in the previous document.

---

# Design Principles

The data model follows these principles:

- Single Table Design
- Access Pattern First
- Query Instead of Scan
- Event-Driven Architecture
- Horizontal Scalability
- Automatic Expiration
- Minimal GSIs
- Immutable Queue Entries

---

# High-Level Data Model

The application manages six logical entity types.

```

Football Event
│
├── Queue Entries
│
├── Users
│
├── Admission Tokens
│
├── Sessions
│
└── Queue Statistics

```

Although these appear as separate entities, they are all stored in one DynamoDB table.

---

# Entity 1 — Event

Represents a football match.

Example Attributes

- Event ID
- Match Name
- Stadium
- Capacity
- Start Time
- Queue Status

Example

```

EVENT#1001

```

---

# Entity 2 — User

Represents a registered customer.

Attributes

- User ID
- Name
- Email

Users are global entities and may participate in multiple events.

---

# Entity 3 — Queue Entry

Represents a user's position in a specific event queue.

Attributes

- Queue Position
- Join Time
- Status
- Estimated Wait
- Shard ID
- Admission Time

Status values

- WAITING
- ADMITTED
- COMPLETED
- CANCELLED
- EXPIRED

---

# Entity 4 — Admission Token

Generated when a user is admitted.

Attributes

- Token ID
- User ID
- Event ID
- Expiration
- Status

Token States

- ACTIVE
- USED
- EXPIRED

---

# Entity 5 — Session

Tracks active waiting-room sessions.

Attributes

- Session ID
- Last Activity
- Device ID
- TTL

Sessions expire automatically.

---

# Entity 6 — Queue Statistics

Stores aggregate information.

Examples

- Users Waiting
- Users Admitted
- Queue Length
- Average Wait Time

These values reduce the need for expensive aggregation queries.

---

# Item Types

Each item stored in DynamoDB belongs to one logical type.

| Item Type | Purpose |
|------------|----------|
| EVENT | Football event |
| USER | Customer |
| QUEUE | Queue entry |
| TOKEN | Admission token |
| SESSION | Waiting room session |
| STATS | Aggregate counters |

---

# Logical Relationships

```

EVENT
│
├── many QUEUE entries
│
├── many TOKENS
│
└── one STATS record

USER
│
├── many QUEUE entries
│
├── many TOKENS
│
└── many SESSIONS

```

---

# Queue Lifecycle

```

User Registers

↓

WAITING

↓

ADMITTED

↓

TOKEN ISSUED

↓

CHECKOUT

↓

COMPLETED

```

Alternative paths

```

WAITING

↓

EXPIRED

```

or

```

WAITING

↓

CANCELLED

```

---

# Admission Token Lifecycle

```

Created

↓

Active

↓

Used

```

or

```

Created

↓

Expired

```

TTL automatically removes expired tokens.

---

# Session Lifecycle

```

Session Created

↓

Active

↓

Idle

↓

TTL Expiration

↓

Deleted

```

---

# Data Ownership

| Entity | Owner |
|---------|--------|
| Event | Administrator |
| User | Authentication System |
| Queue Entry | Waiting Room |
| Session | Waiting Room |
| Token | Admission Service |
| Statistics | Queue Manager |

---

# Data Consistency

The following consistency model is used.

Queue Position

Immutable

Queue Status

Mutable

Token Status

Mutable

Session

Mutable

Event

Mostly Immutable

Statistics

Frequently Updated

---

# Queue Position Strategy

Queue positions are assigned when the user joins.

They should never be modified.

Instead of moving users forward in the queue, their status changes as they progress through the admission process.

This minimizes write operations.

---

# Time To Live (TTL)

TTL is enabled for:

- Sessions
- Admission Tokens

Benefits

- Automatic cleanup
- Lower storage cost
- No scheduled jobs

---

# Sharding Strategy

To avoid hot partitions, queue entries should be distributed across logical write shards.

Conceptually:

```

EVENT#1001#SHARD#01

EVENT#1001#SHARD#02

EVENT#1001#SHARD#03

...

EVENT#1001#SHARD#20

```

Users are assigned to a shard using a deterministic hashing strategy (for example, based on User ID).

Benefits

- Even write distribution
- Improved throughput
- Better adaptive capacity

---

# Aggregate Counters

Frequently requested statistics should not require table scans.

Instead, maintain dedicated counter items.

Example

```

Users Waiting

Users Admitted

Users Expired

Average Wait

```

These counters can be updated atomically.

---

# Benefits of the Model

- Supports millions of users
- Query-based access
- Automatic expiration
- Efficient storage
- Minimal duplication
- High scalability
- Low operational cost

---

# Future Extensions

The model can be extended to support:

- VIP queues
- Priority admission
- Multiple ticket categories
- Regional waiting rooms
- Dynamic queue balancing
- Fraud detection
- Multi-region deployments

---

# Summary

The logical data model establishes the core entities and relationships required for the Football Virtual Waiting Room.

The next document converts these logical entities into a concrete DynamoDB table schema, including:

- Partition Keys
- Sort Keys
- Attribute naming conventions
- Item examples
- Global Secondary Indexes