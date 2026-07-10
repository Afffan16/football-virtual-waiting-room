<div align="center">

# 🏆 Challenge Deliverables

**AWS Builder Center — DynamoDB Football Data Modeling Challenge #1**
*The Virtual Waiting Room: Fairly Queuing 1 Million Fans Under Extreme Load*

**Submitted by:** Muhammad Affan bin Aamir · AWS Student Builder Group Leader

</div>

---

## The Challenge

> *"Tickets go on sale in 10 minutes. One million fans are watching the clock. The stampede is coming."*

When tickets for the biggest match of the year drop, a million fans hit the system simultaneously. Before anyone can buy a seat, the platform must absorb the initial stampede, fairly assign every fan a place in line, and progressively admit them to the purchasing flow without overwhelming downstream systems. A perceived unfairness in the queue — or a system that buckles under the load — can make international headlines.

**The ask:** Design a DynamoDB-powered virtual waiting room that:
- Fairly queues up to **10 million concurrent fans** arriving within seconds
- Assigns each a **verifiable queue position**
- Progressively **promotes batches** from "waiting" to "eligible to browse"
- Handles the initial burst **without dropping or misordering** fans
- Prevents **queue-position gaming**
- Provides **real-time status updates** on position and estimated wait time

---

## Deliverable 1 — DynamoDB Table Design

**Required:** A DynamoDB table design modelling the waiting room queue (fan identifier, queue position, entry timestamp, eligibility status, batch assignment) with a key schema optimized for high-throughput concurrent writes during the initial stampede.

### What I built

A **Single Table Design** (`FootballWaitingRoom`) storing six entity types in one table — differentiated by key prefixes and sort key patterns.

**Queue Entry key schema:**

| Attribute | Value | Purpose |
|---|---|---|
| `PK` | `EVENT#<eventId>` | Groups all queue entries for one event in a single item collection |
| `SK` | `QUEUE#<timestamp_ms>-<uuid8>` | Lexicographically sortable; timestamp ensures order, UUID ensures uniqueness |
| `userId` | Fan identifier | Who joined |
| `status` | `WAITING` / `ADMITTED` / `COMPLETED` / `EXPIRED` / `CANCELLED` / `REGISTRATION_CLOSED` | Eligibility state |
| `joinTime` | ISO 8601 timestamp | Entry timestamp |
| `estimatedWait` | Integer (minutes) | Real-time wait estimate |
| `GSI3SK` | `STATUS#WAITING#<position>` | Enables ordered batch promotion |

**Full entity map:**

| Entity | PK | SK | Purpose |
|---|---|---|---|
| Event | `EVENT#<id>` | `METADATA` | Match metadata (stadium, capacity, status) |
| **Queue Entry** | `EVENT#<id>` | `QUEUE#<ts-uuid>` | Fan's place in the queue |
| Queue Registration Guard | `USER#<id>` | `QUEUE#EVENT#<eventId>` | Prevents duplicate active registration and points to the queue row |
| Admission Token | `TOKEN#<id>` | `METADATA` | Short-lived checkout credential (TTL) |
| Statistics | `EVENT#<id>` | `STATS` and `STATS#SHARD#nn` | Base stats metadata plus sharded hot counters |
| User | `USER#<id>` | `PROFILE` | Fan profile |
| Session | `USER#<id>` | `SESSION#ACTIVE` | Active session (TTL) |

**Table configuration:** On-Demand billing · DynamoDB Streams (`NEW_AND_OLD_IMAGES`) · TTL on `ttl` attribute · Point-in-Time Recovery · Server-Side Encryption.

**Key files:**
- Schema definition: [`docs/05-table-schema.md`](docs/05-table-schema.md)
- Data model reasoning: [`docs/04-data-model.md`](docs/04-data-model.md)
- Infrastructure as Code: [`template.yaml`](template.yaml)
- DynamoDB models: [`src/common/models.py`](src/common/models.py)

---

## Deliverable 2 — Fair Queue Position Assignment

**Required:** An explanation of how fans are assigned a fair queue position when they arrive, including how the design handles clock skew and near-simultaneous arrivals at scale.

### What I built

Queue positions are assigned using a **timestamp + UUID jitter** strategy:

```
position = f"{timestamp_ms:014d}-{uuid4_hex[:8]}"
# Example: "01783619782717-a1b2c3d4"
```

**Why this works:**

