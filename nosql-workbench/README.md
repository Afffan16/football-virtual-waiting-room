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
- Sample data: at least five table items and five sample projected items for each GSI
