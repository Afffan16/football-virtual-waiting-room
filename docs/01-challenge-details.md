# AWS Builder Challenge
# DynamoDB Football Data Modeling Challenge

Author: Muhammad Affan bin Aamir

Version: 1.0

---

# Overview

This project is an implementation of the AWS Builder Center DynamoDB Football Data Modeling Challenge.

The objective is to design and implement a highly scalable data model capable of supporting a virtual waiting room for extremely popular football matches. The system must efficiently manage millions of concurrent users while maintaining fairness, consistency, and low latency.

Rather than focusing solely on application development, this challenge emphasizes one of the most critical aspects of building scalable cloud-native systems:

> Designing an efficient DynamoDB data model based on real-world access patterns.

---

# Challenge Context

When tickets for a high-demand football match become available, millions of supporters attempt to access the platform simultaneously.

Without proper traffic management, this surge can overwhelm backend services, leading to:

- Website crashes
- Long response times
- Lost ticket sales
- Poor customer experience
- Infrastructure overload

To solve this problem, a Virtual Waiting Room is introduced.

Instead of allowing every request to directly reach the ticketing service, users first enter a waiting queue where they are admitted gradually based on queue order and system capacity.

---

# Primary Goal

Build a DynamoDB-based backend capable of:

- Registering users into a queue
- Tracking queue position
- Admitting users fairly
- Issuing admission tokens
- Automatically expiring inactive users
- Scaling to millions of concurrent requests

---

# Business Objectives

The system should:

- Ensure fairness
- Prevent ticket overselling
- Protect backend services
- Handle sudden traffic spikes
- Minimize operational costs
- Maintain high availability

---

# Functional Requirements

The system shall support the following operations.

## Queue Registration

Users should be able to join the waiting room.

Each registration must create a queue record.

---

## Queue Status

Users should retrieve:

- Queue position
- Estimated waiting time
- Current status

without expensive scans.

---

## User Admission

The platform should periodically admit users from the front of the queue.

Admission should preserve ordering.

---

## Token Generation

Successfully admitted users receive a temporary admission token.

The token grants access to the ticket purchasing system.

---

## Token Validation

Before entering checkout, tokens must be validated.

Expired tokens must be rejected.

---

## Queue Expiration

Inactive users should automatically leave the queue after a configurable timeout.

---

## Cleanup

Expired sessions should be removed automatically using DynamoDB TTL.

---

# Non-Functional Requirements

The solution should provide:

## Scalability

Support millions of users.

---

## Low Latency

Typical requests should complete in milliseconds.

---

## High Availability

No single point of failure.

---

## Cost Efficiency

Minimize unnecessary reads and writes.

Avoid table scans.

---

## Durability

Queue information must not be lost.

---

## Security

Support IAM authentication.

Protect APIs using authorization.

---

# DynamoDB Requirements

The data model should follow DynamoDB best practices.

Specifically:

- Single Table Design
- Query-first modeling
- No table scans
- Efficient partition keys
- Efficient sort keys
- Global Secondary Indexes
- Time To Live (TTL)
- Conditional Writes
- Atomic Counters where appropriate

---

# Assumptions

The following assumptions are made.

- Users join using authenticated accounts.
- Each user joins a queue only once per event.
- Queue positions are immutable once assigned.
- Events may have millions of participants.
- Multiple football events may exist simultaneously.
- Tokens expire after a configurable duration.
- Event capacity is configurable.

---

# Constraints

The solution should avoid:

- Full table scans
- Large hot partitions
- Expensive joins
- Cross-table transactions whenever possible
- Manual cleanup jobs

---

# Success Criteria

The challenge is considered successful if the solution can:

- Register users efficiently
- Retrieve queue status quickly
- Admit users fairly
- Scale horizontally
- Keep operational costs low
- Demonstrate effective DynamoDB modeling

---

# Deliverables

The completed solution should include:

- DynamoDB Single Table Design
- Access Pattern Analysis
- Key Schema Design
- GSI Design
- API Design
- Architecture Diagram
- Infrastructure Documentation
- Implementation Guide
- Testing Strategy
- Optimization Recommendations

---

# Technologies

AWS Services

- Amazon DynamoDB
- AWS Lambda
- Amazon API Gateway
- Amazon CloudWatch
- AWS IAM
- Amazon EventBridge
- DynamoDB Streams (optional)

Development

- Python
- Boto3
- AWS SAM or CloudFormation
- Git
- Markdown Documentation

---

# Expected Outcome

By completing this challenge, the resulting solution will demonstrate:

- Advanced DynamoDB data modeling
- Event-driven architecture
- Serverless application design
- Cloud-native scalability
- Production-ready engineering practices

The implementation should closely resemble a real-world ticketing system capable of supporting high-profile sporting events while remaining efficient, reliable, and cost-effective.