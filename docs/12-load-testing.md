# Load Testing Strategy

Author: Muhammad Affan bin Aamir

Version: 1.0

---

# Purpose

This document defines the performance validation strategy for the Football Virtual Waiting Room.

The objective is to verify that the system can handle extremely high traffic while maintaining acceptable latency, availability, and DynamoDB performance.

Unlike functional testing, load testing focuses on system behavior under sustained and burst workloads.

---

# Objectives

The load tests should verify:

- API responsiveness
- DynamoDB scalability
- Lambda scalability
- Admission throughput
- Queue fairness
- Error handling
- Cost efficiency under load

---

# Workload Profiles

The waiting room experiences several distinct traffic patterns.

## Profile 1 — Registration Spike

Occurs when ticket sales begin.

Characteristics:

- Millions of concurrent users
- Very high write throughput
- Short duration
- Burst traffic

Operations:

- POST /queue/join

Primary AWS Services:

- API Gateway
- Lambda
- DynamoDB

---

## Profile 2 — Queue Polling

Occurs after users have joined.

Characteristics:

- Continuous traffic
- Read-heavy
- Long duration

Operations:

- GET /queue/status

---

## Profile 3 — Admission

Periodic processing of waiting users.

Operations:

- Query queue
- Update queue entries
- Generate tokens

---

## Profile 4 — Token Validation

Occurs when admitted users access ticket purchasing.

Operations:

- POST /token/validate

---

# Load Levels

| Stage | Concurrent Users |
|--------|------------------|
| Small | 100 |
| Medium | 1,000 |
| Large | 10,000 |
| Stress | 50,000 |
| Extreme (simulation) | 100,000+ |

Note: Simulating millions of clients is generally impractical in a development environment. Instead, extrapolate results from controlled high-concurrency tests and monitor AWS service scaling.

---

# Test Scenarios

## Scenario 1 — Join Queue

Users continuously submit queue registration requests.

Expected:

- Successful registrations
- No duplicate entries
- Stable latency
- No table scans

---

## Scenario 2 — Queue Status Polling

Users poll queue status every few seconds.

Expected:

- Consistent response times
- Low DynamoDB read latency
- Minimal throttling

---

## Scenario 3 — Mixed Traffic

Traffic distribution:

- 20% Join Queue
- 65% Queue Status
- 10% Token Validation
- 5% Event Lookup

Expected:

System remains responsive under realistic mixed workloads.

---

## Scenario 4 — Admission Processing

The admission service processes users in batches while client traffic continues.

Expected:

- Ordered admission
- Stable API performance
- No inconsistent queue states

---

# Metrics

The following metrics should be collected.

## API Gateway

- Request Count
- Latency
- Integration Latency
- 4XX Errors
- 5XX Errors

---

## Lambda

- Invocations
- Duration
- Concurrent Executions
- Throttles
- Errors

---

## DynamoDB

- Read Capacity Consumption
- Write Capacity Consumption
- Successful Requests
- Throttled Requests
- System Errors
- Latency

---

## Client Metrics

- Average Response Time
- P95 Latency
- P99 Latency
- Error Rate
- Requests per Second

---

# Success Criteria

| Metric | Target |
|---------|---------|
| Average API Latency | < 200 ms |
| P95 Latency | < 500 ms |
| Error Rate | < 1% |
| DynamoDB Throttles | 0 (or investigated if observed) |
| Lambda Errors | 0 (expected during normal operation) |

Targets should be interpreted relative to workload, region, and AWS account quotas.

---

# Test Tools

Recommended:

- k6
- Artillery
- Locust

Optional:

- JMeter
- Gatling

---

# Example k6 Workloads

## Registration Spike

```javascript
export default function () {
    // POST /queue/join
}
```

---

## Queue Polling

```javascript
export default function () {
    // GET /queue/status
}
```

---

# Monitoring

CloudWatch dashboards should display:

- API latency
- Lambda concurrency
- DynamoDB request metrics
- Error counts
- Queue admission rate

---

# Bottleneck Analysis

Possible bottlenecks include:

- API Gateway throttling
- Lambda concurrency limits
- DynamoDB hot partitions
- Excessive client polling

Each bottleneck should be investigated and documented if encountered.

---

# Failure Conditions

The system fails the load test if:

- High error rates persist
- Queue entries become inconsistent
- Duplicate registrations occur
- Latency becomes unacceptable for the defined workload
- DynamoDB experiences sustained throttling without mitigation

---

# Reporting

Each test run should capture:

- Date
- Workload profile
- Concurrent users
- Duration
- Throughput
- Average latency
- P95 latency
- Error rate
- Observations
- Recommendations

Example report:

| Metric | Result |
|---------|--------|
| Concurrent Users | 10,000 |
| Duration | 15 min |
| Avg Latency | 145 ms |
| P95 Latency | 310 ms |
| Error Rate | 0.2% |
| DynamoDB Throttles | 0 |

---

# Optimization Recommendations

If testing identifies bottlenecks, consider:

- Adaptive retry with exponential backoff
- WebSocket or Server-Sent Events to reduce polling
- Write sharding for high-ingest events
- Batch operations where appropriate
- CloudWatch alarms for proactive monitoring

---

# Summary

This load-testing strategy validates that the Football Virtual Waiting Room remains responsive, consistent, and scalable under realistic traffic patterns while providing measurable evidence that the DynamoDB design supports high-demand event workloads.