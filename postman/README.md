# 📮 Postman Collection

**Document:** `postman/README.md`

This folder contains the Postman collection and environment used to exercise the Football Virtual Waiting Room REST API — the same endpoints documented in [`../docs/08-api-design.md`](../docs/08-api-design.md).

---

## Table of Contents

- [Covered APIs](#covered-apis)
- [Environment Variables](#environment-variables)
- [Import](#import)
- [Suggested Run Order](#suggested-run-order)

---

## Covered APIs

| Request | Endpoint |
|---|---|
| Join Queue | `POST /queue/join` |
| Queue Status | `GET /queue/status` |
| Leave Queue | `POST /queue/leave` |
| Admit Users | `POST /queue/admit` |
| Admin Queue List | `GET /queue/admin/list` |
| Validate Token | `POST /token/validate` |
| Events List | `GET /events` |
| Create Event | `POST /event` |
| Event Lookup | `GET /event/{eventId}` |
| Queue Statistics | `GET /event/{eventId}/stats` |

Full request/response contracts for each of these live in [`08-api-design.md`](../docs/08-api-design.md).

---

## Environment Variables

| Variable | Description |
|---|---|
| `baseUrl` | API Gateway base URL for the deployed stack |
| `eventId` | Sample event ID to test against |
| `userId` | Sample user ID to test against |
| `token` | Admission token, captured from a successful admission for use in token validation |
| `adminEmail` | Demo admin email, default `admin123@gmail.com` |
| `adminPassword` | Demo admin password, default `admin123` |
| `adminApiKey` | Optional admin API key if using the API-key path |

---

## Import

1. Open Postman.
2. Import the collection file from this folder.
3. Import the environment file from this folder.
4. Select the imported environment in the top-right environment picker before sending any requests.

---

## Suggested Run Order

Requests are easiest to follow in the same order a real user would move through the waiting room:

1. **Join Queue** — registers the sample user and returns a queue position
2. **Queue Status** — confirms the registration and current position
3. **Queue Admin List** *(admin)* — confirms the user appears in the real queue table
4. **Admit User** *(admin)* — moves the user from `WAITING` to `ADMITTED` and issues a token
5. **Validate Token** — confirms the issued token is active before checkout

Running them out of order works too — for example, calling **Validate Token** before **Admit User** should correctly return an unauthorized response, which is a useful check in itself.
