# 🏆 AWS Builder Challenge — DynamoDB Football Data Modeling Challenge

**Author:** Muhammad Affan bin Aamir · **Version:** 1.0 · **Document:** `docs/01-challenge-details.md`

← [Back to Project Status](00-project-status.md) · Next: [Requirements Analysis →](02-requirements-analysis.md)

---

## Table of Contents

- [Overview](#overview)
- [Challenge Context](#challenge-context)
- [Primary Goal](#primary-goal)
- [Business Objectives](#business-objectives)
- [Functional Requirements](#functional-requirements)
- [Non-Functional Requirements](#non-functional-requirements)
- [DynamoDB Requirements](#dynamodb-requirements)
- [Assumptions](#assumptions)
- [Constraints](#constraints)
- [Success Criteria](#success-criteria)
- [Deliverables](#deliverables)
- [Technologies](#technologies)
- [Expected Outcome](#expected-outcome)

---

## Overview

This project is an implementation of the **AWS Builder Center DynamoDB Football Data Modeling Challenge**.

The objective is to design and implement a highly scalable data model capable of supporting a virtual waiting room for extremely popular football matches. The system must efficiently manage millions of concurrent users while maintaining fairness, consistency, and low latency.

Rather than focusing solely on application development, this challenge emphasizes one of the most critical aspects of building scalable cloud-native systems:

> **Designing an efficient DynamoDB data model based on real-world access patterns.**

---

## Challenge Context

When tickets for a high-demand football match become available, millions of supporters attempt to access the platform simultaneously.

Without proper traffic management, that surge can overwhelm backend services, leading to:

| Failure Mode | Impact |
|---|---|
| 🔴 Website crashes | Platform unavailable during peak demand |
| 🐢 Long response times | Users abandon the purchase flow |
| 💸 Lost ticket sales | Direct revenue impact |
| 😤 Poor customer experience | Reputational damage |
| 🔥 Infrastructure overload | Cascading failures across services |

**The fix:** a Virtual Waiting Room. Instead of every request hitting the ticketing service directly, users first enter a waiting queue where they're admitted gradually, based on queue order and system capacity.

---

## Primary Goal

Build a DynamoDB-based backend capable of:

- [x] Registering users into a queue
- [x] Tracking queue position
- [x] Admitting users fairly
- [x] Issuing admission tokens
- [x] Automatically expiring inactive users
- [x] Scaling to millions of concurrent requests

---

## Business Objectives

The system should:

- Ensure **fairness** — first in, first served
- Prevent **ticket overselling**
- Protect **backend services** from overload
- Handle **sudden traffic spikes** gracefully
- Minimize **operational costs**
- Maintain **high availability**

---

## Functional Requirements

| Requirement | Description |
|---|---|
| **Queue Registration** | Users join the waiting room; each registration creates a queue record |
| **Queue Status** | Users retrieve queue position, estimated wait time, and current status — without expensive scans |
| **User Admission** | The platform periodically admits users from the front of the queue, preserving order |
| **Token Generation** | Successfully admitted users receive a temporary admission token granting access to the ticket purchasing system |
| **Token Validation** | Tokens must be validated before checkout; expired tokens are rejected |
| **Queue Expiration** | Inactive users automatically leave the queue after a configurable timeout |
| **Cleanup** | Expired sessions are removed automatically using DynamoDB TTL — no scheduled jobs |

> See how each of these maps to a Lambda function in [`00-project-status.md`](00-project-status.md#lambda-responsibilities) and to an endpoint in [`08-api-design.md`](08-api-design.md).

---

## Non-Functional Requirements

| Requirement | Target |
|---|---|
| **Scalability** | Support millions of users |
| **Low Latency** | Typical requests complete in milliseconds |
| **High Availability** | No single point of failure |
| **Cost Efficiency** | Minimize unnecessary reads/writes; avoid table scans |
| **Durability** | Queue information must not be lost |
| **Security** | Support IAM authentication; protect APIs using authorization |

---

## DynamoDB Requirements

The data model must follow DynamoDB best practices:

- Single Table Design
- Query-first modeling
- No table scans
- Efficient partition keys
- Efficient sort keys
- Global Secondary Indexes
- Time To Live (TTL)
- Conditional writes
- Atomic counters where appropriate

*(Full design in [`04-data-model.md`](04-data-model.md), [`05-table-schema.md`](05-table-schema.md), and [`06-index-design.md`](06-index-design.md).)*

---

## Assumptions

- Users join using authenticated accounts.
- Each user joins a queue only once per event.
- Queue positions are immutable once assigned.
- Events may have millions of participants.
- Multiple football events may exist simultaneously.
- Tokens expire after a configurable duration.
- Event capacity is configurable.

---

## Constraints

The solution should avoid:

- ❌ Full table scans
- ❌ Large hot partitions
- ❌ Expensive joins
- ❌ Cross-table transactions, wherever possible
- ❌ Manual cleanup jobs

---

## Success Criteria

The challenge is considered successful if the solution can:

- [x] Register users efficiently
- [x] Retrieve queue status quickly
- [x] Admit users fairly
- [x] Scale horizontally
- [x] Keep operational costs low
- [x] Demonstrate effective DynamoDB modeling

---

## Deliverables

| Deliverable | Where it lives |
|---|---|
| DynamoDB Single Table Design | [`05-table-schema.md`](05-table-schema.md) |
| Access Pattern Analysis | [`03-access-patterns.md`](03-access-patterns.md) |
| NoSQL Workbench Export | [`../nosql-workbench/football-waiting-room-data-model.json`](../nosql-workbench/football-waiting-room-data-model.json) |
| Key Schema Design | [`05-table-schema.md`](05-table-schema.md) |
| GSI Design | [`06-index-design.md`](06-index-design.md) |
| API Design | [`08-api-design.md`](08-api-design.md) |
| Architecture Diagram | [`07-system-architecture.md`](07-system-architecture.md), [`../diagrams/architecture-diagrams.md`](../diagrams/architecture-diagrams.md) |
| Infrastructure Documentation | `template.yaml` |
| Implementation Guide | [`09-build-guide.md`](09-build-guide.md) |
| Testing Strategy | [`12-testing-guide.md`](12-testing-guide.md) |
| Optimization Recommendations | [`11-optimization.md`](11-optimization.md) |

---

## Technologies

**AWS Services**

- Amazon DynamoDB
- AWS Lambda
- Amazon API Gateway
- Amazon CloudWatch
- AWS IAM
- Amazon EventBridge
- DynamoDB Streams *(optional)*

**Development**

- Python
- Boto3
- AWS SAM / CloudFormation
- Git
- Markdown documentation

---

## Expected Outcome

By completing this challenge, the resulting solution demonstrates:

- Advanced DynamoDB data modeling
- Event-driven architecture
- Serverless application design
- Cloud-native scalability
- Production-ready engineering practices

The implementation should closely resemble a real-world ticketing system capable of supporting high-profile sporting events, while remaining efficient, reliable, and cost-effective.

---

Next: [`02-requirements-analysis.md`](02-requirements-analysis.md) translates this brief into concrete functional and non-functional requirements.
