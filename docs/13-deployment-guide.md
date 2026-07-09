# 🚀 Deployment Guide

**Author:** Muhammad Affan bin Aamir · **Version:** 2.0 · **Document:** `docs/13-deployment-guide.md`

← [Back: Testing Guide](12-testing-guide.md)

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Backend Deployment — AWS SAM](#backend-deployment--aws-sam)
- [Seeding the Database](#seeding-the-database)
- [Frontend Deployment](#frontend-deployment)
- [Deploying the Frontend Live (S3 + CloudFront)](#deploying-the-frontend-live-s3--cloudfront)
- [Post-Deployment Verification](#post-deployment-verification)
- [Environment Configuration](#environment-configuration)
- [Re-deploying After Changes](#re-deploying-after-changes)
- [Destroying the Stack](#destroying-the-stack)
- [Production Considerations](#production-considerations)
- [Troubleshooting](#troubleshooting)

---

## Overview

The backend deploys entirely via **AWS SAM** (one command). The frontend is static HTML/CSS/JS — it can be opened locally, served via S3 + CloudFront, or dropped behind any static hosting service (Amplify, Vercel, Netlify, Cloudflare Pages).

**Architecture after deployment:**

```
Browser → CloudFront (optional) → S3 (frontend)
Browser → API Gateway (HTTPS) → Lambda → DynamoDB
```

---

## Prerequisites

- **Python 3.12+** — `python --version`
- **AWS SAM CLI** — [install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- **AWS CLI** — [install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **AWS credentials** — `aws configure` (or an IAM role if running from CI)
- **Docker** — required for `sam build` with compiled dependencies

### IAM permissions your deploy user needs

```
cloudformation:*
lambda:*
apigateway:*
dynamodb:*
iam:PassRole
iam:CreateRole
iam:AttachRolePolicy
s3:*              (SAM uses an S3 bucket for artifacts)
```

---

## Backend Deployment — AWS SAM

### 1. Build

```bash
sam build
```

This compiles dependencies and stages the Lambda artifacts in `.aws-sam/build/`.

### 2. First-time guided deploy

```bash
sam deploy --guided
```

You'll be prompted for:

| Prompt | Value |
|---|---|
| Stack Name | `football-virtual-waiting-room` (or any name) |
| AWS Region | `us-east-1` (or your preferred region) |
| StageName | `Prod` |
| TokenTTLMinutes | `15` |
| SessionTTLMinutes | `30` |
| DefaultBatchSize | `50` |
| **AdminApiKey** | A strong random string — keep this secret |
| Confirm changeset | `y` |
| Allow SAM to create IAM roles | `y` |
| Save to samconfig.toml | `y` |

> 🔑 **AdminApiKey** is the secret that protects `POST /queue/admit`. Choose a strong value (e.g. `openssl rand -hex 32`). It will be stored as a Lambda environment variable — for production, consider storing it in AWS Secrets Manager and having the Lambda read it at runtime instead.

### 3. Subsequent deploys

After the first deployment, `samconfig.toml` stores your settings:

```bash
sam build && sam deploy
```

### 4. Get your API URL

After deployment, SAM prints the stack outputs:

```
Key                 WaitingRoomApiUrl
Value               https://<id>.execute-api.<region>.amazonaws.com/Prod/
```

Copy this URL — you'll need it for the frontend.

---

## Seeding the Database

The SAM deploy creates the DynamoDB table but leaves it empty. Seed it with the six football events used by the frontend:

```bash
# Seed event 1001 (single default event)
python scripts/seed_data.py

# Seed all 6 events + test data
python scripts/generate_test_data.py
```

Both scripts read `TABLE_NAME` from the environment. If the value isn't set, they default to `FootballWaitingRoom`. Set it if your stack uses a different name:

```bash
export TABLE_NAME=FootballWaitingRoom
python scripts/seed_data.py
```

---

## Frontend Deployment

### Option A — Open locally (no server needed)

```bash
start frontend/index.html      # Windows
open frontend/index.html       # macOS
```

Edit `frontend/app.js` and set `API_BASE` to your deployed API URL first.

### Option B — Local static server

```bash
python -m http.server 8080 --directory frontend
# Open http://localhost:8080
```

### Option C — AWS S3 + CloudFront (recommended for public access)

This is the recommended path for live deployment. It gives you HTTPS, a global CDN, and a real domain.

---

## Deploying the Frontend Live (S3 + CloudFront)

### Step 1 — Update the API URL in app.js

Open `frontend/app.js` and set `API_BASE` to your deployed API Gateway URL:

```js
const API_BASE = "https://<your-api-id>.execute-api.<region>.amazonaws.com/Prod";
const ADMIN_API_KEY = "your-admin-api-key-here"; // keep this private
```

> For a real production deployment, do **not** hardcode the admin key in the frontend source. Serve the frontend from a backend that injects it via a session cookie, or require admins to authenticate separately. The key in `app.js` is for local/demo use.

### Step 2 — Create an S3 bucket

```bash
aws s3 mb s3://football-waiting-room-frontend-<your-name> --region us-east-1
```

### Step 3 — Enable static website hosting

```bash
aws s3 website s3://football-waiting-room-frontend-<your-name> \
  --index-document index.html \
  --error-document index.html
```

### Step 4 — Upload the frontend

```bash
aws s3 sync frontend/ s3://football-waiting-room-frontend-<your-name> \
  --acl public-read \
  --cache-control "max-age=86400"
```

### Step 5 — Create a CloudFront distribution

In the AWS Console:
1. Go to **CloudFront → Create distribution**
2. **Origin domain** → your S3 bucket website endpoint (e.g. `football-waiting-room-frontend-yourname.s3-website-us-east-1.amazonaws.com`)
3. **Viewer protocol policy** → Redirect HTTP to HTTPS
4. **Default root object** → `index.html`
5. Create distribution — takes ~5 minutes to deploy

CloudFront gives you a URL like `https://dxxxxxx.cloudfront.net`. Point a custom domain there via Route 53 if needed.

### Step 6 — Update CORS in template.yaml (if needed)

If you restrict `AllowOrigin` from `*` to your CloudFront domain, update this in `template.yaml` and redeploy:

```yaml
Cors:
  AllowOrigin: "'https://dxxxxxx.cloudfront.net'"
```

---

## Post-Deployment Verification

After deploying, run these checks:

```bash
export API_URL="https://<your-api-id>.execute-api.<region>.amazonaws.com/Prod"
export ADMIN_KEY="your-admin-api-key"

# 1. Get event details
curl -s "$API_URL/event/1001" | python -m json.tool

# 2. Get stats
curl -s "$API_URL/event/1001/stats" | python -m json.tool

# 3. Join queue
curl -s -X POST "$API_URL/queue/join" \
  -H "Content-Type: application/json" \
  -d '{"eventId":"1001","userId":"DEPLOY-TEST-001"}' | python -m json.tool

# 4. Check status
curl -s "$API_URL/queue/status?eventId=1001&userId=DEPLOY-TEST-001" | python -m json.tool

# 5. Admit (admin)
curl -s -X POST "$API_URL/queue/admit" \
  -H "Content-Type: application/json" \
  -H "x-admin-api-key: $ADMIN_KEY" \
  -d '{"eventId":"1001","batchSize":1}' | python -m json.tool

# 6. Confirm admit is blocked without key
curl -s -X POST "$API_URL/queue/admit" \
  -H "Content-Type: application/json" \
  -d '{"eventId":"1001","batchSize":1}' | python -m json.tool
# Expected: 403 Forbidden
```

---

## Environment Configuration

All environment variables are managed via SAM parameters (`template.yaml`). Override them without editing the template:

```bash
sam deploy --parameter-overrides \
  StageName=Prod \
  TokenTTLMinutes=15 \
  DefaultBatchSize=50 \
  AdminApiKey="$(openssl rand -hex 32)"
```

| Variable | Default | Purpose |
|---|---|---|
| `TABLE_NAME` | `FootballWaitingRoomTable` (auto) | DynamoDB table name |
| `LOG_LEVEL` | `INFO` | Lambda log verbosity |
| `TOKEN_TTL_MINUTES` | `15` | Admission token lifetime |
| `SESSION_TTL_MINUTES` | `30` | Session lifetime |
| `DEFAULT_BATCH_SIZE` | `50` | Admit batch size when not specified |
| `ADMIN_API_KEY` | *(empty)* | Protects POST /queue/admit |

---

## Re-deploying After Changes

```bash
# Rebuild and deploy
sam build && sam deploy

# Deploy with updated parameters
sam build && sam deploy --parameter-overrides AdminApiKey="new-secret-here"
```

---

## Destroying the Stack

```bash
sam delete --stack-name football-virtual-waiting-room
```

> ⚠️ The DynamoDB table has `DeletionPolicy: Retain` — it will **not** be deleted with the stack. This is intentional to protect data. To delete the table too:
> ```bash
> aws dynamodb delete-table --table-name FootballWaitingRoom
> ```

---

## Production Considerations

These are beyond the scope of this demo but matter for a real production deployment:

### 1. Move the admin API key to Secrets Manager

Instead of passing `AdminApiKey` as a SAM parameter (which stores it in CloudFormation as a parameter value), store the key in **AWS Secrets Manager** and have the Lambda read it at cold-start:

```python
import boto3
secret = boto3.client("secretsmanager").get_secret_value(SecretId="football-admin-key")
_ADMIN_API_KEY = secret["SecretString"]
```

### 2. Replace `AllowOrigin: "*"` with your domain

```yaml
AllowOrigin: "'https://yourapp.com'"
```

### 3. Add a Lambda Authorizer or Cognito for user identity

The current system accepts any `userId` string. For production, tie `userId` to an authenticated identity (Cognito User Pool, OAuth JWT) and validate it in a Lambda Authorizer before requests reach the handlers.

### 4. Enable WAF on API Gateway

AWS WAF rules can block common exploits (SQL injection, XSS, bad bots) at the API Gateway level before they reach Lambda.

### 5. DynamoDB on-demand vs. provisioned

On-Demand is fine for a ticket drop (unpredictable burst). For a sustained high-throughput workload, provisioned capacity with Application Auto Scaling is more cost-efficient.

### 6. Set up CloudWatch alarms

```bash
# Lambda error rate > 1%
# API Gateway 5XX > 0
# DynamoDB throttled requests > 0
# Lambda duration p99 > 5000 ms
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `sam build` fails | Ensure Docker is running |
| `sam deploy` fails with permission error | Check your IAM user/role has CloudFormation + IAM permissions |
| API returns 500 | Check Lambda logs in CloudWatch: `aws logs tail /aws/lambda/JoinQueueFunction --follow` |
| DynamoDB table not found | Run `python scripts/seed_data.py` after first deploy |
| `POST /queue/admit` returns 403 | Check `x-admin-api-key` header matches the value you passed as `AdminApiKey` during deploy |
| `POST /queue/join` returns 403 | Event status is not `OPEN` — seed the event data |
| Frontend can't reach API | Check `API_BASE` in `frontend/app.js` matches your deployed URL |
| CORS errors in browser | Verify `AllowOrigin` in `template.yaml` includes your frontend's origin |

---

*For the full build walkthrough, see [`09-build-guide.md`](09-build-guide.md). For testing after deployment, see [`12-testing-guide.md`](12-testing-guide.md).*
