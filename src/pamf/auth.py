"""Verify IdMA JWTs when PAMF_REQUIRE_AUTH=1."""

from __future__ import annotations

import os
from typing import Any

import jwt
from fastapi import Header, HTTPException

SECRET = os.environ.get("PAMF_JWT_SECRET") or os.environ.get("IDMA_JWT_SECRET") or "dev-secret"
ISSUER = os.environ.get("PAMF_JWT_ISS", "idma")
REQUIRED = os.environ.get("PAMF_REQUIRE_AUTH", "0") == "1"

ROUTE_SCOPES = {
    "write": "memory:write",
    "query": "memory:read",
    "get": "memory:read",
    "forget": "memory:forget",
    "freeze": "memory:freeze",
    "export": "memory:export",
}


def current_agent(
    authorization: str | None = Header(default=None),
    required_scope: str | None = None,
) -> dict[str, Any] | None:
    if not REQUIRED:
        return None
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "bearer required")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = jwt.decode(token, SECRET, algorithms=["HS256"], issuer=ISSUER)
    except jwt.PyJWTError as exc:
        raise HTTPException(401, f"invalid token: {exc}") from exc
    scopes = claims.get("scopes") or []
    if required_scope and required_scope not in scopes and "memory:*" not in scopes:
        raise HTTPException(403, f"missing scope {required_scope}")
    return {"agent_id": claims.get("sub"), "scopes": scopes, "jti": claims.get("jti")}