| Problem | Solution |
|---|---|
| Fair ordering | Millisecond-precision timestamp ensures first-come-first-served within normal human timescales |
| Clock skew | Positions are assigned **server-side** inside the Lambda — the client's clock is never trusted |
| Near-simultaneous arrivals | The 8-character UUID suffix guarantees uniqueness and provides randomised tie-breaking among fans who arrive in the same millisecond |
| Gaming prevention | Position is determined at server-side write time, not derived from anything the client supplies. A transactional write creates both the queue row and the per-user registration guard, preventing duplicate active joins |
| Hot partitions | **No atomic counter** is used for position assignment. An atomic counter on a single Stats item would become a hot key under 10M concurrent writes. The timestamp-uuid approach is paired with sharded stats counters to keep the join path distributed |

The position string is **lexicographically sortable**, so DynamoDB's native sort key ordering gives the correct admission sequence with zero additional computation.

**Key files:**
- Position generation: [`src/common/utils.py`](src/common/utils.py) → `generate_queue_position()`
- Join handler: [`src/join_queue/app.py`](src/join_queue/app.py)
- Access pattern analysis: [`docs/03-access-patterns.md`](docs/03-access-patterns.md)

---

## Deliverable 3 — Batch Promotion Strategy

**Required:** A batch promotion strategy describing how groups of fans move from "waiting" to "eligible to browse" — including how batch size is determined, how promotion is triggered, and how over-promotion is prevented.

### What I built

**Promotion flow:**

```
POST /queue/admit  →  Query GSI3 (WAITING, ordered by position)
                   →  For each user: conditional UpdateItem (WAITING → ADMITTED)
                   →  Generate TTL-bearing admission token
                   →  Update STATS item
```

**How batch size is determined:**

Two modes are supported:

1. **Fixed batch** — admin specifies `batchSize` (e.g. `{"eventId": "1001", "batchSize": 50}`). Maximum capped at 500.

2. **Capacity-aware auto-fill** — pass `capacityMode: true`. The system reads the current `admittedUsers` counter from the STATS item, computes `availableSlots = purchasingCapacity − admittedUsers`, and admits exactly that many — never more. This is the stretch goal implementation (see Deliverable 5).

**How promotion is triggered:**

- Manually by an admin via `POST /queue/admit`
- The endpoint is designed stateless so it can be placed on a CloudWatch Events / EventBridge schedule for automatic periodic promotion

**Preventing over-admission:**

- Each user update uses a **conditional write**: `condition_expression="#status = :current_status"` — if a user's status changed between the GSI3 query and the update (race condition), the write is skipped, not retried as a double-admit
- The `admittedUsers` counter in STATS is updated atomically with `ADD`
- In `capacityMode`, the slot calculation happens before the batch query, bounding the batch to available slots

**Ordering guarantee:** GSI3 sort key is `STATUS#WAITING#<position>` — querying with `begins_with("STATUS#WAITING#")` in ascending order gives the exact front-of-queue batch every time.

**Key files:**
- Admission handler: [`src/admit_users/app.py`](src/admit_users/app.py)
- GSI3 design: [`docs/06-index-design.md`](docs/06-index-design.md)
- API contract: [`docs/08-api-design.md`](docs/08-api-design.md)

---

## Deliverable 4 — Fan Status Query Design

**Required:** A fan status query design that lets each fan check their current position, estimated wait time, and eligibility status with low-latency reads — even while millions of fans are polling simultaneously.

### What I built

**GSI1 — User Queue Lookup:**

```
GSI1PK = USER#<userId>
GSI1SK = EVENT#<eventId>
```

A single `Query` on GSI1 returns the fan's queue entry in one request — no scan, no filter expression, no table traversal. This is the only access pattern that matters for the 65% of traffic that is status polling.

**Response includes:**

```json
{
  "eventId": "1001",
  "userId": "FAN-001",
  "queuePosition": "01783619782717-a1b2c3d4",
  "status": "WAITING",
  "estimatedWaitMinutes": 12
}
```

**Estimated wait calculation:** computed from the difference between the fan's timestamp-based position and `currentlyServingPosition` (stored in the STATS item). 1 minute of wait per 10 seconds of queue backlog. This is a deliberate approximation — serving exact global position would require a scan or expensive counter, while this approach is a single `GetItem` on the STATS item.

**Why GSI1 scales under millions of pollers:** each fan's status check hits a separate partition key (`USER#<userId>`) — there is no shared hot key. DynamoDB distributes the read load across the table naturally.

**Key files:**
- Status handler: [`src/queue_status/app.py`](src/queue_status/app.py)
- GSI1 rationale: [`docs/06-index-design.md`](docs/06-index-design.md)
- Wait estimate logic: [`src/common/utils.py`](src/common/utils.py) → `estimate_wait_minutes()`

---

## Deliverable 5 — Stretch Goal: 1,000-Slot Active Purchaser Cap

**Required (stretch):** A mechanism ensuring the number of active users purchasing tickets stays at 1,000, drawing new batches from the waiting room to fill back to 1,000 without waiting for all slots to empty.

