# System Architecture

Author: Muhammad Affan bin Aamir

Version: 1.0

---

# Purpose

This document describes the overall architecture of the Football Virtual Waiting Room.

The solution follows a **serverless, event-driven architecture** built on AWS managed services. The design prioritizes scalability, high availability, operational simplicity, and cost efficiency while showcasing Amazon DynamoDB as the core data store.

---

# High-Level Architecture

```
                        +----------------------+
                        |      Web / Mobile    |
                        |       Client App     |
                        +----------+-----------+
                                   |
                                   |
                          HTTPS REST API
                                   |
                                   ▼
                      +-----------------------+
                      |     Amazon API Gateway|
                      +-----------+-----------+
                                  |
                +-----------------+-----------------+
                |                 |                 |
                ▼                 ▼                 ▼
        Join Queue         Check Status      Validate Token
          Lambda              Lambda             Lambda
                |                 |                 |
                +--------+--------+-----------------+
                         |
                         ▼
                 +------------------+
                 | Amazon DynamoDB  |
                 | FootballWaiting  |
                 | Room Table       |
                 +--------+---------+
                          |
          +---------------+----------------+
          |                                |
          ▼                                ▼
 DynamoDB Streams                 CloudWatch Logs
          |                                |
          ▼                                ▼
 Event Processing                  Monitoring & Alerts
          |
          ▼
 EventBridge (Optional)
```

---

# AWS Services

| Service | Purpose |
|----------|---------|
| Amazon API Gateway | Public REST API |
| AWS Lambda | Business logic |
| Amazon DynamoDB | Persistent storage |
| DynamoDB Streams | Event notifications |
| Amazon CloudWatch | Logs and metrics |
| Amazon EventBridge | Event routing (optional) |
| AWS IAM | Authentication and authorization |

---

# Architecture Principles

The solution is based on the following principles.

- Serverless
- Event-driven
- Stateless compute
- Managed infrastructure
- Horizontal scalability
- Pay-per-use pricing

---

# Component Details

## 1. Client Application

Users interact with the waiting room through a web or mobile application.

Typical operations include:

- Join queue
- Check queue status
- Refresh position
- Enter ticket purchasing flow

The client communicates exclusively with the REST API.

---

## 2. Amazon API Gateway

API Gateway serves as the single entry point.

Responsibilities:

- HTTPS termination
- Request routing
- Authentication
- Rate limiting
- Request validation
- CORS configuration

Endpoints include:

- POST /queue/join
- GET /queue/status
- POST /token/validate
- POST /queue/leave

---

## 3. AWS Lambda

Lambda functions contain the business logic.

Each function has a single responsibility.

### Join Queue Lambda

Responsibilities:

- Validate request
- Prevent duplicate registration
- Assign queue position
- Store queue record

---

### Queue Status Lambda

Responsibilities:

- Retrieve queue information
- Calculate estimated wait
- Return current status

---

### Token Validation Lambda

Responsibilities:

- Verify token exists
- Check expiration
- Return authorization decision

---

### Queue Admission Lambda

Responsibilities:

- Select next users
- Update queue status
- Generate admission tokens

This function may be invoked on a schedule (for example, every few seconds) or by an operational trigger.

---

## 4. Amazon DynamoDB

DynamoDB is the primary data store.

Responsibilities:

- Store all entities
- Maintain queue state
- Persist admission tokens
- Store event metadata
- Track statistics

Features enabled:

- Single Table Design
- On-Demand Capacity
- TTL
- Streams
- Point-in-Time Recovery
- Server-Side Encryption

---

## 5. DynamoDB Streams

Streams capture changes made to the table.

Possible uses:

- Audit logging
- Metrics updates
- Notifications
- Future integrations

Although optional for the challenge, enabling Streams demonstrates readiness for event-driven extensions.

---

## 6. Amazon EventBridge (Optional)

EventBridge can consume events from downstream processes.

Example events:

- User admitted
- Queue closed
- Event started
- Token expired

This decouples future consumers from the core application.

---

## 7. Amazon CloudWatch

CloudWatch provides:

- Logs
- Metrics
- Dashboards
- Alarms

Key metrics include:

- API latency
- Lambda duration
- DynamoDB throttling
- Error rate
- Queue admission rate

---

## 8. AWS IAM

IAM secures communication between services.

Examples:

- Lambda execution roles
- DynamoDB access policies
- CloudWatch permissions
- API authorization

Least privilege should be applied.

---

# Request Flow

## Join Queue

```
Client
   │
   ▼
API Gateway
   │
   ▼
Join Queue Lambda
   │
   ▼
DynamoDB
   │
   ▼
Success Response
```

---

## Check Queue Status

```
Client
   │
   ▼
API Gateway
   │
   ▼
Queue Status Lambda
   │
   ▼
DynamoDB Query
   │
   ▼
Return Queue Information
```

---

## Validate Admission Token

```
Client
   │
   ▼
API Gateway
   │
   ▼
Validation Lambda
   │
   ▼
DynamoDB Lookup
   │
   ▼
Allow / Deny
```

---

# Queue Lifecycle

```
User Registers
      │
      ▼
Waiting
      │
      ▼
Admission Scheduler
      │
      ▼
Admitted
      │
      ▼
Token Created
      │
      ▼
Ticket Purchase
      │
      ▼
Completed
```

Alternative paths:

```
Waiting
   │
   ▼
Expired

or

Waiting
   │
   ▼
Cancelled
```

---

# Scalability

The architecture scales automatically.

## API Gateway

Scales without manual intervention.

---

## AWS Lambda

Automatically scales based on incoming requests.

---

## DynamoDB

Configured in On-Demand mode to automatically adapt to changing workloads.

---

# High Availability

AWS managed services provide:

- Multi-AZ resilience
- Automatic failover
- Durable storage
- Managed infrastructure

No application-managed servers are required.

---

# Security

Security considerations include:

- HTTPS-only communication
- IAM least privilege
- Encryption at rest
- Encryption in transit
- Input validation
- Request authentication
- Token expiration

---

# Monitoring

Recommended CloudWatch alarms:

| Metric | Threshold |
|----------|-----------|
| Lambda Errors | > 1% |
| API 5XX Responses | > 0 |
| DynamoDB Throttled Requests | > 0 |
| High Latency | > 500 ms |
| Admission Failures | > 0 |

---

# Failure Handling

The application should gracefully handle:

- Duplicate registrations
- Invalid tokens
- Expired sessions
- Event not found
- Capacity exhaustion

Failures return meaningful HTTP status codes and do not expose internal implementation details.

---

# Cost Optimization

The architecture minimizes cost by:

- Using serverless services
- Leveraging DynamoDB On-Demand capacity
- Automatically deleting expired items with TTL
- Avoiding idle compute resources
- Using minimal Global Secondary Indexes

---

# Future Enhancements

The architecture can evolve to support:

- Multi-region deployments
- Global tables
- WebSocket notifications
- Priority (VIP) queues
- Fraud detection
- Analytics pipelines
- Real-time dashboards

---

# Summary

The proposed architecture is fully serverless, horizontally scalable, and optimized around DynamoDB.

It demonstrates:

- Cloud-native design
- Event-driven processing
- High availability
- Operational simplicity
- Cost efficiency
- Production-ready engineering practices

This architecture forms the foundation for implementing the APIs and infrastructure described in the remaining documents.