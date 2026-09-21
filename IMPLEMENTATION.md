# PAMF scaffold

Default store is in-memory (tests). Postgres is source of truth when `PAMF_STORE=postgres`.

```bash
docker compose up --build

pip install -r requirements.txt
PYTHONPATH=. uvicorn src.pamf.app:app --port 8080

PAMF_STORE=postgres DATABASE_URL=postgresql://pamf:pamf@127.0.0.1:5432/pamf \
  PYTHONPATH=. uvicorn src.pamf.app:app --port 8080
```

MCP: `python mcp/server.py`  
Helm: `helm template pamf helm/pamf`  
Freeze: `POST /v1/memory/admin/freeze` `{"frozen":true,"actor":"owner"}`

Sequence: see `SEQUENCE.md`
