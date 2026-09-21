# PAMF scaffold

Run API:

```bash
pip install -r requirements.txt
PYTHONPATH=. uvicorn src.pamf.app:app --port 8080
```

MCP stdio:

```bash
python mcp/server.py
```

Helm:

```bash
helm template pamf helm/pamf
```

OpenAPI: `openapi/openapi.yaml`  
MCP tools: `mcp/pamf.mcp.json`

Freeze writes: `POST /v1/memory/admin/freeze` `{"frozen":true,"actor":"owner"}`
