# 📈 Load Testing Strategy

**Author:** Muhammad Affan bin Aamir · **Version:** 1.0 · **Document:** `docs/12-load-testing.md`

← [Back: Testing Plan](11-testing-plan.md) · Next: [Cost Estimation →](13-cost-estimation.md)

---

## Table of Contents

- [Purpose](#purpose)
- [Objectives](#objectives)
- [Workload Profiles](#workload-profiles)
- [Load Levels](#load-levels)
- [Test Scenarios](#test-scenarios)
- [Metrics Collected](#metrics-collected)
- [Success Criteria](#success-criteria)
- [Test Tools](#test-tools)
- [Example k6 Workloads](#example-k6-workloads)
- [Monitoring](#monitoring)
- [Bottleneck Analysis](#bottleneck-analysis)
- [Failure Conditions](#failure-conditions)
- [Reporting](#reporting)
- [Optimization Recommendations](#optimization-recommendations)
- [Summary](#summary)

---

## Purpose

This document defines the performance validation strategy for the Football Virtual Waiting Room — the load-testing half of the broader plan in [`11-testing-plan.md`](11-testing-plan.md).

Functional testing confirms the system behaves correctly. Load testing confirms it stays correct, responsive, and cost-efficient under the kind of sustained and burst traffic a real ticket release produces.

---

## Objectives

Load tests verify:

- API responsiveness under load
- DynamoDB scalability
- Lambda scalability
- Admission throughput
- Queue fairness, even while under stress
- Error handling at scale
- Cost efficiency under load

---

## Workload Profiles

The waiting room sees several distinct traffic shapes, not one uniform load. Each is modeled separately.

### Profile 1 — Registration Spike

Occurs the moment ticket sales open.

| | |
|---|---|
| **Characteristics** | Millions of concurrent users · very high write throughput · short duration · bursty |
| **Operations** | `POST /queue/join` |
| **Primary AWS Services** | API Gateway · Lambda · DynamoDB |

### Profile 2 — Queue Polling

Sustained traffic after users have already joined.

| | |
|---|---|
| **Characteristics** | Continuous · read-heavy · long duration |
| **Operations** | `GET /queue/status` |

This is the profile that matters most in practice, since queue-status polling makes up the dominant share of expected traffic, per the distribution modeled in [`03-access-patterns.md#expected-request-distribution`](03-access-patterns.md#expected-request-distribution).

### Profile 3 — Admission

Periodic batch processing of waiting users.

| | |
|---|---|
| **Operations** | Query queue · update queue entries · generate tokens |

### Profile 4 — Token Validation

Occurs as admitted users move into ticket purchasing.

| | |
|---|---|
| **Operations** | `POST /token/validate` |

---

## Load Levels

| Stage | Concurrent Users |
|---|---|
| Small | 100 |
| Medium | 1,000 |
| Large | 10,000 |
| Stress | 50,000 |
| Extreme (simulation) | 100,000+ |

> Simulating millions of real clients isn't practical in a development environment. Instead, results from controlled high-concurrency runs are extrapolated, and AWS service scaling is monitored directly for signs it won't hold at higher volumes.

---

## Test Scenarios

### Scenario 1 — Join Queue

Users continuously submit registration requests.

**Expected:** successful registrations · no duplicate entries · stable latency · no table scans.

### Scenario 2 — Queue Status Polling

Users poll queue status every few seconds.

**Expected:** consistent response times · low DynamoDB read latency · minimal throttling.

### Scenario 3 — Mixed Traffic

A blended profile approximating real-world behavior:

| Traffic Type | Share |
|---|---|
| Join Queue | 20% |
| Queue Status | 65% |
| Token Validation | 10% |
| Event Lookup | 5% |

**Expected:** the system stays responsive under this realistic mix, not just under single-operation tests.

### Scenario 4 — Admission Processing

The admission service processes users in batches while client traffic continues in parallel.

**Expected:** ordered admission · stable API performance throughout · no inconsistent queue states.

---

## Metrics Collected

### API Gateway

Request count · latency · integration latency · 4XX errors · 5XX errors.

### Lambda

Invocations · duration · concurrent executions · throttles · errors.

### DynamoDB

Read capacity consumption · write capacity consumption · successful requests · throttled requests · system errors · latency.

### Client-Side

Average response time · P95 latency · P99 latency · error rate · requests per second.

---

## Success Criteria

| Metric | Target |
|---|---|
| Average API Latency | < 200 ms |
| P95 Latency | < 500 ms |
| Error Rate | < 1% |
| DynamoDB Throttles | 0 (or investigated if observed) |
| Lambda Errors | 0 under normal operation |

These targets mirror the ones in [`11-testing-plan.md#performance-targets`](11-testing-plan.md#performance-targets), and should be read relative to workload shape, AWS region, and account-level service quotas.

---

## Test Tools

**Primary:** k6 · Artillery · Locust

**Optional:** JMeter · Gatling

---

## Example k6 Workloads

**Registration spike:**

```javascript
export default function () {
    // POST /queue/join
}
```

**Queue polling:**

```javascript
export default function () {
    // GET /queue/status
}
```

Full scripts live in `tests/load/`, referenced from the repository structure in [`00-project-status.md`](00-project-status.md#repository-structure).

---

## Monitoring

CloudWatch dashboards display, in real time during each run:

- API latency
- Lambda concurrency
- DynamoDB request metrics
- Error counts
- Queue admission rate

---

## Bottleneck Analysis

Likely bottleneck candidates, in rough order of expectation:

| Bottleneck | Where it shows up |
|---|---|
| API Gateway throttling | Sustained high-concurrency runs |
| Lambda concurrency limits | Sudden registration spikes |
| DynamoDB hot partitions | A single wildly popular event |
| Excessive client polling | Long-running queue-status scenarios |

Every bottleneck actually observed during testing is investigated and documented rather than tuned away silently — the reasoning behind any resulting design change belongs in [`14-optimization.md`](14-optimization.md).

---

## Failure Conditions

A load test run is considered failed if:

- High error rates persist rather than recovering
- Queue entries become inconsistent
- Duplicate registrations occur under concurrent load
- Latency exceeds what's acceptable for the tested workload
- DynamoDB experiences sustained throttling with no mitigation in place

---

## Reporting

Each run captures: date, workload profile, concurrent users, duration, throughput, average latency, P95 latency, error rate, observations, and recommendations.

**Example report:**

| Metric | Result |
|---|---|
| Concurrent Users | 10,000 |
| Duration | 15 min |
| Avg Latency | 145 ms |
| P95 Latency | 310 ms |
| Error Rate | 0.2% |
| DynamoDB Throttles | 0 |

---

## Optimization Recommendations

Where testing surfaces a real bottleneck, the options are:

- Adaptive retry with exponential backoff
- WebSocket or Server-Sent Events, to cut down on raw polling volume
- Write sharding for events with extreme registration spikes (see [`04-data-model.md#sharding-strategy`](04-data-model.md#sharding-strategy))
- Batch operations where the access pattern allows it
- CloudWatch alarms tuned for proactive detection, not just after-the-fact review

The full breakdown of which of these were actually needed, and why, is in [`14-optimization.md`](14-optimization.md).

---

## Summary

This strategy validates that the Football Virtual Waiting Room stays responsive, consistent, and scalable under traffic that actually resembles a high-demand ticket release — and gives measurable evidence that the DynamoDB design in [`05-table-schema.md`](05-table-schema.md) holds up under that load, not just on paper.

Next: [`13-cost-estimation.md`](13-cost-estimation.md) translates this traffic modeling into an expected AWS cost profile.