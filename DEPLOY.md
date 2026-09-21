# Deploy Day 1 Memory Agent

This is the autonomous multi-agent AI commerce platform, Day 1 only: PAMF.

## Production profile (required)

```
PAMF_STORE=postgres
DATABASE_URL=postgresql://USER:PASS@HOST:5432/pamf
```

Do not set `PAMF_STORE=memory` on a public URL. That profile is for unit tests. A restart would drop every packet.

## Run locally as production would run

```bash
docker compose up --build
```

Compose starts Postgres, applies `sql/*.sql`, and serves the API on port 8080 with `PAMF_STORE=postgres`.

Health: `GET /v1/memory/health`
If Postgres is down, health is not `ok`.

## Platform deploy

Any host that runs a container and a Postgres 16 database:

1. Provision Postgres. Create database `pamf`.
2. Set `DATABASE_URL` and `PAMF_STORE=postgres`.
3. Run the image. On boot the process applies `sql/001_init.sql` and `sql/002_events.sql`.
4. Confirm `GET /v1/memory/health` returns `"sql":"postgres"` and `"status":"ok"`.
5. Confirm a write survives `docker compose restart api`.

Image: `Dockerfile` in this repo. CI already builds it on push to `main`.

## What this deploy is

- Memory write, query, get, supersede, forget, timeline, freeze
- Decision citations stored in Postgres
- `memory.written` rows stored in Postgres `event_log`
- Secret-shaped writes rejected
- Restricted writes require `evidence_refs`

## What this deploy is not

- Not a payment system
- Not a storefront
- Not NATS / Kafka
- Not pgvector embeddings
- Not SPIFFE/mTLS (put TLS on the platform edge)
- Not transferred to Creignificent until a restore drill has been run on the target Postgres

## Owner freeze after deploy

```
POST /v1/memory/admin/freeze
{"frozen": true, "actor": "owner", "reason": "emergency"}
```
