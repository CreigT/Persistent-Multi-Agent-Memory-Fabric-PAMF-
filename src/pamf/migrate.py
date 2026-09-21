"""Apply SQL files. Safe to run on every boot."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "sql"


def migrate(dsn: str | None = None) -> None:
    dsn = dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL required for migrate")
    files = sorted(SQL_DIR.glob("*.sql"))
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for path in files:
                cur.execute(path.read_text())
        conn.commit()
