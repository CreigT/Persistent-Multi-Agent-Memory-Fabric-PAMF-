"""PAMF Memory Agent. PAMF_STORE=memory for tests; postgres for deploy."""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.pamf.auth import ROUTE_SCOPES, current_agent
from src.pamf.events import emit, log as event_log

SECRET_RE = re.compile(r"(api[_-]?key|password|secret|bearer\s+[a-z0-9]|4[0-9]{12}(?:[0-9]{3})?)", re.I)
app = FastAPI(title="PAMF Memory Agent", version="0.1.0")
citations: dict[str, list[str]] = {}


class EntityRef(BaseModel):
    type: str
    id: str


class Fact(BaseModel):
    k: str
    v: Any


class MemoryWriteRequest(BaseModel):
    actor_agent: str
    entity_type: str | None = None
    entity_id: str | None = None
    entities: list[EntityRef] = Field(default_factory=list)
    memory_type: str
    summary: str
    facts: list[Fact] = Field(default_factory=list)
    confidence: float
    evidence_refs: list[str] = Field(default_factory=list)
    ttl_seconds: int | None = None
    sensitivity: str
    purpose: str | None = None


class MemoryQueryRequest(BaseModel):
    query: str
    purpose: str
    entity_type: str | None = None
    entity_id: str | None = None
    memory_types: list[str] | None = None
    k: int = 8
    decision_id: str | None = None


class FreezeRequest(BaseModel):
    frozen: bool
    actor: str
    reason: str | None = None


class MemoryStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self.rows: dict[str, dict[str, Any]] = {}
        self.frozen = False
        self.holds: set[str] = set()

    def write(self, body: MemoryWriteRequest, idem: str) -> dict[str, Any]:
        if self.frozen:
            raise HTTPException(423, "writes frozen")
        if SECRET_RE.search(body.summary) or any(SECRET_RE.search(str(f.v)) for f in body.facts):
            raise HTTPException(422, "secret-shaped payload rejected")
        if body.sensitivity == "restricted" and not body.evidence_refs:
            raise HTTPException(400, "restricted memories require evidence_refs")
        mid = "mem_" + hashlib.sha256(idem.encode()).hexdigest()[:16]
        now = datetime.now(timezone.utc).isoformat()
        entities = body.entities or (
            [EntityRef(type=body.entity_type, id=body.entity_id)] if body.entity_type and body.entity_id else []
        )
        packet = {
            "memory_id": mid,
            "type": body.memory_type,
            "entities": [e.model_dump() for e in entities],
            "summary": body.summary,
            "facts": [f.model_dump() for f in body.facts],
            "confidence": body.confidence,
            "evidence_refs": body.evidence_refs,
            "sensitivity": body.sensitivity,
            "created_by": body.actor_agent,
            "valid_from": now,
            "valid_to": None,
            "freshness": "fresh",
            "purpose": body.purpose,
        }
        with self._lock:
            if mid in self.rows and self.rows[mid]["summary"] == body.summary:
                return self.rows[mid]
            self.rows[mid] = packet
        return packet

    def get(self, memory_id: str) -> dict[str, Any] | None:
        return self.rows.get(memory_id)

    def close(self, memory_id: str) -> None:
        row = self.rows.get(memory_id)
        if row:
            row["valid_to"] = datetime.now(timezone.utc).isoformat()

    def forget(self, memory_id: str, policy_id: str | None) -> dict[str, Any]:
        if memory_id in self.holds:
            raise HTTPException(409, "legal hold")
        if memory_id not in self.rows:
            raise HTTPException(404, "not found")
        del self.rows[memory_id]
        return {
            "certificate_id": f"fg_{uuid.uuid4().hex[:12]}",
            "memory_id": memory_id,
            "policy_id": policy_id,
            "forgotten_at": datetime.now(timezone.utc).isoformat(),
        }

    def ping(self) -> bool:
        return True

    def emit_event(self, type_: str, source: str, subject: str | None, data: dict[str, Any]) -> dict[str, Any]:
        return emit(type_, source, subject, data)

    def cite(self, decision_id: str, memory_id: str) -> None:
        citations.setdefault(decision_id, [])
        if memory_id not in citations[decision_id]:
            citations[decision_id].append(memory_id)

    def listed_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return event_log[-limit:]

    def cited(self, decision_id: str) -> list[str]:
        return citations.get(decision_id, [])


def build_store():
    if os.environ.get("PAMF_STORE", "memory") == "postgres":
        from src.pamf.migrate import migrate
        from src.pamf.pg import PostgresStore

        migrate()
        return PostgresStore()
    return MemoryStore()