### What I built

Capacity-aware admission mode added to `POST /queue/admit`:

```json
POST /queue/admit
{ "eventId": "1001", "capacityMode": true, "purchasingCapacity": 1000 }
```

**Logic:**

```python
currently_admitted = stats.get("admittedUsers", 0)
available_slots = max(0, purchasing_capacity - currently_admitted)
# Only admit exactly as many fans as there are free slots
batch_size = available_slots
```

**Responses:**

- If slots are available: admits `available_slots` fans, returns `activePurchasers` and `purchasingCapacity`
- If at capacity: returns `capacityFull: true`; remaining waiting registrations can be moved to `REGISTRATION_CLOSED` and the event can be marked `CLOSED`

**Frontend integration:** the Admin Dashboard has an "⚡ Auto-Fill" button that calls `capacityMode: true`. An admin (or automated scheduler) can repeatedly call this to maintain the purchasing pool near 1,000 without over-admitting.

**Environment variable:** `PURCHASING_CAPACITY` (default 1000) — configurable via SAM parameter `PurchasingCapacity`.

**Key files:**
- Implementation: [`src/admit_users/app.py`](src/admit_users/app.py)
- Constant definition: [`src/common/constants.py`](src/common/constants.py) → `PURCHASING_CAPACITY`
- SAM parameter: [`template.yaml`](template.yaml)
- Admin UI: [`frontend/app.js`](frontend/app.js) → `adminAdmitCapacity()`

---

## Beyond the Deliverables — What Else Was Built

The challenge asked for a data model. This submission delivers a **fully deployed, production-quality system** on top of it.

| Extra | Detail |
|---|---|
| **10 Lambda functions** | One per operation — Join, Status, Leave, Admit, Admin Queue List, Validate Token, Event Lookup, Events List, Admin Event Create, Statistics |
| **Live deployed API** | `https://n20mxucrj4.execute-api.us-east-1.amazonaws.com/Prod` |
| **Frontend SPA** | Glassmorphism dark-themed app with Admin Dashboard and User flow |
| **DynamoDB-backed events** | `GET /events` loads the event catalog; admin `POST /event` creates new events and stats rows |
| **1M-request load test** | `scripts/mass_ticket_requests.py` — asyncio + aiohttp, p50/p90/p95/p99 reporting |
| **API security** | Admin key auth (`hmac.compare_digest`), input validation, throttling |
| **Infrastructure as Code** | Full AWS SAM template — one command deploys everything |
| **13-document engineering log** | Every design decision documented in `docs/` |

---

## Key Design Decisions Summary

| Decision | Reasoning |
|---|---|
| Timestamp + UUID queue position (no atomic counter) | Atomic counters create a single hot partition under 10M writes. Distributed timestamp-uuid is fully parallel |
| Single Table Design | All access patterns served from one table — fewer round trips, lower latency |
| GSI3 sort key `STATUS#<state>#<position>` | Enables `begins_with("STATUS#WAITING#")` to return the exact front-of-queue batch ordered correctly |
| GSI1 `USER#<id>` partition key | Status checks (65% of traffic) hit a separate partition per user — no shared hot key |
| Immutable queue positions | Only `status` changes; positions never rewrite — flat write volume at scale |
| TTL for tokens and sessions | Zero cleanup jobs; DynamoDB handles expiry automatically |
| Transactional join guard | Queue row and active registration guard are written atomically; duplicate joins return the existing active registration |

---

## Repository

**GitHub:** [github.com/Afffan16/football-virtual-waiting-room](https://github.com/Afffan16/football-virtual-waiting-room)

| File / Folder | What it is |
|---|---|
| [`template.yaml`](template.yaml) | SAM infrastructure — DynamoDB, Lambda, API Gateway |
| [`src/`](src/) | All Lambda handlers + shared common library |
| [`docs/`](docs/) | 13-document engineering log |
| [`frontend/`](frontend/) | Live SPA connected to the deployed API |
| [`scripts/mass_ticket_requests.py`](scripts/mass_ticket_requests.py) | 1M-request async load test |
| [`scripts/clear_event_records.py`](scripts/clear_event_records.py) | Reset queue/session/token records while preserving event metadata |
| [`DELIVERABLES.md`](DELIVERABLES.md) | This file |
| [`README.md`](README.md) | Full project overview |

---

<div align="center">

**Muhammad Affan bin Aamir**
Software Engineer · Cloud Data Engineer · AWS Student Builder Group Leader

[![GitHub](https://img.shields.io/badge/GitHub-Afffan16-181717?logo=github&logoColor=white)](https://github.com/Afffan16)

*Built with AWS Lambda · DynamoDB · API Gateway · SAM · Python 3.14*

</div>
