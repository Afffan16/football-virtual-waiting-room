# Final Solution Status

This is the active handoff checklist for the project. It records what has been completed, what changed in the latest session, what still needs verification, and the next actions to take.

## Current Direction

The backend is now moving from a fixed demo catalog toward a DynamoDB-backed event catalog with admin event creation, guarded active registrations, real admin queue visibility, and cleaner sold-out/closed registration behavior.

Admin authorization still uses the demo credentials:
- Email: `admin123@gmail.com`
- Password: `admin123`

The frontend sends these credentials as `x-admin-email` and `x-admin-password` for admin endpoints. The backend still supports `x-admin-api-key` as a later production path.

## Completed Before Latest Session

### 1. Load-Test and Hot-Path Improvements

- API Gateway stage and usage-plan throttle limits were raised for controlled ticket-drop testing.
- DynamoDB boto3 client uses adaptive retry behavior.
- Join queue no longer does the duplicate lookup on the normal successful path.
- Queue positions use timestamp + UUID strings for lexicographic fairness and tie-breaking.
- Queue rows now write to deterministic event shards (`EVENT#<id>#SHARD#nn`) instead of one `EVENT#<id>` hot partition.
- GSI3 admin/admission partitions are sharded the same way and merged by `queuePosition` for fair admission order.
- Stats use sharded counters to avoid a single hot STATS item.

### 2. Duplicate Registration Guard

- Join queue writes a per-user, per-event registration guard item.
- Guard item and queue item are written together with a transaction.
- Duplicate joins return the existing queue registration instead of creating another queue entry.
- Moto transaction compatibility was handled in the DynamoDB helper for local tests.

### 3. Real Admin Queue Visibility

- Added admin-protected `GET /queue/admin/list`.
- The endpoint queries GSI3 and returns real queue entries.
- Frontend admin table calls `/queue/admin/list`.
- Admin filters call the backend with the selected status.

### 4. Demo Login Flows

- Added user login and stable derived fan IDs.
- Added admin login with session state and logout.
- Frontend admin requests send the demo admin credential headers.
- Join, status, and leave actions use the session-derived fan ID.

## Latest Session Changes

### 1. Rejoin After Leave Fix

- `leave_queue` now removes the active registration guard when a user leaves.
- The cancelled queue row remains in DynamoDB for admin/audit visibility.
- The cancelled row is removed from the user lookup path so `GET /queue/status` correctly reports "not in queue".
- The same fan can now join the same event again after leaving.
- `join_queue` includes a compatibility cleanup for old cancelled/expired guard rows already in DynamoDB.

### 2. Registration Closed / Sold-Out Behavior

- Added queue status `REGISTRATION_CLOSED`.
- Added `closedUsers` stats support.
- Added `close_waiting_registrations()` helper in DynamoDB utilities.
- When purchasing capacity is full, remaining `WAITING` users can be moved to `REGISTRATION_CLOSED`.
- Closed rows stay visible in the admin queue table and are filterable.
- The event metadata can be marked `CLOSED` when registrations are closed.

### 3. DynamoDB-Backed Event Catalog

- Added new Lambda module `src/events/app.py` for `GET /events`.
- Added new Lambda module `src/admin_event/app.py` for admin-only `POST /event`.
- Updated `template.yaml` with:
  - `GET /events`
  - `POST /event`
  - Lambda outputs for the new functions
- Frontend now loads events from `/events`, with the old hardcoded catalog kept as fallback.

### 4. Admin Add Event UI

- Added an "Add Event" form to the admin dashboard.
- Admin can enter event ID, match name, stadium, capacity, start time, and status.
- Frontend calls `POST /event`, then refreshes the event catalog and selector.

### 5. Frontend Error Handling

- API helper now normalizes API Gateway proxy responses.
- Failed calls should now show a readable message instead of `[object Object]`.
- Updated admin admit/auto-fill and user leave error handling to use normalized messages.

### 6. Data Scripts

- Added `scripts/clear_event_records.py`.
- Default cleanup behavior keeps event metadata, deletes queue/session-like event records, deletes registration guards/tokens, and resets STATS rows.
- Added `--reopen-events` option to reset preserved events back to `OPEN`.
- Added `--delete-events` option if event metadata should be removed too.
- Updated `scripts/generate_test_data.py` to create registration guard rows along with queue rows.
- Updated seed/test stats fixtures to include `closedUsers`.