store = build_store()


@app.get("/v1/memory/health")
def health() -> Any:
    backend = "postgres" if os.environ.get("PAMF_STORE") == "postgres" else "in-memory"
    try:
        store.ping()
    except Exception as exc:
        return JSONResponse(
            {"status": "down", "frozen": False, "index_lag_ms": -1, "sql": backend, "error": str(exc)},
            status_code=503,
        )
    return {"status": "frozen" if store.frozen else "ok", "frozen": store.frozen, "index_lag_ms": 0, "sql": backend}


def _agent_write(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    return current_agent(authorization, ROUTE_SCOPES["write"])


def _agent_read(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    return current_agent(authorization, ROUTE_SCOPES["query"])


def _agent_forget(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    return current_agent(authorization, ROUTE_SCOPES["forget"])


def _agent_freeze(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    return current_agent(authorization, ROUTE_SCOPES["freeze"])


@app.post("/v1/memory/write", status_code=201)
def write(
    body: MemoryWriteRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    agent: dict[str, Any] | None = Depends(_agent_write),
) -> dict[str, Any]:
    if agent and not body.actor_agent:
        body.actor_agent = agent["agent_id"]
    packet = store.write(body, idempotency_key)
    store.emit_event("memory.written", body.actor_agent, packet["memory_id"], {"memory_id": packet["memory_id"], "type": packet["type"]})
    return packet


@app.post("/v1/memory/query")
def query(body: MemoryQueryRequest, agent: dict[str, Any] | None = Depends(_agent_read)) -> dict[str, Any]:
    q = body.query.lower()
    hits = []
    for row in store.rows.values():
        if row.get("valid_to"):
            continue
        if body.entity_type and body.entity_id:
            if not any(e["type"] == body.entity_type and e["id"] == body.entity_id for e in row["entities"]):
                continue
        blob = row["summary"].lower()
        if q in blob or not q:
            hits.append(row)
    hits.sort(key=lambda r: r["confidence"], reverse=True)
    packets = hits[: body.k]
    if body.decision_id:
        for p in packets:
            store.cite(body.decision_id, p["memory_id"])
    return {"packets": packets, "degraded": False}


@app.get("/v1/memory/{memory_id}")
def get_one(memory_id: str) -> dict[str, Any]:
    row = store.get(memory_id)
    if not row:
        raise HTTPException(404, "not found")
    return row


@app.patch("/v1/memory/{memory_id}")
def supersede(memory_id: str, body: MemoryWriteRequest) -> dict[str, Any]:
    row = store.get(memory_id)
    if not row:
        raise HTTPException(404, "not found")
    store.close(memory_id)
    return store.write(body, f"supersede:{memory_id}:{uuid.uuid4()}")


@app.post("/v1/memory/{memory_id}/forget")
def forget(
    memory_id: str,
    payload: dict[str, Any],
    agent: dict[str, Any] | None = Depends(_agent_forget),
) -> dict[str, Any]:
    return store.forget(memory_id, payload.get("policy_id"))


@app.get("/v1/memory/entities/{entity_type}/{entity_id}")
def timeline(entity_type: str, entity_id: str) -> dict[str, Any]:
    items = [
        r
        for r in store.rows.values()
        if any(e["type"] == entity_type and e["id"] == entity_id for e in r["entities"])
    ]
    items.sort(key=lambda r: r["valid_from"])
    return {"items": items}


@app.post("/v1/memory/export", status_code=202)
def export_mem() -> dict[str, str]:
    return {"status": "queued"}


@app.post("/v1/memory/admin/freeze")
def freeze(body: FreezeRequest, agent: dict[str, Any] | None = Depends(_agent_freeze)) -> dict[str, Any]:
    store.frozen = body.frozen
    return {"frozen": store.frozen, "at": datetime.now(timezone.utc).isoformat(), "actor": body.actor}


@app.get("/v1/memory/decisions/{decision_id}")
def explain_used(decision_id: str) -> dict[str, Any]:
    ids = store.cited(decision_id)
    return {"decision_id": decision_id, "memory_ids": ids, "packets": [store.get(i) for i in ids if store.get(i)]}


@app.get("/v1/memory/events")
def list_events(limit: int = 50) -> dict[str, Any]:
    return {"items": store.listed_events(limit)}


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse({"service": "pamf-memory", "project": "autonomous-multi-agent-ai-commerce", "day": 1, "docs": "/docs", "health": "/v1/memory/health"})
