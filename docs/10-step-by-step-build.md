# Step-by-Step Implementation Guide

Author: Muhammad Affan bin Aamir

Version: 1.0

---

# Purpose

This document provides a complete implementation guide for building the Football Virtual Waiting Room from scratch using AWS serverless services.

Following these steps should result in a fully functional implementation that matches the architecture and DynamoDB design documents.

---

# Step 1 — Install Prerequisites

Install the following software.

## Required

- Python 3.12
- Git
- AWS CLI v2
- AWS SAM CLI
- Docker Desktop
- Visual Studio Code

---

## Verify Installation

```bash
python --version
git --version
aws --version
sam --version
docker --version
```

---

# Step 2 — Configure AWS

Login to AWS.

Configure credentials.

```bash
aws configure
```

Provide:

```
AWS Access Key

AWS Secret Key

Region

Output Format
```

Verify.

```bash
aws sts get-caller-identity
```

---

# Step 3 — Create Project

Create repository.

```bash
mkdir football-waiting-room

cd football-waiting-room
```

Initialize Git.

```bash
git init
```

Create SAM project.

```bash
sam init
```

Choose:

```
Python 3.12

Zip Package

Hello World Template
```

---

# Step 4 — Create Project Structure

Create folders.

```
docs/

src/

tests/

events/

scripts/

diagrams/
```

Commit.

```bash
git add .

git commit -m "Initial project structure"
```

---

# Step 5 — Configure SAM Template

Edit

```
template.yaml
```

Define:

- DynamoDB Table
- Lambda Functions
- API Gateway
- IAM Roles
- Outputs

Validate.

```bash
sam validate
```

---

# Step 6 — Deploy Infrastructure

Build.

```bash
sam build
```

Deploy.

```bash
sam deploy --guided
```

Provide:

```
Stack Name

AWS Region

Confirm Changes

Capabilities
```

Verify deployment in CloudFormation.

---

# Step 7 — Configure DynamoDB

Confirm table creation.

Verify:

- TTL enabled
- Streams enabled
- PITR enabled
- Billing Mode = On-Demand

---

# Step 8 — Create Common Library

Inside

```
src/common/
```

Create:

```
constants.py

models.py

utils.py

dynamodb.py
```

These modules should contain:

- Shared constants
- DynamoDB helper functions
- Validation utilities
- Common response builders

---

# Step 9 — Implement Join Queue Lambda

Responsibilities

- Validate request
- Prevent duplicates
- Assign queue position
- Write queue item
- Update statistics

Test locally.

```bash
sam local invoke
```

---

# Step 10 — Implement Queue Status Lambda

Responsibilities

- Query GSI
- Return queue status
- Estimate wait time

Test.

---

# Step 11 — Implement Leave Queue Lambda

Responsibilities

- Update status
- Release session
- Update statistics

Test.

---

# Step 12 — Implement Token Validation Lambda

Responsibilities

- Lookup token
- Verify TTL
- Verify status
- Return authorization

Test.

---

# Step 13 — Implement Event Lookup Lambda

Responsibilities

- Return event metadata
- Return event status
- Validate event exists

Test.

---

# Step 14 — Implement Admission Service

Responsibilities

- Query waiting users
- Admit next batch
- Generate tokens
- Update queue entries
- Update statistics

This function may be invoked manually during development and scheduled in production.

---

# Step 15 — Configure API Gateway

Create routes.

```
POST /queue/join

GET /queue/status

POST /queue/leave

POST /queue/admit

POST /token/validate

GET /event/{id}

GET /event/{id}/stats
```

Enable:

- CORS
- Request validation
- Logging

---

# Step 16 — Local Testing

Run local API.

```bash
sam local start-api
```

Open.

```
http://127.0.0.1:3000
```

Test every endpoint using:

- Postman
- curl
- HTTPie

---

# Step 17 — Deploy to AWS

Build.

```bash
sam build
```

Deploy.

```bash
sam deploy
```

Verify:

- Stack
- Lambda
- API Gateway
- DynamoDB

---

# Step 18 — Functional Testing

Verify:

✓ Join queue

✓ Duplicate registration

✓ Queue status

✓ Leave queue

✓ Token validation

✓ Event lookup

✓ Statistics

---

# Step 19 — Verify TTL

Create temporary session.

Wait until expiration.

Confirm automatic deletion.

---

# Step 20 — Verify DynamoDB Streams

Modify queue item.

Confirm stream records appear.

Verify downstream processing if implemented.

---

# Step 21 — CloudWatch

Inspect:

- Lambda logs
- API logs
- Metrics
- Errors

Confirm no unexpected failures.

---

# Step 22 — Load Testing

Recommended tools.

- k6
- Artillery
- Locust

Measure:

- Throughput
- Latency
- Error Rate
- DynamoDB Performance

---

# Step 23 — Documentation

Complete:

- Architecture
- APIs
- Deployment Guide
- Testing Guide
- Lessons Learned

---

# Step 24 — Final Validation

Before submission confirm:

✓ Infrastructure deploys successfully

✓ APIs work

✓ No table scans

✓ GSIs function correctly

✓ TTL enabled

✓ Streams enabled

✓ Monitoring configured

✓ Documentation complete

---

# Recommended Development Order

```
Infrastructure

↓

Database

↓

Common Library

↓

Join Queue

↓

Queue Status

↓

Leave Queue

↓

Admission

↓

Token Validation

↓

Statistics

↓

Testing

↓

Optimization

↓

Documentation
```

---

# Recommended Git Commits

```
Initial project setup

Create infrastructure

Configure DynamoDB

Implement Join Queue

Implement Queue Status

Implement Leave Queue

Implement Token Validation

Implement Admission Service

Configure API Gateway

Add tests

Optimize DynamoDB

Complete documentation
```

---

# Final Checklist

| Task | Status |
|------|--------|
| Infrastructure deployed | □ |
| DynamoDB configured | □ |
| Lambda functions complete | □ |
| API Gateway configured | □ |
| IAM roles configured | □ |
| CloudWatch enabled | □ |
| TTL enabled | □ |
| Streams enabled | □ |
| Functional tests passed | □ |
| Load tests passed | □ |
| Documentation completed | □ |

---

# Outcome

At the completion of this guide, the project will provide:

- A serverless architecture
- A production-inspired DynamoDB data model
- RESTful APIs
- Infrastructure as Code
- Automated cleanup with TTL
- Monitoring and observability
- Comprehensive documentation

The solution will be ready for demonstration, further enhancement, or submission to the AWS Builder Center challenge.