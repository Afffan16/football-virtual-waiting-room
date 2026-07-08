# Football Virtual Waiting Room

A production-inspired serverless implementation of a Football Virtual Waiting Room built with AWS managed services.

This project was created as part of the AWS Builder Center DynamoDB Data Modeling Challenge and demonstrates how to design a highly scalable queue management system using Amazon DynamoDB.

---

# Features

- Serverless architecture
- Amazon DynamoDB Single Table Design
- REST API with Amazon API Gateway
- AWS Lambda business logic
- Admission token generation
- Automatic TTL cleanup
- Infrastructure as Code using AWS SAM
- Comprehensive documentation
- Automated testing strategy

---

# Architecture

```
Client

↓

API Gateway

↓

Lambda

↓

DynamoDB

↓

CloudWatch
```

---

# Technology Stack

## Cloud

- Amazon DynamoDB
- AWS Lambda
- Amazon API Gateway
- Amazon CloudWatch
- AWS IAM
- DynamoDB Streams

## Development

- Python
- AWS SAM
- CloudFormation
- Git
- pytest

---

# Repository Structure

```
football-waiting-room/

├── docs/
├── src/
├── tests/
├── diagrams/
├── events/
├── scripts/
├── template.yaml
└── README.md
```

---

# Documentation

| Document | Description |
|-----------|-------------|
| 01 | Challenge Details |
| 02 | Requirements Analysis |
| 03 | Access Patterns |
| 04 | Data Model |
| 05 | Table Schema |
| 06 | Index Design |
| 07 | System Architecture |
| 08 | API Design |
| 09 | Implementation Plan |
| 10 | Step-by-Step Guide |
| 11 | Testing Strategy |
| 12 | Load Testing |
| 13 | Cost Estimation |
| 14 | Optimization |
| 15 | Final Solution |

---

# Getting Started

Clone the repository.

```bash
git clone <repository-url>
```

Set up your local environment by copying the example configuration:

```bash
cp .env.example .env
```

Install the development dependencies (this includes the application dependencies):

```bash
pip install -r requirements-dev.txt
```

Build the application.

```bash
sam build
```

Deploy the infrastructure.

```bash
sam deploy --guided
```

Run locally.

```bash
sam local start-api
```

Run tests.

```bash
pytest
```

---

# Project Goals

The project demonstrates:

- DynamoDB data modeling
- Serverless application design
- Event-driven architecture
- Infrastructure as Code
- Cloud-native engineering
- AWS best practices

---

# Future Improvements

- WebSocket queue updates
- Multi-region deployment
- Global Tables
- Write sharding
- Redis integration
- CI/CD pipeline
- Real-time analytics

---

# License

This project is provided for educational and demonstration purposes.

---

# Author

**Muhammad Affan bin Aamir**

Junior Data Engineer

AWS Builder Community Member

GitHub: https://github.com/Afffan16