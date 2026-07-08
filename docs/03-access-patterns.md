# Access Pattern Analysis

Author: Muhammad Affan bin Aamir

Version: 1.0

---

# Purpose

Amazon DynamoDB is designed around **access patterns**, not entity relationships.

Unlike relational databases, where tables are created first and queries are written later, DynamoDB requires us to identify every application query before designing the table schema.

This document defines every operation the Football Virtual Waiting Room must support and maps each operation to an efficient DynamoDB access strategy.

---

# Design Goals

Every access pattern should satisfy the following objectives:

- Query-based retrieval only
- No table scans
- Single-digit millisecond latency
- Horizontal scalability
- Minimal read and write costs
- Efficient partition utilization

---

# Core Access Patterns

The application supports the following major operations.

| ID | Operation | Priority |
|----|-----------|----------|
| AP-01 | Join Queue | High |
| AP-02 | Check Queue Status | High |
| AP-03 | Get Event Information | High |
| AP-04 | Admit Next Users | High |
| AP-05 | Generate Admission Token | High |
| AP-06 | Validate Token | High |
| AP-07 | Remove Expired Session | Medium |
| AP-08 | Update Queue Status | Medium |
| AP-09 | List Users for Event (Admin) | Low |
| AP-10 | View Queue Statistics | Low |

---

# AP-01 — Join Queue

## Description

A user joins the waiting room for a football event.

---

## Input

- User ID
- Event ID
- Join Timestamp

---

## Output

- Queue Position
- Queue Status

---

## DynamoDB Operation

PutItem

---

## Requirements

- Prevent duplicate registrations.
- Assign queue metadata.
- Write should complete in milliseconds.

---

## Conditional Expression

```

attribute_not_exists(PK)

```

---

## Expected Cost

1 Write Capacity Unit

---

# AP-02 — Check Queue Status

## Description

Retrieve the current waiting status of a user.

---

## Input

User ID

Event ID

---

## Output

- Position
- Status
- Estimated Wait
- Event

---

## DynamoDB Operation

Query

---

## Requirements

No scans.

Should return exactly one queue record.

---

## Frequency

Very High

Users may poll every few seconds.

---

# AP-03 — Retrieve Event Details

## Description

Retrieve football match information.

---

## Input

Event ID

---

## Output

- Match
- Stadium
- Capacity
- Queue Status

---

## DynamoDB Operation

GetItem

---

## Frequency

Medium

---

# AP-04 — Admit Next Users

## Description

Select the next group of users eligible for admission.

---

## Input

Event ID

Batch Size

---

## Output

Users to admit

---

## DynamoDB Operation

Query

Ordered by queue metadata.

---

## Requirements

- Maintain fairness.
- Avoid scans.
- Support configurable admission batch sizes.

---

## Expected Cost

Small query returning only required items.

---

# AP-05 — Generate Admission Token

## Description

Create an access token after admission.

---

## Input

User ID

Event ID

Expiration

---

## Output

Token

---

## DynamoDB Operation

PutItem

---

## Requirements

TTL enabled.

Unique token.

---

# AP-06 — Validate Token

## Description

Validate user admission token before checkout.

---

## Input

Token

---

## Output

Valid

Expired

Invalid

---

## DynamoDB Operation

GetItem

or

Query via GSI

---

## Requirements

Very low latency.

---

# AP-07 — Remove Expired Session

## Description

Automatically remove inactive sessions.

---

## Input

TTL Expiration

---

## DynamoDB Operation

Automatic TTL deletion

---

## Manual Reads

None

---

# AP-08 — Update Queue Status

## Description

Update a user's queue status.

Possible values

- Waiting
- Admitted
- Expired
- Completed
- Cancelled

---

## DynamoDB Operation

UpdateItem

---

## Requirements

Atomic update.

---

# AP-09 — Administrator View

## Description

List users participating in an event.

---

## Input

Event ID

---

## Output

User List

---

## DynamoDB Operation

Query

---

## Usage

Low frequency.

Administrative dashboard only.

---

# AP-10 — Queue Statistics

## Description

Retrieve queue metrics.

---

## Example Metrics

Current Queue Size

Users Admitted

Users Waiting

Expired Sessions

Completion Rate

---

## DynamoDB Operation

Aggregated counters or derived metrics

Avoid expensive scans.

---

# Read vs Write Analysis

| Operation | Read | Write |
|-----------|------|-------|
| Join Queue |  | ✓ |
| Queue Status | ✓ | |
| Event Lookup | ✓ | |
| Admit Users | ✓ | ✓ |
| Token Generation | | ✓ |
| Token Validation | ✓ | |
| Session Expiration | | Automatic |
| Status Update | | ✓ |

---

# Expected Request Distribution

| Operation | Percentage |
|-----------|------------|
| Queue Status | 65% |
| Join Queue | 15% |
| Admit Users | 8% |
| Token Validation | 7% |
| Event Lookup | 3% |
| Admin Operations | 2% |

Observation:

The workload is heavily read-oriented because users continuously check their queue status.

---

# Access Pattern Matrix

| Access Pattern | DynamoDB Operation | Expected Result |
|----------------|-------------------|-----------------|
| Join Queue | PutItem | Queue created |
| Check Queue | Query | Single queue record |
| Event Lookup | GetItem | Event metadata |
| Admit Users | Query | Ordered batch |
| Issue Token | PutItem | Token created |
| Validate Token | GetItem | Token status |
| Update Status | UpdateItem | Status changed |
| Remove Session | TTL | Record deleted |
| Admin Event View | Query | Event users |
| Queue Metrics | Query / Counters | Statistics |

---

# Access Pattern Priority

## Critical

- Join Queue
- Check Queue
- Admit Users
- Validate Token

These operations directly affect end-user experience and must remain highly optimized.

---

## Important

- Update Queue Status
- Token Generation
- Event Lookup

---

## Administrative

- Statistics
- Event Dashboard
- Queue Reports

These operations must never impact customer-facing traffic.

---

# Scalability Considerations

The following challenges must be addressed during schema design.

## Hot Partitions

Millions of users may join the same event simultaneously.

Mitigation:

- Event-based partitioning
- Write sharding (if necessary)
- Adaptive Capacity

---

## Polling Traffic

Users repeatedly check their queue status.

Mitigation:

- Query by User ID
- Lightweight projections
- Efficient indexing

---

## Admission Processing

Users should be admitted in order.

Mitigation:

- Sort Key ordering
- Query with Limit
- Batch updates

---

## Token Validation

Token validation must remain extremely fast.

Mitigation:

- Direct key lookup
- Dedicated GSI if required

---

# Design Decisions Derived from Access Patterns

From this analysis we conclude that the final DynamoDB model must support:

- Fast user lookup
- Fast event lookup
- Ordered queue traversal
- Token lookup
- Automatic expiration
- Atomic updates
- Conditional writes
- Efficient indexing

These requirements will directly influence the Primary Key, Sort Key, and Global Secondary Index design in the next document.