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
- CloudFormation-compatible key catalog: `AttributeDefinitions` includes only `PK`, `SK`, and the GSI key attributes defined in `template.yaml`
- Workbench base-table non-key catalog: projected attributes such as `queuePosition`, `status`, `joinTime`, `estimatedWait`, `eventId`, `userId`, `entityType`, `tokenId`, and `expiresAt`
- Sample data: 15 full base table items, with at least five base items carrying the key attributes for each GSI
- GSI coverage is derived from full base table items, not separate index-only rows
