# Testing Strategy and Validation Plan

Author: Muhammad Affan bin Aamir

Version: 1.0

---

# Purpose

This document defines the testing strategy for the Football Virtual Waiting Room.

The objective is to verify that every component behaves correctly, satisfies the defined access patterns, and scales under high traffic while maintaining data consistency.

The testing approach includes:

- Unit Testing
- Integration Testing
- API Testing
- DynamoDB Validation
- Load Testing
- Failure Testing
- Security Testing

---

# Testing Objectives

The system should demonstrate:

- Functional correctness
- Data consistency
- High availability
- Scalability
- Fault tolerance
- Low latency
- Correct DynamoDB behavior

---

# Testing Pyramid

```
                Load Tests
                     ▲

            End-to-End Tests
                     ▲

          Integration Tests
                     ▲

              Unit Tests
```

---

# Test Environment

AWS Services

- API Gateway
- Lambda
- DynamoDB
- CloudWatch

Testing Tools

- pytest
- Postman
- AWS SAM CLI
- k6
- Artillery
- Locust

---

# Unit Testing

## Objective

Verify individual Lambda functions.

---

## Join Queue Lambda

Test Cases

| ID | Description | Expected Result |
|----|-------------|----------------|
| UT-01 | Valid registration | Queue item created |
| UT-02 | Missing Event ID | HTTP 400 |
| UT-03 | Missing User ID | HTTP 400 |
| UT-04 | Duplicate registration | HTTP 409 |
| UT-05 | Closed event | HTTP 403 |

---

## Queue Status Lambda

| ID | Description | Expected Result |
|----|-------------|----------------|
| UT-06 | Existing queue | Queue returned |
| UT-07 | Unknown queue | HTTP 404 |
| UT-08 | Invalid request | HTTP 400 |

---

## Leave Queue Lambda

| ID | Description | Expected Result |
|----|-------------|----------------|
| UT-09 | Valid leave | Status updated |
| UT-10 | Already completed | HTTP 409 |
| UT-11 | Queue not found | HTTP 404 |

---

## Token Validation Lambda

| ID | Description | Expected Result |
|----|-------------|----------------|
| UT-12 | Valid token | Authorized |
| UT-13 | Expired token | Unauthorized |
| UT-14 | Unknown token | Unauthorized |
| UT-15 | Used token | Unauthorized |

---

# Integration Testing

## Objective

Verify interactions between AWS services.

---

## Test Flow

```
API Gateway

↓

Lambda

↓

DynamoDB

↓

CloudWatch
```

---

## Integration Scenarios

| ID | Scenario |
|----|----------|
| IT-01 | Join queue end-to-end |
| IT-02 | Retrieve queue status |
| IT-03 | Leave queue |
| IT-04 | Validate token |
| IT-05 | Update statistics |

---

# API Testing

Verify every endpoint.

| Endpoint | Tests |
|-----------|------|
| POST /queue/join | Success, duplicate, invalid |
| GET /queue/status | Existing, missing |
| POST /queue/leave | Success, invalid |
| POST /token/validate | Valid, expired |
| GET /event/{id} | Existing, missing |
| GET /event/{id}/stats | Existing |

---

# DynamoDB Validation

## Verify

- No table scans
- Query operations only
- TTL functionality
- Conditional writes
- GSI lookups
- Correct item structure

---

## Validation Queries

Confirm:

✓ Queue lookup

✓ Event lookup

✓ Token lookup

✓ Statistics lookup

---

# TTL Testing

Create a session with a short expiration.

Verify:

- Record exists initially.
- Record is automatically removed after TTL processing.
- Expired session is no longer returned by application logic.

Note: DynamoDB TTL deletion is asynchronous and may take time after the expiration timestamp.

---

# Streams Testing

Enable DynamoDB Streams.

Verify:

- INSERT events
- MODIFY events
- REMOVE events (when applicable)

Confirm stream records contain expected attributes.

---

# Load Testing

Objective

Simulate heavy traffic.

Scenarios

- 1,000 concurrent users
- 10,000 concurrent users
- Burst traffic
- Continuous polling
- Admission batches

Metrics

- Average latency
- P95 latency
- Throughput
- Error rate
- Throttled requests

---

# Stress Testing

Increase traffic until the system reaches operational limits.

Observe:

- API Gateway
- Lambda concurrency
- DynamoDB behavior
- Error responses

Expected outcome:

Graceful degradation without data corruption.

---

# Failure Testing

## Duplicate Requests

Expected

Single queue record.

---

## Invalid Token

Expected

HTTP 401

---

## Closed Event

Expected

Registration denied.

---

## Missing Event

Expected

HTTP 404

---

## Queue Overflow

Expected

Graceful rejection or waiting room closure.

---

# Security Testing

Verify

- HTTPS enforcement
- Authentication
- Authorization
- Input validation
- Token ownership
- Least-privilege IAM policies

---

# Performance Targets

| Metric | Target |
|--------|--------|
| API Response Time | < 200 ms (typical) |
| Lambda Duration | < 500 ms |
| Queue Registration | < 200 ms |
| Queue Lookup | < 100 ms |
| Token Validation | < 100 ms |
| Error Rate | < 1% |

These targets should be validated under representative load and adjusted if production requirements differ.

---

# Observability

Confirm logs include:

- Request ID
- User ID (where appropriate)
- Event ID
- Lambda execution time
- Error details (without exposing sensitive information)

---

# Acceptance Criteria

The project is accepted when:

- All unit tests pass.
- Integration tests pass.
- API tests pass.
- No table scans are required.
- TTL functions correctly.
- GSIs satisfy all access patterns.
- Error handling is consistent.
- Performance targets are met or documented.
- Documentation matches implementation.

---

# Regression Testing

Run the full test suite after:

- Schema changes
- New Lambda functions
- API modifications
- Infrastructure updates

Automate regression testing in CI/CD where possible.

---

# Test Deliverables

The repository should include:

```
tests/

├── unit/
├── integration/
├── api/
├── load/
└── fixtures/
```

Additional artifacts:

- Test reports
- Load test scripts
- Postman collection
- Sample requests
- Sample responses

---

# Summary

This testing strategy verifies correctness, scalability, and reliability across all layers of the Football Virtual Waiting Room.

By combining unit, integration, API, load, and failure testing, the solution demonstrates production-oriented engineering practices while validating the DynamoDB data model under realistic conditions.