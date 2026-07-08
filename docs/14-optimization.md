# ⚙️ Performance Optimization Guide

**Author:** Muhammad Affan bin Aamir · **Version:** 1.0 · **Document:** `docs/14-optimization.md`

← [Back: Cost Estimation](13-cost-estimation.md) · Next: [Final Solution →](15-final-solution.md)

---

## Table of Contents

- [Purpose](#purpose)
- [Optimization Goals](#optimization-goals)
- [DynamoDB Optimizations](#dynamodb-optimizations)
- [Lambda Optimizations](#lambda-optimizations)
- [API Gateway Optimizations](#api-gateway-optimizations)
- [CloudWatch Optimization](#cloudwatch-optimization)
- [Cost Optimization](#cost-optimization)
- [Scalability Considerations](#scalability-considerations)
- [Security Optimizations](#security-optimizations)
- [Operational Best Practices](#operational-best-practices)
- [Lessons Learned](#lessons-learned)
- [Summary](#summary)

---

## Purpose

This document describes the optimization strategies applied to the Football Virtual Waiting Room, and identifies future improvements that could push scalability further, reduce latency, or lower operational cost beyond what's already covered in [`13-cost-estimation.md`](13-cost-estimation.md).

The focus is primarily DynamoDB, since that's where most of the cost and latency lives — but API Gateway, Lambda, and the overall architecture are covered too.

---

## Optimization Goals

- Single-digit millisecond database latency where practical
- High throughput
- Low operational cost
- Horizontal scalability
- Efficient resource utilization
- Fault tolerance

---

## DynamoDB Optimizations

### Single Table Design

Keeping every entity in one table minimizes the number of round trips a single request needs and avoids joins entirely.

**Benefits:** lower latency, reduced complexity, better scalability. Full reasoning: [`04-data-model.md`](04-data-model.md).

### Access Pattern Driven Design

Every attribute and index exists because a specific query in [`03-access-patterns.md`](03-access-patterns.md) needs it — nothing was added speculatively.

**Benefits:** no table scans, predictable performance, lower read costs.

### Query Instead of Scan

Every data retrieval operation uses `GetItem` or `Query`. Table scans are avoided deliberately, not just by convention.

### Conditional Writes

Conditional expressions prevent duplicate queue registrations, race conditions, and lost updates:

```
attribute_not_exists(PK)
```

### Time To Live (TTL)

TTL automatically removes expired sessions and admission tokens.

**Benefits:** lower storage cost, no cleanup jobs, simpler maintenance. Full reasoning: [`04-data-model.md#time-to-live-ttl`](04-data-model.md#time-to-live-ttl).

### Sparse Global Secondary Indexes

Only item types that actually need an alternate access pattern populate an index — GSI2, for example, contains only `TOKEN` items.

**Benefits:** smaller indexes, faster queries, reduced write amplification. Full reasoning: [`06-index-design.md#sparse-indexes`](06-index-design.md#sparse-indexes).

### Projection Optimization

Each GSI projects only the attributes its access pattern actually needs.

**Benefits:** lower storage, reduced write cost.

### Immutable Queue Positions

Queue positions are assigned once and never rewritten — only the `status` field changes as a user moves through the queue.

**Benefits:** fewer writes, simpler logic, better consistency. Full reasoning: [`04-data-model.md#queue-position-strategy`](04-data-model.md#queue-position-strategy).

---

## Lambda Optimizations

- Reuse DynamoDB clients across invocations instead of recreating them per request
- Minimize cold start impact
- Keep every function single-purpose, per [`00-project-status.md#lambda-responsibilities`](00-project-status.md#lambda-responsibilities)
- Use structured logging throughout
- Handle retries gracefully rather than failing hard on transient errors

---

## API Gateway Optimizations

- Request validation at the gateway, before Lambda is even invoked
- Usage plans
- Throttling
- Caching, where the access pattern tolerates it

These controls improve reliability and shield the backend from traffic it doesn't need to see directly.

---

## CloudWatch Optimization

Monitored continuously: Lambda duration, error rates, API latency, DynamoDB throttling, and admission throughput — with alarms configured for abnormal behavior rather than relying on manual review. See the monitoring targets in [`07-system-architecture.md#monitoring`](07-system-architecture.md#monitoring).

---

## Cost Optimization

- DynamoDB On-Demand billing
- Automatic TTL cleanup
- Minimal GSIs
- Efficient attribute projection
- Stateless Lambda functions

Full breakdown: [`13-cost-estimation.md`](13-cost-estimation.md).

---

## Scalability Considerations

### Current Design

Already supports high concurrent reads, high concurrent writes, multiple simultaneous events, and automatic scaling — without any additional work.

### Future Enhancements

**Write sharding:** distribute queue entries across multiple logical shards to reduce hot partitions during extreme registration bursts. The key structure already supports this as an additive change — see [`05-table-schema.md#future-scalability`](05-table-schema.md#future-scalability) and [`04-data-model.md#sharding-strategy`](04-data-model.md#sharding-strategy).

**Push-based updates:** replace frequent polling with API Gateway WebSocket APIs or Server-Sent Events. Fewer reads, lower latency, better user experience — this is the single change most likely to move the needle, since queue-status polling is the dominant traffic source identified in [`03-access-patterns.md#expected-request-distribution`](03-access-patterns.md#expected-request-distribution).

**Global Tables:** replicate data across AWS regions for disaster recovery and lower latency for geographically distributed users.

**Distributed admission workers:** multiple workers processing independent queue partitions in parallel, while still preserving fairness.

**Caching:** introduce Amazon ElastiCache (Redis) only if repeated low-latency reads actually become a bottleneck — not preemptively.

---

## Security Optimizations

- IAM least privilege
- Encryption at rest
- Encryption in transit
- Token expiration strictly enforced
- Input validation
- Rate limiting

---

## Operational Best Practices

- Infrastructure as Code
- Automated deployments
- Automated testing
- CloudWatch dashboards
- Structured logging
- Version control

---

## Lessons Learned

- Design around access patterns, not entities — the whole schema in [`04-data-model.md`](04-data-model.md) and [`05-table-schema.md`](05-table-schema.md) exists because of this one decision made early, in [`02-requirements-analysis.md`](02-requirements-analysis.md).
- Minimize indexes — every GSI has a real cost, so each one needs a real justification.
- Avoid table scans, without exception.
- Prefer immutable data where possible — the immutable queue position is the clearest example of how much this simplifies everything downstream.
- Build for observability from day one, not as an afterthought once something breaks.

---

## Summary

These optimizations keep the Football Virtual Waiting Room scalable, maintainable, and cost-effective, while staying aligned with the AWS Well-Architected Framework and DynamoDB best practices throughout.

Next: [`15-final-solution.md`](15-final-solution.md) pulls everything together into the executive-level summary of the finished solution.