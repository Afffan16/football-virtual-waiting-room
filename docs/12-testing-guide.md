# 🧪 Testing Guide

**Author:** Muhammad Affan bin Aamir · **Version:** 2.0 · **Document:** `docs/12-testing-guide.md`

← [Back: Optimization](11-optimization.md) · Next: [Deployment Guide →](13-deployment-guide.md)

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Test Structure](#test-structure)
- [Running Unit Tests](#running-unit-tests)
- [Running Integration Tests](#running-integration-tests)
- [Running API Contract Tests](#running-api-contract-tests)
- [Load Testing with mass_ticket_requests.py](#load-testing-with-mass_ticket_requestspy)
- [Manual Testing with cURL](#manual-testing-with-curl)
- [Testing the Frontend Locally](#testing-the-frontend-locally)
- [SAM Local Testing](#sam-local-testing)
- [Security Testing Checklist](#security-testing-checklist)
- [Test Coverage Targets](#test-coverage-targets)
- [CI Pipeline](#ci-pipeline)

---

## Overview

This guide covers every layer of testing for the Football Virtual Waiting Room:

| Layer | Tool | Scope |
|---|---|---|
| **Unit** | `pytest` + `moto` | Lambda handler logic, models, utilities |
| **Integration** | `pytest` + `moto` | Full request flows through Lambda → DynamoDB |
| **API Contract** | `pytest` + `requests` | HTTP request/response schema validation |
| **Load** | `mass_ticket_requests.py` / k6 | Concurrent-user and burst-traffic simulation |
| **Manual** | cURL / Postman | Ad-hoc endpoint verification |
| **Frontend** | Browser dev tools | SPA routing, API calls, UI behaviour |

---

## Prerequisites

```bash
# Python 3.12+
python --version

# Install dev dependencies
pip install -r requirements-dev.txt

# AWS SAM CLI (for SAM Local)
sam --version

# Optional: aiohttp for load testing
pip install aiohttp
```

---

## Test Structure

```
tests/
├── unit/               # Isolated Lambda handler + utility tests
├── integration/        # End-to-end Lambda ↔ DynamoDB flows (moto)
├── api/                # REST contract tests (request/response shape)
└── load/               # k6 / Locust load test scripts
```

---

## Running Unit Tests

```bash
# Run the full suite
pytest

# Run only unit tests
pytest tests/unit/

# With coverage report
pytest --cov=src --cov-report=term-missing

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

Key things unit tests cover:

- Each Lambda handler returns correct HTTP status codes
- `parse_body` handles missing/malformed JSON
- `validate_required_fields` catches missing fields
- `generate_queue_position` produces lexicographically sortable strings
- `estimate_wait_minutes` returns non-negative integers
- Response builders (`success`, `bad_request`, etc.) include CORS headers
- Model `from_item` / `to_item` round-trips are lossless
- Admin authorization check in `admit_users` correctly accepts/rejects keys

---

## Running Integration Tests

Integration tests use `moto` to mock DynamoDB locally — no AWS credentials required.

```bash
pytest tests/integration/ -v
```

Key flows covered:

1. **Join → Status → Leave** — full user lifecycle
2. **Join → Admit → Validate Token** — happy-path admission
3. **Duplicate join** — returns existing entry, not 409
4. **Admit with no waiting users** — returns `admittedUsers: 0` gracefully
5. **Leave when not WAITING** — returns 409 Conflict
6. **Stats increment** — counters update correctly after admits/leaves
7. **Unauthorized admit** — returns 403 when admin key is wrong

---

## Running API Contract Tests

API contract tests run against the **deployed** API. Set your endpoint URL first:

```bash
export API_URL="https://n20mxucrj4.execute-api.us-east-1.amazonaws.com/Prod"
export ADMIN_API_KEY="your-admin-key-here"

pytest tests/api/ -v
```

These tests assert:

- Response shape matches the documented schema
- Error responses include `error.code` and `error.message`
- 200/201 responses include all required fields
- CORS headers are present on every response

---

## Load Testing with mass_ticket_requests.py

The script at `scripts/mass_ticket_requests.py` fires high-volume join requests against the deployed API.

```bash
# Install aiohttp first
pip install aiohttp

# Run a small test (1,000 requests)
python scripts/mass_ticket_requests.py --total 1000 --concurrency 20 --event 1001

# Run a medium test (100K requests)
python scripts/mass_ticket_requests.py --total 100000 --concurrency 100 --event 1002

# Full 1M load test (use with caution — this hits production)
python scripts/mass_ticket_requests.py --total 1000000 --concurrency 150 --event 1001
```

**Output includes:**
- Real-time progress every 10,000 requests
- Final throughput (req/s)
- p50 / p90 / p95 / p99 latency percentiles
- Error breakdown by type

**Performance targets under load:**

| Metric | Target |
|---|---|
| p99 API latency | < 500 ms |
| p90 API latency | < 200 ms |
| Error rate | < 1% |
| Throughput | > 500 req/s sustained |

> ⚠️ **Warning:** The load test fires real requests to the live API. Each request creates a DynamoDB write. Run with small `--total` values first to validate, then scale up. Always have a DynamoDB cost estimate before running 1M requests.

---

## Manual Testing with cURL

Replace `$API_URL` and `$ADMIN_KEY` with your values.

```bash
export API_URL="https://n20mxucrj4.execute-api.us-east-1.amazonaws.com/Prod"
export ADMIN_KEY="your-admin-key"
```

### Join the queue

```bash
curl -s -X POST "$API_URL/queue/join" \
  -H "Content-Type: application/json" \
  -d '{"eventId": "1001", "userId": "FAN-TEST-001"}' | python -m json.tool
```

Expected: HTTP 201, body contains `queuePosition`, `status: "WAITING"`, `estimatedWaitMinutes`.

### Check queue status

```bash
curl -s "$API_URL/queue/status?eventId=1001&userId=FAN-TEST-001" | python -m json.tool
```

Expected: HTTP 200, body contains `queuePosition`, `status`, `estimatedWaitMinutes`.

### Leave the queue

```bash
curl -s -X POST "$API_URL/queue/leave" \
  -H "Content-Type: application/json" \
  -d '{"eventId": "1001", "userId": "FAN-TEST-001"}' | python -m json.tool
```

Expected: HTTP 200, `message: "You have left the queue."`.

### Admit a batch (admin — requires API key)

```bash
curl -s -X POST "$API_URL/queue/admit" \
  -H "Content-Type: application/json" \
  -H "x-admin-api-key: $ADMIN_KEY" \
  -d '{"eventId": "1001", "batchSize": 5}' | python -m json.tool
```

Expected: HTTP 200, `admittedUsers`, `remainingQueue`, `admittedUserIds`.

Calling without the key should return 403 Forbidden.

### Validate an admission token

```bash
curl -s -X POST "$API_URL/token/validate" \
  -H "Content-Type: application/json" \
  -d '{"token": "PASTE-TOKEN-ID-HERE"}' | python -m json.tool
```

### Get event details

```bash
curl -s "$API_URL/event/1001" | python -m json.tool
```

### Get queue statistics

```bash
curl -s "$API_URL/event/1001/stats" | python -m json.tool
```

---

## Testing the Frontend Locally

The frontend is a static SPA — open it directly in a browser:

```bash
# From the project root
start frontend/index.html         # Windows
open frontend/index.html          # macOS
xdg-open frontend/index.html      # Linux
```

Or serve it with any static server:

```bash
# Python built-in server
python -m http.server 8080 --directory frontend
# Then open http://localhost:8080
```

**Manual checks:**
1. Home page loads with particle background and role cards
2. Admin card → Admin Dashboard page (event selector populates)
3. User card → Events List (6 event cards appear)
4. Click an event card → Event Detail page
5. Enter a Fan ID and click "Join Queue" → success toast and position shown
6. Click "Check My Status" → status panel updates
7. Click "Leave Queue" → confirm dialog, then success
8. Admin Dashboard: select event, click Refresh, admit a batch

---

## SAM Local Testing

Test Lambda functions locally without deploying:

```bash
# Build first
sam build

# Start local API (runs on http://127.0.0.1:3000)
sam local start-api

# Invoke a single function with a test event
sam local invoke JoinQueueFunction --event events/join_queue.json
sam local invoke QueueStatusFunction --event events/queue_status.json
sam local invoke AdmitUsersFunction --event events/admit_users.json
```

> SAM Local requires Docker. For local DynamoDB, use `docker run -p 8000:8000 amazon/dynamodb-local` and set `AWS_SAM_LOCAL=true` + override `TABLE_NAME` to point at the local endpoint.

---

## Security Testing Checklist

| Test | Expected result |
|---|---|
| `POST /queue/admit` without `x-admin-api-key` header | 403 Forbidden |
| `POST /queue/admit` with wrong API key | 403 Forbidden |
| `POST /queue/admit` with correct API key | 200 OK |
| `POST /queue/join` with `eventId` of 200+ characters | 400 Bad Request |
| `POST /queue/join` with `userId` of 200+ characters | 400 Bad Request |
| `GET /queue/status` missing `eventId` | 400 Bad Request |
| `POST /queue/leave` for a non-WAITING user | 409 Conflict |
| `POST /token/validate` with expired token | 401 Unauthorized |
| `POST /token/validate` with non-existent token | 401 Unauthorized |
| CORS header present on all responses | `Access-Control-Allow-Origin: *` |

---

## Test Coverage Targets

| Area | Target |
|---|---|
| Lambda handler branches | ≥ 85% |
| Common utilities | ≥ 90% |
| Model serialization | 100% |
| Error response paths | 100% |

Generate a coverage report:

```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in a browser
```

---

## Performance Targets

These targets apply to the live deployed API and are validated under load:

| Metric | Target |
|---|---|
| p50 API latency | < 100 ms |
| p90 API latency | < 200 ms |
| p99 API latency | < 500 ms |
| Lambda duration | < 500 ms |
| Token validation | < 100 ms |
| Error rate under load | < 1% |
| DynamoDB throttled requests | 0 (investigate any throttles) |

---

## Load Test Workload Profiles

The waiting room sees several distinct traffic shapes — each is tested separately:

| Profile | Endpoint | Characteristics |
|---|---|---|
| **Registration spike** | `POST /queue/join` | Burst writes, short duration, bursty |
| **Queue polling** | `GET /queue/status` | Continuous, read-heavy, long duration — dominant traffic share |
| **Admission** | `POST /queue/admit` | Periodic, write-heavy batches |
| **Token validation** | `POST /token/validate` | Short bursts as admitted users check out |
| **Mixed realistic** | All | 20% join · 65% status · 10% token · 5% event lookup |

Concurrency levels to test at: 100 · 1,000 · 10,000 · 50,000+.

---

## Failure Testing Checklist

| Condition | Expected Behavior |
|---|---|
| Duplicate join request | Returns existing entry (idempotent) |
| Join closed event | 403 Forbidden |
| Status for unknown user | 404 Not Found |
| Leave when ADMITTED/CANCELLED | 409 Conflict |
| Admit with no waiting users | 200 OK, `admittedUsers: 0` |
| Token expired | 401 Unauthorized |
| Token not found | 401 Unauthorized |
| Missing required field | 400 Bad Request |
| Oversized input | 400 Bad Request |

---

## CI Pipeline

Tests run automatically on every push and pull request via GitHub Actions (`.github/workflows/`). The pipeline:

1. Installs dependencies from `requirements-dev.txt`
2. Runs `make lint` (flake8)
3. Runs `pytest` with coverage
4. Runs `sam validate` to check the SAM template

A failing test or lint error blocks the PR from merging.

---

*For the full deployment walkthrough, see [`13-deployment-guide.md`](13-deployment-guide.md).*
