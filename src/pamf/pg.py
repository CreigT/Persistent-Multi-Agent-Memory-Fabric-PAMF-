"""Postgres MemoryStore. Same methods as the in-process store."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg
from fastapi import HTTPException
from psycopg.rows import dict_row

from src.pamf.app import MemoryWriteRequest, SECRET_RE, EntityRef


def _dsn() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://pamf:pamf@127.0.0.1:5432/pamf")


def _packet(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "memory_id": row["memory_id"],
        "type": row["memory_type"],
        "entities": row["entities"],
        "summary": row["summary"],
        "facts": row["facts"],
        "confidence": row["confidence"],
        "evidence_refs": row["evidence_refs"],
        "sensitivity": row["sensitivity"],
        "created_by": row["created_by"],
        "valid_from": row["valid_from"].isoformat() if hasattr(row["valid_from"], "isoformat") else row["valid_from"],
        "valid_to": row["valid_to"].isoformat() if row.get("valid_to") and hasattr(row["valid_to"], "isoformat") else row.get("valid_to"),
        "freshness": row["freshness"],
        "purpose": row.get("purpose"),
    }


class PostgresStore:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or _dsn()

    def _conn(self):
        return psycopg.connect(self.dsn, row_factory=dict_row)

    @property
    def frozen(self) -> bool:
        with self._conn() as c, c.cursor() as cur:
            cur.execute("SELECT v FROM memory_control WHERE k = 'frozen'")
            row = cur.fetchone()
            return bool(row and row["v"] == "true")

    @frozen.setter
    def frozen(self, value: bool) -> None:
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "INSERT INTO memory_control (k, v) VALUES ('frozen', %s) ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v, updated_at = now()",
                ("true" if value else "false",),
            )
            c.commit()

    @property
    def holds(self) -> set[str]:
        with self._conn() as c, c.cursor() as cur:
            cur.execute("SELECT memory_id FROM legal_holds")
            return {r["memory_id"] for r in cur.fetchall()}

    @property
    def rows(self) -> dict[str, dict[str, Any]]:
        with self._conn() as c, c.cursor() as cur:
            cur.execute("SELECT * FROM memories")
            return {r["memory_id"]: _packet(r) for r in cur.fetchall()}

    def write(self, body: MemoryWriteRequest, idem: str) -> dict[str, Any]:
        if self.frozen:
            raise HTTPException(423, "writes frozen")
        if SECRET_RE.search(body.summary) or any(SECRET_RE.search(str(f.v)) for f in body.facts):
            raise HTTPException(422, "secret-shaped payload rejected")
        if body.sensitivity == "restricted" and not body.evidence_refs:
            raise HTTPException(400, "restricted memories require evidence_refs")
        mid = "mem_" + hashlib.sha256(idem.encode()).hexdigest()[:16]
        entities = body.entities or (
            [EntityRef(type=body.entity_type, id=body.entity_id)] if body.entity_type and body.entity_id else []
        )
        now = datetime.now(timezone.utc)
        with self._conn() as c, c.cursor() as cur:
            cur.execute("SELECT * FROM memories WHERE idempotency_key = %s", (idem,))
            existing = cur.fetchone()
            if existing:
                return _packet(existing)
            cur.execute(
                """
                INSERT INTO memories (
                    memory_id, idempotency_key, memory_type, summary, facts, entities,
                    confidence, evidence_refs, sensitivity, purpose, created_by, valid_from
                ) VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s,%s,%s,%s)
                RETURNING *
                """,
                (
                    mid, idem, body.memory_type, body.summary,
                    json.dumps([f.model_dump() for f in body.facts]),
                    json.dumps([e.model_dump() for e in entities]),
                    body.confidence, json.dumps(body.evidence_refs),
                    body.sensitivity, body.purpose, body.actor_agent, now,
                ),
            )
            row = cur.fetchone()
            c.commit()
            return _packet(row)

    def get(self, memory_id: str) -> dict[str, Any] | None:
        with self._conn() as c, c.cursor() as cur:
            cur.execute("SELECT * FROM memories WHERE memory_id = %s", (memory_id,))
            row = cur.fetchone()
            return _packet(row) if row else None

    def close(self, memory_id: str) -> None:
        with self._conn() as c, c.cursor() as cur:
            cur.execute("UPDATE memories SET valid_to = now() WHERE memory_id = %s AND valid_to IS NULL", (memory_id,))
            c.commit()

    def forget(self, memory_id: str, policy_id: str | None) -> dict[str, Any]:
        if memory_id in self.holds:
            raise HTTPException(409, "legal hold")
        with self._conn() as c, c.cursor() as cur:
            cur.execute("SELECT 1 FROM memories WHERE memory_id = %s", (memory_id,))
            if not cur.fetchone():
                raise HTTPException(404, "not found")
            cert = f"fg_{uuid.uuid4().hex[:12]}"
            cur.execute("DELETE FROM memories WHERE memory_id = %s", (memory_id,))
            cur.execute(
                "INSERT INTO forget_certificates (certificate_id, memory_id, policy_id) VALUES (%s,%s,%s)",
                (cert, memory_id, policy_id),
            )
            c.commit()
        return {
            "certificate_id": cert,
            "memory_id": memory_id,
            "policy_id": policy_id,
            "forgotten_at": datetime.now(timezone.utc).isoformat(),
        }
