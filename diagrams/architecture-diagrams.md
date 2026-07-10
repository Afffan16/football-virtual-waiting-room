# 🗺️ Architecture Diagrams

**Document:** `diagrams/architecture-diagrams.md`

← [Back to Project Status](../docs/00-project-status.md)

Companion diagrams for [`07-system-architecture.md`](../docs/07-system-architecture.md) and [`05-table-schema.md`](../docs/05-table-schema.md). Where those documents use Mermaid for flow and sequence diagrams, the diagrams here use precise ASCII layouts — better suited for showing exact key structures, byte-for-byte item shapes, and permission boundaries.

---

## Table of Contents

- [1. High-Level System Architecture](#1-high-level-system-architecture)
- [2. DynamoDB Single Table Design](#2-dynamodb-single-table-design)
- [3. User Journey Flow](#3-user-journey-flow)
- [4. API Endpoint Map](#4-api-endpoint-map)
- [5. IAM Permission Model](#5-iam-permission-model)
- [6. TTL & Streams Cleanup Flow](#6-ttl--streams-cleanup-flow)
- [7. CI/CD Pipeline](#7-cicd-pipeline)

---

## 1. High-Level System Architecture

End-to-end request path, from client to storage to observability. Matches the component breakdown in [`07-system-architecture.md#component-details`](../docs/07-system-architecture.md#component-details).

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLIENTS                                │
│              (Web Browser / Mobile App / API Consumer)           │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AMAZON API GATEWAY                          │
│                                                                 │
│  ┌──────────┐  ┌────────────┐  ┌───────────┐  ┌─────────────┐  │
│  │POST /join │  │GET /status │  │POST /leave│  │POST /admit  │  │
│  └──────────┘  └────────────┘  └───────────┘  └─────────────┘  │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │POST /validate │  │GET /events       │  │POST /event       │  │
│  └──────────────┘  └──────────────────┘  └──────────────────┘  │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │GET /event/{id}   │  │GET /event/stats  │                     │
│  └──────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                 │
│  • CORS Enabled    • X-Ray Tracing    • CloudWatch Metrics      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       AWS LAMBDA                                │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Join Queue   │  │ Queue Status │  │ Leave Queue  │          │
│  │  (POST)       │  │  (GET)       │  │  (POST)      │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Admit Users  │  │Validate Token│  │ Event Lookup │          │
│  │  (POST)      │  │  (POST)      │  │  (GET)       │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│  ┌──────────────┐                                               │
│  │  Statistics  │   • Python 3.14    • Powertools Logger         │
│  │  (GET)       │   • 256 MB Memory  • 30s Timeout              │
│  └──────┬───────┘                                               │
│         │          Shared: src/common/ (constants, dynamodb,     │
│         │                   models, responses, utils, logger)    │
└─────────┼───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AMAZON DYNAMODB                             │
│                                                                 │
│  Table: FootballWaitingRoom                                     │
│  Billing: PAY_PER_REQUEST (On-Demand)                           │
│                                                                 │
│  Primary Key:  PK (HASH) + SK (RANGE)                           │
│                                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                         │
│  │  GSI1   │  │  GSI2   │  │  GSI3   │                         │
│  │  User   │  │  Token  │  │  Admin  │                         │
│  │ Lookup  │  │ Lookup  │  │  View   │                         │
│  └─────────┘  └─────────┘  └─────────┘                         │
│                                                                 │
│  • TTL Enabled       • DynamoDB Streams (NEW_AND_OLD_IMAGES)    │
│  • SSE Encryption    • Point-in-Time Recovery                   │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AMAZON CLOUDWATCH                            │
│                                                                 │
│  • Lambda Logs (JSON structured via Powertools)                 │
│  • API Gateway Access Logs                                      │
│  • DynamoDB Metrics (consumed RCU/WCU, throttles)               │
│  • Custom Metrics & Alarms                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. DynamoDB Single Table Design

The physical layout behind [`05-table-schema.md`](../docs/05-table-schema.md), with all three GSIs from [`06-index-design.md`](../docs/06-index-design.md) shown side by side.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     FootballWaitingRoom Table                            │
├──────────────────┬──────────────────┬────────────────────────────────────┤
│       PK         │       SK         │         Entity / Data              │
├──────────────────┼──────────────────┼────────────────────────────────────┤
│ EVENT#1001       │ METADATA         │ Event details (match, stadium...)  │
│ EVENT#1001       │ STATS            │ Queue statistics (counters)        │
│ EVENT#1001#SHARD#00 │ QUEUE#2026...#a1 │ Queue entry (user, position)   │
│ EVENT#1001#SHARD#01 │ QUEUE#2026...#b2 │ Queue entry (user, position)   │
│ EVENT#1001#SHARD#02 │ QUEUE#2026...#c3 │ Queue entry (user, position)   │
│ TOKEN#A1B2C3D4   │ METADATA         │ Admission token (ttl, status)     │
├──────────────────┴──────────────────┴────────────────────────────────────┤
│                                                                          │
│  GSI1 — User Queue Lookup                                                │
│  ┌──────────────────────┬──────────────────────┐                         │
│  │      GSI1PK          │      GSI1SK          │                         │
│  ├──────────────────────┼──────────────────────┤                         │
│  │ USER#user_001        │ EVENT#1001           │  → Queue Entry          │
│  │ USER#user_002        │ EVENT#1001           │  → Queue Entry          │
│  └──────────────────────┴──────────────────────┘                         │
│                                                                          │
│  GSI2 — Token Lookup                                                     │
│  ┌──────────────────────┬──────────────────────┐                         │
│  │      GSI2PK          │      GSI2SK          │                         │
│  ├──────────────────────┼──────────────────────┤                         │
│  │ TOKEN#A1B2C3D4       │ STATUS#ACTIVE        │  → Token Details        │
│  └──────────────────────┴──────────────────────┘                         │
│                                                                          │
│  GSI3 — Admin Queue View (sorted by status + position)                   │
│  ┌──────────────────────┬──────────────────────────────────────┐         │
│  │      GSI3PK          │      GSI3SK                          │         │
│  ├──────────────────────┼──────────────────────────────────────┤         │
│  │ EVENT#1001#SHARD#00  │ STATUS#WAITING#2026...#a1           │         │
│  │ EVENT#1001#SHARD#01  │ STATUS#WAITING#2026...#b2           │         │
│  │ EVENT#1001#SHARD#02  │ STATUS#ADMITTED#2026...#c3          │         │
│  └──────────────────────┴──────────────────────────────────────┘         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. User Journey Flow

The same happy path shown as a sequence diagram in [`07-system-architecture.md#request-flows`](../docs/07-system-architecture.md#request-flows), here shown with the specific DynamoDB operation behind every step.

```
  ┌──────────┐
  │   User   │
  └────┬─────┘
       │
       │  POST /queue/join { eventId, userId }
       ▼
  ┌──────────────────────────────┐
  │       Join Queue Lambda      │
  │                              │
  │  1. Validate input           │
  │  2. Check event is OPEN      │
  │  3. Read sharded stats       │
  │  4. Generate timestamp pos   │
  │  5. Transact guard + queue   │
  │  6. Increment stat shard     │
  └──────────┬───────────────────┘
             │  201 Created { queuePosition, estimatedWait }
             ▼
  ┌──────────────────────────────┐
  │   User Polls Queue Status    │
  │                              │
  │  GET /queue/status           │
  │    ?eventId=1001             │
  │    &userId=user_001          │
  └──────────┬───────────────────┘
             │  200 OK { position, status, estimatedWait }
             ▼
  ┌──────────────────────────────┐
  │    Admin Admits Batch         │
  │                              │
  │  POST /queue/admit           │
  │  { eventId, batchSize }      │
  │                              │
  │  1. Query GSI3 for WAITING   │
  │  2. Update status→ADMITTED   │
  │  3. Generate token (TTL)     │
  │  4. Update stats counters    │
  └──────────┬───────────────────┘
             │
             ▼
  ┌──────────────────────────────┐
  │   User Validates Token       │
  │                              │
  │  POST /token/validate        │
  │  { token }                   │
  │                              │
  │  1. Look up token            │
  │  2. Check ACTIVE status      │
  │  3. Check expiration         │
  └──────────┬───────────────────┘
             │  200 OK { valid: true }
             ▼
  ┌──────────────────────────────┐
  │   User Accesses Ticketing    │
  │   (Protected Downstream)     │
  └──────────────────────────────┘

  ═══════════════════════════════

  Alternative Flows:

  ┌──────────┐
  │   User   │───── POST /queue/leave ────▶ Status → CANCELLED
  └──────────┘                               waitingUsers--
                                             cancelledUsers++

  ┌──────────┐
  │  Timer   │───── Token TTL expires ────▶ DynamoDB TTL auto-deletes
  └──────────┘
```

---

## 4. API Endpoint Map

Every route from [`08-api-design.md`](../docs/08-api-design.md), mapped to its Lambda function and the exact DynamoDB calls each one makes.

```
  API Gateway (WaitingRoomApi)
  │
  ├── POST  /queue/join        →  JoinQueueFunction
  │                                 ├── DynamoDB: GetItem (event check)
  │                                 ├── DynamoDB: GetItem (stats/shard check)
  │                                 ├── DynamoDB: TransactWriteItems (guard + queue)
  │                                 └── DynamoDB: UpdateItem (sharded stats)
  │
  ├── GET   /queue/status      →  QueueStatusFunction
  │                                 ├── DynamoDB: GetItem (registration guard)
  │                                 └── DynamoDB: GetItem (queue row)
  │
  ├── POST  /queue/leave       →  LeaveQueueFunction
  │                                 ├── DynamoDB: GetItem (registration guard)
  │                                 ├── DynamoDB: UpdateItem (conditional)
  │                                 ├── DynamoDB: DeleteItem (registration guard)
  │                                 └── DynamoDB: UpdateItem (stats x2)
  │
  ├── POST  /queue/admit       →  AdmitUsersFunction
  │                                 ├── DynamoDB: Query GSI3
  │                                 ├── DynamoDB: UpdateItem (per user)
  │                                 ├── DynamoDB: PutItem (token per user)
  │                                 └── DynamoDB: UpdateItem (stats x2)
  │
  ├── POST  /token/validate    →  ValidateTokenFunction
  │                                 └── DynamoDB: GetItem
  │
  ├── GET   /events            →  EventsFunction
  │                                 └── DynamoDB: Scan event metadata
  │
  ├── POST  /event             →  AdminEventFunction
  │                                 └── DynamoDB: TransactWriteItems (event + stats)
  │
  ├── GET   /queue/admin/list  →  AdminQueueListFunction
  │                                 └── DynamoDB: Query GSI3
  │
  ├── GET   /event/{eventId}   →  EventLookupFunction
  │                                 └── DynamoDB: GetItem
  │
  └── GET   /event/{id}/stats  →  StatisticsFunction
                                    └── DynamoDB: GetItem
```

---

## 5. IAM Permission Model

Every Lambda gets exactly the access it needs and nothing more — the least-privilege split described in [`07-system-architecture.md#8-aws-iam`](../docs/07-system-architecture.md#8-aws-iam).

```
  ┌─────────────────────┐     ┌────────────────────────┐
  │  Read-Only Lambdas  │     │  Read-Write Lambdas    │
  │                     │     │                        │
  │  • Queue Status     │     │  • Join Queue          │
  │  • Events List      │     │  • Admin Event Create  │
  │  • Event Lookup     │     │  • Leave Queue         │
  │  • Statistics       │     │  • Admit Users         │
  │  • Validate Token   │     │                        │
  │  • Admin Queue List │     │                        │
  │                     │     │                        │
  │  Policy:            │     │  Policy:               │
  │  DynamoDBReadPolicy │     │  DynamoDBCrudPolicy    │
  │                     │     │  + TransactWriteItems  │
  └─────────────────────┘     └────────────────────────┘
            │                           │
            └───────────┬───────────────┘
                        ▼
              ┌──────────────────┐
              │  DynamoDB Table  │
              │  (FootballWR)    │
              └──────────────────┘
```

---

## 6. TTL & Streams Cleanup Flow

How expired items actually leave the table, and how that change becomes visible downstream — the mechanics behind [`04-data-model.md#time-to-live-ttl`](../docs/04-data-model.md#time-to-live-ttl).

```
┌────────────────────────┐
│  Session / Token Item   │
│  ttl = <unix timestamp> │
└───────────┬─────────────┘
            │
            │  Current time passes ttl
            ▼
┌─────────────────────────────────────────┐
│  DynamoDB TTL Background Sweep           │
│  (asynchronous — not instantaneous)      │
└───────────┬───────────────────────────────┘
            │
            │  Item removed
            ▼
┌─────────────────────────────────────────┐
│  DynamoDB Streams                        │
│  REMOVE event (with old image)           │
└───────────┬───────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│  Amazon EventBridge (optional)           │
│  → future consumers: audit log,          │
│    notifications, analytics              │
└─────────────────────────────────────────┘

  No scheduled Lambda. No cron job. No manual cleanup.
```

---

## 7. CI/CD Pipeline

The automated path from a pushed commit to a validated build, per the CI pipeline referenced in [`00-project-status.md#infrastructure`](../docs/00-project-status.md#infrastructure).

```
┌──────────────┐     ┌───────────────────┐     ┌────────────────────┐
│  git push /   │────▶│  GitHub Actions   │────▶│   sam validate     │
│  Pull Request │     │  workflow trigger │     │   (template check) │
└──────────────┘     └───────────────────┘     └──────────┬──────────┘
                                                            │
                                                            ▼
                                                ┌────────────────────┐
                                                │  Install deps       │
                                                │  (requirements.txt, │
                                                │   requirements-dev) │
                                                └──────────┬──────────┘
                                                            │
                                                            ▼
                                                ┌────────────────────┐
                                                │  pytest             │
                                                │  unit + integration │
                                                │  + API test suites  │
                                                └──────────┬──────────┘
                                                            │
                                                    pass ───┴─── fail
                                                     │              │
                                                     ▼              ▼
                                          ┌────────────────┐  ┌───────────────┐
                                          │  sam build      │  │  Block merge   │
                                          │  (build check)  │  │  Report failure│
                                          └────────────────┘  └───────────────┘
```
