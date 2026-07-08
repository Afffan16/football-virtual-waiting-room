# Requirements Analysis

Author: Muhammad Affan bin Aamir

Version: 1.0

---

# Purpose

The goal of this document is to translate the business requirements of the Football Virtual Waiting Room into technical requirements that guide the DynamoDB data model.

Unlike relational databases, Amazon DynamoDB is designed using an **access pattern-first approach**. Therefore, understanding how the application interacts with the data is essential before defining partition keys, sort keys, or indexes.

---

# Business Problem

When tickets for a popular football match are released, millions of users may attempt to access the ticketing platform simultaneously.

Without proper request management:

- Backend systems become overloaded.
- Ticket inventory may become inconsistent.
- Users experience long wait times.
- Fairness cannot be guaranteed.

The Virtual Waiting Room acts as a buffer between users and the ticketing platform by controlling admission based on queue order and system capacity.

---

# Core Business Goals

The solution should:

- Handle sudden traffic spikes.
- Protect backend ticketing systems.
- Ensure fairness in queue processing.
- Scale to millions of concurrent users.
- Provide users with real-time queue updates.
- Automatically clean up expired sessions.
- Minimize infrastructure costs.

---

# Functional Requirements

## FR-01: Register a User

A user should be able to join the waiting room for a specific football event.

### Inputs

- User ID
- Event ID
- Timestamp

### Expected Outcome

- Queue record is created.
- Queue position is assigned.
- User receives confirmation.

### DynamoDB Implications

- Fast write operation
- No duplicate queue entries
- Conditional writes to prevent duplicate registration

---

## FR-02: Retrieve Queue Status

Users should be able to check their current queue status.

### Information Returned

- Queue position
- Queue status
- Estimated waiting time
- Event information

### DynamoDB Implications

- Query by User ID
- No table scans
- Low-latency reads

---

## FR-03: Admit Users

The system periodically admits users from the front of the queue.

### Expected Behaviour

- Users are admitted in order.
- Queue fairness is maintained.
- Admission capacity is configurable.

### DynamoDB Implications

- Efficient retrieval of the next eligible users
- Ordered queries
- Minimal read cost

---

## FR-04: Generate Admission Token

When a user is admitted:

- Generate a temporary access token.
- Associate the token with the user.
- Define an expiration time.

### DynamoDB Implications

- Fast writes
- TTL support
- Token lookup

---

## FR-05: Validate Token

Before accessing ticket purchasing services:

- Validate token.
- Ensure token is active.
- Reject expired tokens.

### DynamoDB Implications

- Query by Token ID
- Very low latency
- No scans

---

## FR-06: Remove Expired Users

Inactive users should automatically leave the queue.

### Expected Behaviour

- Expired records disappear automatically.
- No scheduled cleanup jobs.

### DynamoDB Implications

- DynamoDB TTL
- Automatic expiration

---

## FR-07: Support Multiple Events

The platform must support multiple football matches simultaneously.

### Expected Behaviour

- Independent queues
- Independent capacities
- Independent admission rates

### DynamoDB Implications

- Event-aware partitioning
- Prevent cross-event interference

---

# Non-Functional Requirements

## Scalability

Target:

Millions of concurrent users.

Technical Requirement

- Horizontal scaling
- Partition distribution
- Adaptive capacity

---

## Availability

Target:

99.99% availability.

Technical Requirement

- Fully managed infrastructure
- Multi-AZ storage
- No single point of failure

---

## Performance

Target

Single-digit millisecond latency.

Technical Requirement

- Query operations only
- Avoid scans
- Efficient indexing

---

## Cost Efficiency

Target

Lowest possible read/write cost.

Technical Requirement

- Minimal GSIs
- Projection optimization
- Sparse indexes where appropriate

---

## Security

Target

Secure API access.

Technical Requirement

- IAM authentication
- API authorization
- Encryption at rest

---

# Data Entities

The solution revolves around five primary entities.

---

## Event

Represents a football match.

Example Attributes

- Event ID
- Stadium
- Match Name
- Capacity
- Start Time

---

## User

Represents a customer entering the waiting room.

Example Attributes

- User ID
- Name
- Email
- Registration Time

---

## Queue Entry

Represents a user's position within an event queue.

Example Attributes

- Queue Position
- Status
- Join Time
- Admission Time

---

## Admission Token

Temporary credential issued when a user is admitted.

Example Attributes

- Token ID
- Expiration Time
- Status

---

## Session

Tracks an active waiting room session.

Example Attributes

- Session ID
- Last Activity
- Device Information
- Expiration

---

# Data Lifecycle

The expected lifecycle is illustrated below.

```
User
    │
    ▼
Join Queue
    │
    ▼
Waiting
    │
    ▼
Admitted
    │
    ▼
Token Issued
    │
    ▼
Ticket Purchase
    │
    ▼
Completed
```

Alternative paths:

```
Waiting
      │
      ▼
Timeout

or

Waiting
      │
      ▼
Cancelled
```

---

# DynamoDB Design Principles

The following DynamoDB best practices will guide the implementation.

## Single Table Design

Store all related entities in one table whenever practical.

---

## Access Pattern Driven

Schema design must satisfy application queries rather than relational normalization.

---

## Query over Scan

Every operation should be implemented using Query or GetItem.

Table scans should be avoided.

---

## Immutable Queue Position

Queue positions should not be updated after assignment.

Instead, status transitions indicate progress through the queue.

---

## Time To Live (TTL)

Expired sessions and tokens should be removed automatically.

---

## Conditional Writes

Prevent duplicate registrations.

Prevent race conditions during admission.

---

## Global Secondary Indexes (GSIs)

Indexes should only exist when required by a supported access pattern.

---

# Risks

| Risk | Mitigation |
|------|------------|
| Hot partitions | Distribute partition keys where appropriate |
| Duplicate registrations | Conditional writes |
| Token replay | Token expiration and validation |
| Queue starvation | Ordered admission logic |
| Expensive queries | Access-pattern-driven schema |

---

# Key Technical Decisions

| Decision | Reason |
|----------|--------|
| Single-table design | Reduced complexity and lower cost |
| TTL enabled | Automatic cleanup |
| Conditional writes | Data consistency |
| Query-first modeling | High performance |
| Event-based partitioning | Independent queues |
| GSIs only where required | Cost optimization |

---

# Outputs of this Analysis

This requirements analysis provides the foundation for:

- Access Pattern Analysis
- DynamoDB Single Table Design
- Primary Key Strategy
- Global Secondary Index Design
- API Design
- Infrastructure Implementation

These topics are covered in the subsequent documentation.