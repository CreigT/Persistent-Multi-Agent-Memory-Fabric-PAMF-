"""PAMF MCP server — stdio JSON-RPC 2.0 subset for local agent wiring."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from urllib import request

API = "http://127.0.0.1:8080/v1"
MANIFEST = json.loads((Path(__file__).with_name("pamf.mcp.json")).read_text())


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    req = request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Idempotency-Key": body.get("idempotency_key", "mcp")},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _get(path: str) -> dict[str, Any]:
    with request.urlopen(f"{API}{path}", timeout=10) as resp:
        return json.loads(resp.read().decode())


def dispatch(name: str, args: dict[str, Any]) -> Any:
    if name == "memory_write":
        return _post("/memory/write", args)
    if name == "memory_search":
        return _post("/memory/query", args)
    if name == "memory_get_entity_timeline":
        t, i = args["entity_type"], args["entity_id"]
        return _get(f"/memory/entities/{t}/{i}")
    if name == "memory_supersede":
        mid = args.pop("memory_id")
        req = request.Request(
            f"{API}/memory/{mid}",
            data=json.dumps(args).encode(),
            headers={"Content-Type": "application/json"},
            method="PATCH",
        )
        with request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    if name == "memory_forget":
        mid = args["memory_id"]
        return _post(f"/memory/{mid}/forget", args)
    if name == "memory_explain_used":
        return {"decision_id": args["decision_id"], "memory_ids": []}
    raise ValueError(f"unknown tool {name}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        mid = msg.get("id")
        method = msg.get("method")
        try:
            if method == "initialize":
                result = {"protocolVersion": "2024-11-05", "serverInfo": {"name": "pamf-memory", "version": "0.1.0"}, "capabilities": {"tools": {}}}
            elif method == "tools/list":
                result = {"tools": MANIFEST["tools"]}
            elif method == "tools/call":
                params = msg.get("params") or {}
                data = dispatch(params["name"], params.get("arguments") or {})
                result = {"content": [{"type": "text", "text": json.dumps(data)}]}
            else:
                raise ValueError(f"unknown method {method}")
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}) + "\n")
        except Exception as exc:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "error": {"code": -32000, "message": str(exc)}}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
