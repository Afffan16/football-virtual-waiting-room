# Contributing to Football Virtual Waiting Room

First off, thanks for considering a contribution — whether that's a bug fix, a new Lambda, an extra test case, or a documentation tweak. This project started as an AWS Builder Center DynamoDB challenge submission, but it's structured to be extended, so real contributions are genuinely welcome.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Before You Start](#before-you-start)
- [Development Setup](#development-setup)
- [Project Layout](#project-layout)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Working with Infrastructure (AWS SAM)](#working-with-infrastructure-aws-sam)
- [Data Model Changes](#data-model-changes)
- [Commit & PR Guidelines](#commit--pr-guidelines)
- [Pull Request Checklist](#pull-request-checklist)
- [Reporting Bugs](#reporting-bugs)
- [Proposing Features](#proposing-features)
- [Questions](#questions)

---

## Code of Conduct

Be respectful, be constructive, assume good intent. Disagreements about design (especially DynamoDB modeling choices) are expected and welcome — keep them focused on the tradeoffs, not the person.

---

## Ways to Contribute

You don't need to write Lambda code to help. Useful contributions include:

| Type | Examples |
|---|---|
| 🐛 Bug fixes | Incorrect status codes, broken validation, edge cases in TTL handling |
| ✨ Features | New endpoints, WebSocket support, write sharding (see [Roadmap](README.md#-roadmap)) |
| 🧪 Tests | New unit/integration cases, load test scenarios, edge-case coverage |
| 📚 Docs | Clarifying the `docs/` design log, fixing broken links, improving examples |
| 🏗️ Infra | `template.yaml` improvements, CI pipeline enhancements |
| 🔍 Reviews | Reviewing open PRs, sanity-checking access-pattern claims against the data model |

---

## Before You Start

For anything beyond a small fix (typos, obvious bugs), **open an issue first** to discuss the approach — especially for anything that touches the DynamoDB table schema. This is a single-table design; a new access pattern can have ripple effects on partition keys, GSIs, and write costs, so it's worth aligning before you write code.

If you're picking up an existing issue, comment on it so we don't duplicate work.

---

## Development Setup

**Prerequisites:** Python 3.12+, [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html), Git.

```bash
# 1. Fork the repo, then clone your fork
git clone https://github.com/<your-username>/football-virtual-waiting-room.git
cd football-virtual-waiting-room

# 2. Create a feature branch
git checkout -b feature/short-description

# 3. Install app + dev dependencies (pytest, black, flake8, mypy, isort, moto, pre-commit)
pip install -r requirements-dev.txt
# or: make install

# 4. (Recommended) enable pre-commit hooks
pre-commit install

# 5. Build and run locally to confirm your environment works
sam build
sam local start-api
```

---

## Project Layout

```
src/
├── common/            # Shared across all Lambdas — edit with care, it's a blast radius
│   ├── constants.py    # App-wide constants
│   ├── dynamodb.py     # DynamoDB access helpers
│   ├── logger.py       # Structured JSON logging
│   ├── models.py       # Pydantic models
│   ├── responses.py    # Standard API response builders
│   └── utils.py        # Shared utilities
├── join_queue/        # One folder = one Lambda handler
├── queue_status/
├── leave_queue/
├── admit_users/
├── validate_token/
├── event_lookup/
└── statistics/

tests/
├── unit/               # Fast, isolated, no AWS calls (mocked via moto)
├── integration/        # One file per Lambda, exercises the full handler
├── api/                # Contract tests against docs/08-api-design.md
└── load/                # Concurrency / burst simulations
```

If you're adding a new capability, it's almost always either **a new function under `src/`** (one responsibility, mirrors an API endpoint) or **a change inside `src/common/`** — know which one you're touching before you start, since the latter affects every Lambda.

---

## Development Workflow

1. **Fork** the repository and clone your fork.
2. **Branch** off `main` with a descriptive name: `feature/websocket-updates`, `fix/ttl-race-condition`, `docs/clarify-gsi2`.
3. **Write the code**, keeping each Lambda focused on a single responsibility.
4. **Write tests** for the change — new behavior needs new coverage, not just a passing existing suite.
5. **Run formatting and linting tools** before committing (see below).
6. **Run the full test suite** and confirm it's green.
7. **Update relevant docs** — if you touch the schema, update `docs/05-table-schema.md`; if you touch an endpoint, update `docs/08-api-design.md`; if you add a new doc-worthy decision, it can go in `docs/`.
8. **Open a Pull Request** against `main` with a clear description of what changed and why.

---

## Coding Standards

- Follow **PEP 8**.
- Use **type hints** everywhere — this codebase relies on them for readability, not just for `mypy`.
- Add **docstrings** for public functions and Lambda handlers.
- Keep Lambda functions **stateless** and scoped to a single responsibility — resist the urge to have one handler do two things because it's convenient.
- Reuse `src/common/` rather than duplicating logic across Lambdas.
- Log using the shared `logger.py` (structured JSON), including request ID, event ID, and user ID where applicable — see `docs/08-api-design.md#observability`.
- No table scans, ever. If your change needs one, it's a sign the access pattern needs a new GSI — raise it as a design discussion first.

Run all formatting/linting via the `Makefile`:

```bash
make format    # black — auto-formats src/
make sort      # isort — sorts imports
make lint      # flake8 — style checks
```

(`mypy` can be run directly: `mypy src/`.)

---

## Testing

```bash
pytest                 # full suite
pytest --cov=src        # with coverage report
pytest tests/unit        # just unit tests
pytest tests/integration -k join_queue   # a specific integration test
```

or via `make test` / `make coverage`.

**Guidelines:**

- Unit tests should not make real AWS calls — use `moto` to mock DynamoDB.
- Integration tests exercise the full handler path (`tests/integration/test_<lambda>.py`) and should cover both success and the documented error cases (see the test-case tables in `docs/11-testing-plan.md`).
- If you add a new endpoint, add a matching case to `tests/api/` reflecting its contract.
- If your change affects performance-sensitive paths (queue join, token validation), consider whether `tests/load/` needs an updated scenario.
- All tests must pass locally **and** in CI (`.github/workflows/ci.yml`, which also runs `sam validate`) before a PR is merged.

---

## Working with Infrastructure (AWS SAM)

- **All infrastructure changes go through `template.yaml`.** Do not modify AWS resources manually from the console, except for local, throwaway testing.
- Validate before pushing:

  ```bash
  make validate    # sam validate
  make build         # sam build
  ```

- If you change the table definition, GSIs, or TTL configuration, cross-check `docs/05-table-schema.md` and `docs/06-index-design.md` — the docs are meant to always match the deployed schema.
- Be deliberate about new GSIs. Per the project's design philosophy (`docs/06-index-design.md`), every index must map to a real access pattern — don't add one "just in case," since each one adds write and storage cost.

---

## Data Model Changes

This project's whole premise is a carefully justified single-table DynamoDB design, so schema changes get extra scrutiny. If your PR touches `PK`/`SK` conventions, adds an item type, or introduces a new GSI, please include in the PR description:

1. The **access pattern** this supports (that doesn't already exist).
2. Why it **can't** be served by an existing key or index.
3. The **write/read cost impact** (rough estimate is fine).
4. Any **TTL** or **consistency** implications.

This mirrors the reasoning already documented in `docs/03-access-patterns.md` through `docs/06-index-design.md` — new changes should extend that same document trail.

---

## Commit & PR Guidelines

- Keep commits focused and messages descriptive (`fix: prevent duplicate queue entry on retry` rather than `fix bug`).
- Keep PRs scoped to one concern — a schema change and an unrelated formatting sweep should be separate PRs.
- Reference the related issue in the PR description (`Closes #12`).
- Be ready to iterate on review feedback, especially around access-pattern justification.

### Pull Request Checklist

Before requesting review, confirm:

- [ ] `pytest` passes locally
- [ ] `make lint` and `make format` are clean
- [ ] `sam validate` passes (if `template.yaml` changed)
- [ ] New/changed behavior has test coverage
- [ ] Relevant `docs/*.md` files are updated
- [ ] No table scans introduced
- [ ] PR description explains **what** changed and **why**

---

## Reporting Bugs

Open an issue with:

- What you expected to happen vs. what happened
- Steps to reproduce (a `curl`/Postman request is ideal — see [`postman/`](postman/))
- Relevant logs (CloudWatch or `sam local` output)
- Whether it reproduces locally (`sam local start-api`) or only in a deployed stack

## Proposing Features

Open an issue describing the use case before opening a PR. For anything touching the data model, sketch the access pattern the way `docs/03-access-patterns.md` does — it makes the design discussion much faster.

## Questions

Not sure if something's a bug, a design question, or a "yes, that's intentional"? Open an issue anyway and tag it as a question — that's what the `docs/` design log is for, and it's better to ask than to guess.

---

Thanks again for contributing — every PR, issue, and question helps this be a better reference for anyone learning DynamoDB single-table design.
