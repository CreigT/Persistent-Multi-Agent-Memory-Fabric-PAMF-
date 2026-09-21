# Build the commerce company — start here

Repository: `CreigT/Persistent-Multi-Agent-Memory-Fabric-PAMF-`

This repo **is** the autonomous multi-agent AI commerce platform.
Day 1 in this repo: **Memory Agent (PAMF)**. Later days add agents. They all use this fabric.

## Run Day 1

```bash
git clone https://github.com/CreigT/Persistent-Multi-Agent-Memory-Fabric-PAMF-.git
cd Persistent-Multi-Agent-Memory-Fabric-PAMF-
pip install -r requirements.txt
PYTHONPATH=. uvicorn src.pamf.app:app --port 8080
```

Postgres (SQL is truth):

```bash
docker compose up db -d
PAMF_STORE=postgres DATABASE_URL=postgresql://pamf:pamf@127.0.0.1:5432/pamf \
  PYTHONPATH=. uvicorn src.pamf.app:app --port 8080
```

Write a packet:

```bash
curl -s -X POST localhost:8080/v1/memory/write \
  -H 'Idempotency-Key: k1' -H 'Content-Type: application/json' \
  -d '{"actor_agent":"refund_agent","entity_type":"customer","entity_id":"cus_123","memory_type":"episodic","summary":"Refund approved under policy R-14","facts":[{"k":"refund_amount_usd","v":48.20}],"confidence":0.93,"evidence_refs":["ticket_8841"],"sensitivity":"restricted"}'
```

Freeze (owner):

```bash
curl -s -X POST localhost:8080/v1/memory/admin/freeze \
  -H 'Content-Type: application/json' \
  -d '{"frozen":true,"actor":"owner","reason":"emergency"}'
```

## What is built now

- Write / query / get / supersede / forget / timeline / freeze
- Secret-shaped payload rejected
- Restricted writes require evidence_refs
- Optional IdMA JWT (`PAMF_REQUIRE_AUTH=1`)
- Optional Postgres store
- memory.written event log
- decision_id citations (`GET /v1/memory/decisions/{id}`)
- OpenAPI, MCP tools, Helm, CI

## What is not built yet

- Nightly consolidation worker
- Live pgvector index
- NATS JetStream
- SPIFFE/mTLS mesh
- Products, payments, or customers

Spec: Day 1 module in README and https://github.com/CreigT/Persistent-Multi-Agent-Memory-Fabric-PAMF-/blob/8b9bb26/README.md
