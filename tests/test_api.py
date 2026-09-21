from fastapi.testclient import TestClient

from src.pamf.app import app, store

client = TestClient(app)


def setup_function() -> None:
    store.rows.clear()
    store.frozen = False
    store.holds.clear()


def test_health() -> None:
    r = client.get("/v1/memory/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_write_and_query() -> None:
    body = {
        "actor_agent": "refund_agent",
        "entity_type": "customer",
        "entity_id": "cus_123",
        "memory_type": "episodic",
        "summary": "Refund approved under policy R-14",
        "confidence": 0.93,
        "evidence_refs": ["ticket_8841"],
        "sensitivity": "restricted",
    }
    w = client.post("/v1/memory/write", json=body, headers={"Idempotency-Key": "k1"})
    assert w.status_code == 201
    mid = w.json()["memory_id"]
    q = client.post("/v1/memory/query", json={"query": "refund", "purpose": "support"})
    assert q.status_code == 200
    assert q.json()["packets"][0]["memory_id"] == mid


def test_reject_secret() -> None:
    r = client.post(
        "/v1/memory/write",
        json={
            "actor_agent": "x",
            "memory_type": "episodic",
            "summary": "password=hunter2 leaked",
            "confidence": 0.5,
            "sensitivity": "internal",
        },
        headers={"Idempotency-Key": "k2"},
    )
    assert r.status_code == 422


def test_cite_decision() -> None:
    body = {
        "actor_agent": "refund_agent",
        "memory_type": "episodic",
        "summary": "Refund approved under policy R-14",
        "confidence": 0.93,
        "evidence_refs": ["ticket_8841"],
        "sensitivity": "restricted",
        "entity_type": "customer",
        "entity_id": "cus_123",
    }
    client.post("/v1/memory/write", json=body, headers={"Idempotency-Key": "cite1"})
    q = client.post("/v1/memory/query", json={"query": "refund", "purpose": "support", "decision_id": "dec_1"})
    assert q.status_code == 200
    e = client.get("/v1/memory/decisions/dec_1")
    assert e.json()["memory_ids"]


def test_freeze() -> None:
    client.post("/v1/memory/admin/freeze", json={"frozen": True, "actor": "owner"})
    r = client.post(
        "/v1/memory/write",
        json={
            "actor_agent": "x",
            "memory_type": "working",
            "summary": "note",
            "confidence": 0.1,
            "sensitivity": "internal",
        },
        headers={"Idempotency-Key": "k3"},
    )
    assert r.status_code == 423
