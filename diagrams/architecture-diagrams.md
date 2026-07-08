# Football Virtual Waiting Room — Architecture Diagrams

---

## 1. High-Level System Architecture

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
│  │POST /validate │  │GET /event/{id}   │  │GET /event/stats  │  │
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
│  │  Statistics  │   • Python 3.12    • Powertools Logger         │
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

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     FootballWaitingRoom Table                            │
├──────────────────┬──────────────────┬────────────────────────────────────┤
│       PK         │       SK         │         Entity / Data              │
├──────────────────┼──────────────────┼────────────────────────────────────┤
│ EVENT#1001       │ METADATA         │ Event details (match, stadium...)  │
│ EVENT#1001       │ STATS            │ Queue statistics (counters)        │
│ EVENT#1001       │ QUEUE#0000000001 │ Queue entry (user, position, ...)  │
│ EVENT#1001       │ QUEUE#0000000002 │ Queue entry (user, position, ...)  │
│ EVENT#1001       │ QUEUE#0000000003 │ Queue entry (user, position, ...)  │
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
│  │ EVENT#1001           │ STATUS#WAITING#0000000001            │         │
│  │ EVENT#1001           │ STATUS#WAITING#0000000002            │         │
│  │ EVENT#1001           │ STATUS#ADMITTED#0000000003           │         │
│  └──────────────────────┴──────────────────────────────────────┘         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. User Journey Flow

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
  │  3. Check duplicate (GSI1)   │
  │  4. Atomic counter → pos     │
  │  5. Conditional PutItem      │
  │  6. Increment waitingUsers   │
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

```
  API Gateway (WaitingRoomApi)
  │
  ├── POST  /queue/join        →  JoinQueueFunction
  │                                 ├── DynamoDB: GetItem (event check)
  │                                 ├── DynamoDB: Query GSI1 (duplicate check)
  │                                 ├── DynamoDB: UpdateItem (atomic counter)
  │                                 ├── DynamoDB: PutItem (conditional write)
  │                                 └── DynamoDB: UpdateItem (stats)
  │
  ├── GET   /queue/status      →  QueueStatusFunction
  │                                 └── DynamoDB: Query GSI1
  │
  ├── POST  /queue/leave       →  LeaveQueueFunction
  │                                 ├── DynamoDB: Query GSI1
  │                                 ├── DynamoDB: UpdateItem (conditional)
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
  ├── GET   /event/{eventId}   →  EventLookupFunction
  │                                 └── DynamoDB: GetItem
  │
  └── GET   /event/{id}/stats  →  StatisticsFunction
                                    └── DynamoDB: GetItem
```

---

## 5. IAM Permission Model

```
  ┌─────────────────────┐     ┌────────────────────────┐
  │  Read-Only Lambdas  │     │  Read-Write Lambdas    │
  │                     │     │                        │
  │  • Queue Status     │     │  • Join Queue          │
  │  • Event Lookup     │     │  • Leave Queue         │
  │  • Statistics       │     │  • Admit Users         │
  │  • Validate Token   │     │                        │
  │                     │     │                        │
  │  Policy:            │     │  Policy:               │
  │  DynamoDBReadPolicy │     │  DynamoDBCrudPolicy    │
  └─────────────────────┘     └────────────────────────┘
            │                           │
            └───────────┬───────────────┘
                        ▼
              ┌──────────────────┐
              │  DynamoDB Table  │
              │  (FootballWR)    │
              └──────────────────┘
```