### 7. Test Alignment

- Updated leave queue tests for the new behavior: second leave is now `404` because no active registration remains.
- Added a regression test that a user can rejoin after leaving.

## Post-Deploy Incident Investigation

The deployed frontend showed:

```text
[22:15:05] Checking status for FAN-00NNB7VS in event 1001...
[22:13:52] Joining queue for event 1001 as FAN-00NNB7VS...
Ready. Selected event: Manchester United vs Liverpool (1001)
```

No success/error toast appeared, and the user did not enter the queue.

### What Was Checked

- Confirmed `template.yaml` still defines `WaitingRoomApi`.
- Confirmed the deployed stack still outputs the same API URL used by `frontend/app.js`:
  - `https://n20mxucrj4.execute-api.us-east-1.amazonaws.com/Prod/`
- Confirmed CloudWatch logs show `POST /queue/join` and `GET /queue/status` both reach their Lambda functions.
- Confirmed DynamoDB still has `EVENT#1001 / METADATA` with status `OPEN`.
- Confirmed DynamoDB still has `EVENT#1001 / STATS` reset to zero counters.
- Confirmed `USER#FAN-00NNB7VS / QUEUE#EVENT#1001` does not exist after the failed join.
- Confirmed there are no queue rows for event `1001` after the failed join.

So API Gateway was not removed. The route and Lambda integration exist.

### Root Backend Problem

`join_queue` now writes two items atomically:

- A user registration guard row.
- The actual event queue row.

That uses `dynamodb:TransactWriteItems`.

The deployed `JoinQueueFunction` IAM role had:

- `dynamodb:GetItem`: allowed
- `dynamodb:PutItem`: allowed
- `dynamodb:UpdateItem`: allowed
- `dynamodb:DeleteItem`: allowed
- `dynamodb:Query`: allowed
- `dynamodb:TransactWriteItems`: `implicitDeny`

The SAM `DynamoDBCrudPolicy` used in `template.yaml` does not grant `dynamodb:TransactWriteItems`. Because of that, every join transaction failed before writing queue records.

`AdminEventFunction` also uses `transact_put_items()` to create an event and stats row together, so it needed the same permission.

### Secondary Backend Problem

`src/common/dynamodb.py` treated every `TransactionCanceledException` as a duplicate/conditional conflict and returned `False`.

That hid the real IAM failure and made the API return a misleading `409 Queue registration already exists` for brand-new users.

### Frontend Problem

The frontend API helper now normalizes API Gateway proxy responses, but some callers still tried to run:

```javascript
JSON.parse(data.body)
```

After normalization, `data.body` can already be an object or may not exist. On error responses this could throw before `showToast()` or `detailLog()` ran, which is why the UI appeared to do nothing after "Joining..." or "Checking status...".

## Fixes Applied In This Session

### 1. SAM IAM Fix

Updated `template.yaml` to explicitly grant:

```yaml
dynamodb:TransactWriteItems
```

to:

- `JoinQueueFunction`
- `AdminEventFunction`

### 2. Transaction Error Handling Fix

Updated `src/common/dynamodb.py` so `transact_put_items()` only returns `False` for actual conditional-check cancellations.

Other transaction failures, including IAM/access problems, now raise and get logged as real backend errors instead of being converted into fake duplicate-registration conflicts.

### 3. Frontend Error Parsing Fix

Updated `frontend/app.js` with `unwrapApiBody()` and replaced remaining unsafe `JSON.parse(data.body)` call sites.

Failed join/status/leave/admin calls should now display a readable toast/log message instead of silently failing in the error handler.

### 4. Test Alignment Fix

Updated `tests/unit/test_constants.py` so `REGISTRATION_CLOSED` is included in the expected queue status set.

## Second Join Failure Investigation

After the IAM fix was deployed, `POST /queue/join` reached the Lambda but returned:

```text
Failed: Internal server error.
```

CloudWatch showed:

```text
TransactionCanceledException
CancellationReasons: [ValidationError, None]
Type mismatch for key PK expected: S actual: M
```

### Root Cause

`src/common/dynamodb.py` built transaction items with `TypeSerializer` output, then sent them through `_table.meta.client.transact_write_items()`.

