# REST API Design

Author: Muhammad Affan bin Aamir

Version: 1.0

---

# Purpose

This document defines the REST API for the Football Virtual Waiting Room.

The API provides endpoints for:

- Queue management
- Queue status
- Admission
- Token validation
- Administrative operations

The APIs are designed to be stateless, idempotent where applicable, and suitable for deployment behind Amazon API Gateway.

---

# Base URL

```
https://api.example.com/v1
```

---

# Authentication

The API is designed to work with authenticated users.

Possible authentication mechanisms:

- JWT
- Amazon Cognito
- IAM Authorization
- Lambda Authorizer

For this challenge, authentication is assumed to occur before requests reach the application.

---

# Content Type

```
application/json
```

---

# API Summary

| Method | Endpoint | Purpose |
|----------|----------|----------|
| POST | /queue/join | Join waiting room |
| GET | /queue/status | Retrieve queue status |
| POST | /queue/leave | Leave queue |
| POST | /queue/admit | Admit next users (Admin) |
| POST | /token/validate | Validate admission token |
| GET | /event/{eventId} | Event information |
| GET | /event/{eventId}/stats | Queue statistics |

---

# POST /queue/join

## Description

Registers a user in the waiting room.

---

## Request

```json
{
  "eventId": "1001",
  "userId": "501"
}
```

---

## Success Response

HTTP 201

```json
{
  "message": "Successfully joined queue.",
  "queuePosition": 123,
  "status": "WAITING",
  "estimatedWaitMinutes": 18
}
```

---

## Error Responses

| HTTP | Meaning |
|------|----------|
| 400 | Invalid request |
| 401 | Unauthorized |
| 404 | Event not found |
| 409 | Already registered |
| 500 | Internal error |

---

## DynamoDB Operations

- Conditional PutItem
- Update queue statistics

---

## Idempotency

Duplicate requests should return the existing queue record rather than creating another one.

---

# GET /queue/status

## Description

Returns the current status of the authenticated user's queue entry.

---

## Query Parameters

```
eventId=1001
```

---

## Success Response

```json
{
  "eventId": "1001",
  "queuePosition": 123,
  "status": "WAITING",
  "estimatedWaitMinutes": 18
}
```

---

## DynamoDB Operation

Query (GSI1)

---

# POST /queue/leave

## Description

Allows a user to voluntarily leave the queue.

---

## Request

```json
{
  "eventId": "1001",
  "userId": "501"
}
```

---

## Success Response

```json
{
  "message": "You have left the queue."
}
```

---

## DynamoDB Operation

UpdateItem

Status becomes

```
CANCELLED
```

---

# POST /queue/admit

## Description

Administrative endpoint that admits the next batch of waiting users.

---

## Request

```json
{
  "eventId": "1001",
  "batchSize": 50
}
```

---

## Success Response

```json
{
  "admittedUsers": 50,
  "remainingQueue": 18235
}
```

---

## DynamoDB Operations

- Query queue
- Update queue entries
- Generate admission tokens

---

## Authorization

Administrator only.

---

# POST /token/validate

## Description

Validates an admission token before allowing access to ticket purchasing.

---

## Request

```json
{
  "token": "ABC123XYZ"
}
```

---

## Success Response

```json
{
  "valid": true,
  "eventId": "1001",
  "userId": "501",
  "expiresAt": "2026-07-08T13:45:00Z"
}
```

---

## Invalid Response

HTTP 401

```json
{
  "valid": false,
  "reason": "Token expired."
}
```

---

## DynamoDB Operation

GetItem or GSI2 lookup

---

# GET /event/{eventId}

## Description

Returns metadata for a football event.

---

## Success Response

```json
{
  "eventId": "1001",
  "matchName": "Manchester United vs Liverpool",
  "stadium": "Old Trafford",
  "capacity": 50000,
  "status": "OPEN"
}
```

---

## DynamoDB Operation

GetItem

---

# GET /event/{eventId}/stats

## Description

Returns aggregate queue statistics.

---

## Success Response

```json
{
  "waitingUsers": 385421,
  "admittedUsers": 16450,
  "expiredUsers": 237,
  "averageWaitMinutes": 24
}
```

---

## DynamoDB Operation

GetItem (STATS item)

---

# Standard Error Response

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Requested resource does not exist."
  }
}
```

---

# HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

---

# Validation Rules

## Join Queue

- Event ID must exist.
- User must be authenticated.
- User must not already be in the queue.
- Event must be open.

---

## Validate Token

- Token must exist.
- Token must not be expired.
- Token must belong to the requesting user.

---

## Leave Queue

- Queue entry must exist.
- Queue must still be active.
- User must own the queue entry.

---

# Rate Limiting

Recommended API Gateway throttling:

| Endpoint | Limit |
|----------|-------|
| Queue Status | 5 requests/second/user |
| Join Queue | 2 requests/minute/user |
| Token Validation | 10 requests/minute/user |
| Event Lookup | 20 requests/minute/user |

Rate limiting helps protect the platform during peak traffic.

---

# Idempotency Strategy

To prevent duplicate registrations:

- Use conditional writes in DynamoDB.
- Support an optional `Idempotency-Key` request header.
- If a request with the same idempotency key is retried, return the original response.

This is especially important for unreliable mobile networks and browser retries.

---

# Sequence Example

```
User
 │
 │ POST /queue/join
 ▼
API Gateway
 │
 ▼
Join Queue Lambda
 │
 ▼
Conditional PutItem
 │
 ▼
Queue Created
 │
 ▼
HTTP 201
```

---

# Security Considerations

- HTTPS only
- Input validation
- Authorization before business logic
- No sensitive information in responses
- Token expiration enforcement
- Least-privilege IAM roles

---

# Observability

Each request should include:

- Request ID
- Correlation ID
- Timestamp
- User ID (where appropriate)

These identifiers simplify debugging and distributed tracing.

---

# Summary

The REST API is designed to be:

- Stateless
- Secure
- Idempotent
- Scalable
- Easy to consume
- Efficiently mapped to DynamoDB access patterns

Each endpoint corresponds directly to one or more optimized DynamoDB operations, ensuring low latency and predictable performance under heavy load.