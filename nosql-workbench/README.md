# NoSQL Workbench Export

This folder contains the DynamoDB data model export for the Football Virtual Waiting Room challenge.

| File | Purpose |
|---|---|
| `football-waiting-room-data-model.json` | NoSQL Workbench JSON export with the table schema, GSI1-GSI3, no LSIs, and sample items |

The model mirrors `template.yaml`:

- Table: `FootballWaitingRoom`
- Primary key: `PK` + `SK`
- GSIs: `GSI1`, `GSI2`, `GSI3`
- LSIs: none, because the deployed table does not define any
- Key attribute catalog: declared once via `KeyAttributes` on the base table and on each GSI (NoSQL Workbench's native format — not a CloudFormation `AttributeDefinitions` block, which Workbench doesn't import). Every GSI key attribute (`GSI1PK`/`GSI1SK`, `GSI2PK`/`GSI2SK`, `GSI3PK`/`GSI3SK`) is also listed in the base table's `NonKeyAttributes`, which Workbench requires so it can resolve each index's keys against the table
- Workbench base-table non-key catalog: GSI key attributes above, plus the projected attributes carried on base items — `queuePosition`, `status`, `joinTime`, `estimatedWait`, `eventId`, `userId`, `entityType`, `tokenId`, `expiresAt`, and the remaining item-specific fields (`matchName`, `stadium`, `capacity`, `waitingUsers`, `ttl`, etc.)
- Sample data: 14 base table items (Event metadata, Event stats, 5 Queue entries across 2 events, 5 Token records, 1 user queue-registration pointer, 1 session record), with 5 items carrying the key attributes for each of GSI1, GSI2, and GSI3
- GSI coverage is derived from full base table items, not separate index-only rows — every value stored is in DynamoDB typed attribute-value format (e.g. `{"S": "..."}`, `{"N": "..."}`), which is required for Workbench to import and render the model correctly