In this resource-backed path, boto3 expected normal Python values for `Item`, not already-serialized DynamoDB attribute maps. The double serialization turned the key into a map-like value, so DynamoDB rejected the transaction before writing anything.

### Fix Applied

- Changed the transaction helper to build plain Python item values by default.
- Kept serialized transaction building only as a fallback for clients that require raw DynamoDB shapes.
- Verified the patched `join_queue` handler directly against the deployed table with a debug fan/event and received `201 Created`.
- Removed the debug guard/queue rows afterward and corrected the sharded stat increment.

## Verification Completed After The Fix

Passed:

```powershell
node --check frontend\app.js

python -m py_compile src\common\dynamodb.py src\join_queue\app.py src\admin_event\app.py

python -m pytest tests\unit\test_constants.py tests\integration\test_join_queue.py tests\integration\test_queue_status.py -q
# 31 passed

python -m pytest -q
# 134 passed
```

Also run:

```powershell
sam validate
sam build
```

Result:

- Template reported valid.
- SAM build completed successfully.
- SAM still printed local metadata permission warnings for `C:\Users\Dr.pc\AppData\Roaming\AWS SAM\metadata.json`; this is a local sandbox/SAM telemetry config issue, not a template validation failure.

## Still Left

### 1. Deploy Backend Fix

```powershell
sam deploy
```

After deploy, verify the JoinQueue role now allows transaction writes:

```powershell
aws iam simulate-principal-policy `
  --policy-source-arn <JoinQueueFunctionRoleArn> `
  --action-names dynamodb:TransactWriteItems `
  --resource-arns <FootballWaitingRoomTableArn>
```

Expected result: `allowed`.

### 2. Smoke Test Backend Join/Status

```powershell
curl -X POST https://n20mxucrj4.execute-api.us-east-1.amazonaws.com/Prod/queue/join `
  -H "Content-Type: application/json" `
  -d "{\"eventId\":\"1001\",\"userId\":\"FAN-SMOKE-001\"}"

curl "https://n20mxucrj4.execute-api.us-east-1.amazonaws.com/Prod/queue/status?eventId=1001&userId=FAN-SMOKE-001"
```

Expected:

- Join returns `201`.
- DynamoDB contains a `USER#FAN-SMOKE-001 / QUEUE#EVENT#1001` guard.
- DynamoDB contains an `EVENT#1001 / QUEUE#...` row.
- Status returns the queue entry.

### 3. Deploy Frontend Fix

```powershell
aws s3 sync frontend/ s3://<frontend-bucket-name>/ --delete --cache-control "no-cache, no-store, must-revalidate"
aws cloudfront create-invalidation --distribution-id E1MW2RPK9I9W6J --paths "/*"
```

Then hard-refresh the CloudFront URL and verify:

- Join shows success.
- Status button shows status or a readable "not in queue" message.
- Error cases show readable toasts/log messages.

### 4. Smoke Test New and Existing API Endpoints

Verify:
- `GET /events`
- `POST /event` with demo admin headers
- `POST /queue/join`
- `GET /queue/status`
- `POST /queue/leave`
- Rejoin after leave
- `POST /queue/admit` with demo admin headers
- Capacity full behavior closes remaining waiting registrations
- `GET /queue/admin/list?status=REGISTRATION_CLOSED`
- `GET /event/{eventId}/stats` includes `closedUsers`

### 5. Optional DynamoDB Cleanup

To reset queue records while keeping events:

```powershell
$env:TABLE_NAME='<deployed-table-name>'
python scripts\clear_event_records.py --reopen-events
```

The script prompts for `CLEAR`. To skip the prompt:

```powershell
python scripts\clear_event_records.py --table-name '<deployed-table-name>' --reopen-events --yes
```

### 6. Git Add Reminder

New files are currently untracked and must be included before commit:
- `scripts/clear_event_records.py`
- `src/events/`
- `src/admin_event/`

There is also an untracked `deploy.txt`; confirm whether it should be committed or ignored.

## Production Security Follow-Up

The demo admin credential flow is acceptable for this project stage only. Production should move to one of:
- Cognito or a Lambda Authorizer.
- Server-side admin session.
- Secrets Manager backed admin secret.
- API key or JWT not exposed directly in static frontend source.
