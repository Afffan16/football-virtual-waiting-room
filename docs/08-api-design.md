# 🔌 REST API Design

**Author:** Muhammad Affan bin Aamir · **Version:** 1.0 · **Document:** `docs/08-api-design.md`

← [Back: System Architecture](07-system-architecture.md) · Next: [Build Guide →](09-build-guide.md)

---

## Table of Contents

- [Purpose](#purpose)
- [Base URL & Authentication](#base-url--authentication)
- [API Summary](#api-summary)
- [Endpoints](#endpoints)
- [Standard Error Response](#standard-error-response)
- [HTTP Status Codes](#http-status-codes)
- [Validation Rules](#validation-rules)
- [Rate Limiting](#rate-limiting)
- [Idempotency Strategy](#idempotency-strategy)
- [Security Considerations](#security-considerations)
- [Observability](#observability)

---

## Purpose

This document defines the REST API for the Football Virtual Waiting Room — covering queue management, queue status, admission, token validation, and administrative operations. Every endpoint is stateless, idempotent where applicable, and designed for deployment behind Amazon API Gateway.

Each endpoint maps directly to one or more optimized DynamoDB operations from [`03-access-patterns.md`](03-access-patterns.md) and [`06-index-design.md`](06-index-design.md).

---

## Base URL & Authentication

```
https://api.example.com/v1
```

| | |
|---|---|
| **Content-Type** | `application/json` |
| **Authentication** | Assumed to occur before requests reach the application. Possible mechanisms: JWT, Amazon Cognito, IAM Authorization, or a Lambda Authorizer. |

---

## API Summary

| Method | Endpoint | Purpose | DynamoDB Op |
|---|---|---|---|
| `POST` | `/queue/join` | Join waiting room | Conditional `PutItem` |
| `GET` | `/queue/status` | Retrieve queue status | `Query` (GSI1) |
| `POST` | `/queue/leave` | Leave queue | `UpdateItem` |
| `POST` | `/queue/admit` | Admit next users *(Admin)* | `Query` + `UpdateItem` |
| `POST` | `/token/validate` | Validate admission token | `GetItem` / GSI2 |
| `GET` | `/event/{eventId}` | Event information | `GetItem` |
| `GET` | `/event/{eventId}/stats` | Queue statistics | `GetItem` (STATS item) |

---

## Endpoints

### `POST /queue/join`

Registers a user in the waiting room.

<details>
<summary><b>Request / Response / Errors</b></summary>

**Request**
```json
{ "eventId": "1001", "userId": "501" }
```

**Success — `201 Created`**
```json
{
  "message": "Successfully joined queue.",
  "queuePosition": 123,
  "status": "WAITING",
  "estimatedWaitMinutes": 18
}
```

**Errors**

| HTTP | Meaning |
|---|---|
| 400 | Invalid request |
| 401 | Unauthorized |
| 404 | Event not found |
| 409 | Already registered |
| 500 | Internal error |

**Idempotency:** duplicate requests return the existing queue record rather than creating another one.

</details>

---

### `GET /queue/status`

Returns the current status of the authenticated user's queue entry.

<details>
<summary><b>Request / Response</b></summary>

**Query Parameters:** `eventId=1001`

**Success — `200 OK`**
```json
{
  "eventId": "1001",
  "queuePosition": 123,
  "status": "WAITING",
  "estimatedWaitMinutes": 18
}
```

**DynamoDB Operation:** `Query` (GSI1)

</details>

---

### `POST /queue/leave`

Allows a user to voluntarily leave the queue.

<details>
<summary><b>Request / Response</b></summary>

**Request**
```json
{ "eventId": "1001", "userId": "501" }
```

**Success — `200 OK`**
```json
{ "message": "You have left the queue." }
```

**DynamoDB Operation:** `UpdateItem` → status becomes `CANCELLED`

</details>

---

### `POST /queue/admit` — *Admin only*

Admits the next batch of waiting users.

> 🔐 **Authorization required.** This endpoint requires the `x-admin-api-key` header. Requests without a valid key return `403 Forbidden`.

<details>
<summary><b>Request / Response</b></summary>

**Request**
```http
POST /queue/admit
Content-Type: application/json
x-admin-api-key: <your-admin-api-key>
```
```json
{ "eventId": "1001", "batchSize": 50 }
```

**Success — `200 OK`**
```json
{
  "admittedUsers": 50,
  "remainingQueue": 18235,
  "admittedUserIds": ["FAN-001", "FAN-002", "..."]
}
```

**Unauthorized — `403 Forbidden`**
```json
{ "error": { "code": "FORBIDDEN", "message": "Admin authorization required." } }
```

**DynamoDB Operations:** Query GSI3 (WAITING status) → batch UpdateItem → PutItem (admission tokens)

**Authorization:** Pass `x-admin-api-key: <key>` header. The key is set via the `AdminApiKey` SAM parameter at deploy time. Maximum `batchSize` is capped at 500.

</details>

---

### `POST /token/validate`

Validates an admission token before allowing access to ticket purchasing.

<details>
<summary><b>Request / Response</b></summary>

**Request**
```json
{ "token": "ABC123XYZ" }
```

**Success — `200 OK`**
```json
{
  "valid": true,
  "eventId": "1001",
  "userId": "501",
  "expiresAt": "2026-07-08T13:45:00Z"
}
```

**Invalid — `401 Unauthorized`**
```json
{ "valid": false, "reason": "Token expired." }
```

**DynamoDB Operation:** `GetItem` or GSI2 lookup

</details>

---

### `GET /event/{eventId}`

Returns metadata for a football event.

<details>
<summary><b>Response</b></summary>

```json
{
  "eventId": "1001",
  "matchName": "Manchester United vs Liverpool",
  "stadium": "Old Trafford",
  "capacity": 50000,
  "status": "OPEN"
}
```

**DynamoDB Operation:** `GetItem`

</details>

---

### `GET /event/{eventId}/stats`

Returns aggregate queue statistics.

<details>
<summary><b>Response</b></summary>

```json
{
  "waitingUsers": 385421,
  "admittedUsers": 16450,
  "expiredUsers": 237,
  "averageWaitMinutes": 24
}
```

**DynamoDB Operation:** `GetItem` (STATS item)

</details>

---

## Standard Error Response

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Requested resource does not exist."
  }
}
```

---

## HTTP Status Codes

| Code | Meaning |
|---|---|
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

## Validation Rules

| Endpoint | Rules |
|---|---|
| **Join Queue** | Event ID must exist · user must be authenticated · user must not already be in the queue · event must be open |
| **Validate Token** | Token must exist · token must not be expired · token must belong to the requesting user |
| **Leave Queue** | Queue entry must exist · queue must still be active · user must own the queue entry |

---

## Rate Limiting

Recommended API Gateway throttling:

| Endpoint | Limit |
|---|---|
| Queue Status | 5 requests/second/user |
| Join Queue | 2 requests/minute/user |
| Token Validation | 10 requests/minute/user |
| Event Lookup | 20 requests/minute/user |

Rate limiting protects the platform during peak, ticket-drop-level traffic.

---

## Idempotency Strategy

To prevent duplicate registrations:

- Use conditional writes in DynamoDB (`attribute_not_exists(PK)`)
- Support an optional `Idempotency-Key` request header
- Retried requests with the same idempotency key return the original response

Especially important for unreliable mobile networks and browser retries — see `POST /queue/join` above.

---

## Security Considerations

- HTTPS only
- Input validation on every request (field presence + length limits)
- Admin endpoints protected by `x-admin-api-key` header (checked server-side with constant-time comparison to prevent timing attacks)
- `ADMIN_API_KEY` injected via Lambda environment variable — set via SAM `AdminApiKey` parameter, never hardcoded in source
- No sensitive information in error responses
- Token expiration strictly enforced
- Least-privilege IAM roles per Lambda
- API Gateway stage-level throttling (200 req/s rate limit, 500 burst)
- For production: move `ADMIN_API_KEY` to AWS Secrets Manager; add Cognito/Lambda Authorizer for user identity; restrict `AllowOrigin` to your domain

---

## Observability

Every request logs:

- Request ID
- Correlation ID
- Timestamp
- User ID (where applicable)

These identifiers simplify debugging and distributed tracing across API Gateway → Lambda → DynamoDB.

---

## Summary

The REST API is stateless, secure, idempotent, scalable, and easy to consume. Each endpoint maps cleanly to the DynamoDB access patterns and indexes established earlier in the design — ensuring low latency and predictable performance under heavy load.

A ready-to-use request collection is available in [`../postman/`](../postman/). Next: [`09-build-guide.md`](09-build-guide.md) covers how this API and its backing infrastructure were actually built.