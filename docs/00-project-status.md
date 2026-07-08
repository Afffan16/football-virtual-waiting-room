# Football Virtual Waiting Room
## Project Status & Implementation Roadmap

Author: Muhammad Affan bin Aamir

Version: 1.0

---

# Project Overview

This repository contains the design and implementation of a **Football Virtual Waiting Room** built using AWS Serverless technologies as part of the AWS Builder Center DynamoDB Data Modeling Challenge.

The objective is to design a highly scalable, fair, and cost-efficient waiting room capable of handling extremely high traffic during football ticket releases.

The architecture follows an **access-pattern-driven DynamoDB Single Table Design** and uses fully managed AWS services.

---

# Current Status

## Phase

✅ Core Implementation Complete

All core Lambda functions, the common library, scripts, and the SAM template have been fully implemented.

---

# Repository Structure

```
Football-Virtual-Waiting-Room/

.github/
docs/
diagrams/
events/
infrastructure/
postman/
scripts/
src/
tests/

template.yaml
samconfig.toml
requirements.txt
requirements-dev.txt
README.md
Makefile
LICENSE
```

---

# Documentation Completed

The following design documents have been completed.

01 Challenge Details

02 Requirements Analysis

03 Access Patterns

04 Data Model

05 Table Schema

06 Index Design

07 System Architecture

08 API Design

09 Implementation Plan

10 Step-by-Step Build Guide

11 Testing Plan

12 Load Testing

13 Cost Estimation

14 Optimization

15 Final Solution

Repository documentation

README

CONTRIBUTING

Development setup

---

# Source Structure

```
src/

common/

join_queue/

queue_status/

leave_queue/

admit_users/

validate_token/

event_lookup/

statistics/
```

Each folder represents one Lambda function except **common**, which contains shared code.

---

# Common Module Responsibilities

constants.py

Application constants

dynamodb.py

Database helper functions

logger.py

Structured logging

models.py

Application models

responses.py

Standard API responses

utils.py

Shared utility functions

---

# Lambda Responsibilities

Join Queue

Registers users.

Queue Status

Returns queue information.

Leave Queue

Removes users.

Admit Users

Processes admissions.

Validate Token

Validates admission tokens.

Event Lookup

Returns event details.

Statistics

Returns analytics.

---

# Infrastructure

Infrastructure is managed using AWS SAM.

Primary AWS Services

Amazon DynamoDB

AWS Lambda

Amazon API Gateway

Amazon CloudWatch

AWS IAM

DynamoDB Streams

TTL

CloudFormation

---

# DynamoDB Design

Single Table Design

No table scans

Access-pattern driven

Conditional writes

TTL

GSIs

Immutable queue positions

---

# Development Principles

Follow AWS Well-Architected Framework

Infrastructure as Code

Single Responsibility Principle

Reusable common module

Serverless-first

Query-first database design

No premature optimization

Production-quality code

---

# Development Phases

Phase 1

Infrastructure

Tasks

Design template.yaml

Create DynamoDB table

Configure GSIs

Configure TTL

Enable Streams

Create IAM roles

Configure API Gateway

---

Phase 2

Shared Modules

Tasks

constants.py

logger.py

responses.py

models.py

utils.py

dynamodb.py

---

Phase 3

Lambda Development

Order

Join Queue

Queue Status

Leave Queue

Admit Users

Validate Token

Event Lookup

Statistics

---

Phase 4

Testing

Unit Tests

Integration Tests

API Tests

Load Tests

SAM Local

---

Phase 5

Deployment

Deploy using AWS SAM

Validate resources

Run end-to-end tests

Collect metrics

Capture screenshots

---

# Coding Standards

Python 3.12

Type hints

PEP 8

Structured logging

Minimal dependencies

Stateless Lambda functions

Shared reusable utilities

---

# Project Goals

Demonstrate:

DynamoDB data modeling

Serverless architecture

Scalable queue management

Production-ready API design

Infrastructure as Code

AWS best practices

---

# Success Criteria

The project is considered complete when:

All Lambda functions are implemented.

Infrastructure deploys successfully.

API Gateway is functional.

DynamoDB satisfies every access pattern.

Unit tests pass.

Integration tests pass.

Load testing is completed.

Documentation matches implementation.

The project is deployable using a single SAM command.

---

# Reference

This document serves as the master implementation reference.

If development is paused or resumed later, implementation should continue from the next incomplete phase without redesigning the architecture.