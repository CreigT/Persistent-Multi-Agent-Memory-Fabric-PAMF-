"""In-process CloudEvent log for memory.* subjects. NATS comes later."""

from __future__ import annotations

import time
import uuid
from typing import Any

log: list[dict[str, Any]] = []


def emit(type_: str, source: str, subject: str | None, data: dict[str, Any]) -> dict[str, Any]:
    evt = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "specversion": "1.0",
        "type": type_,
        "source": source,
        "subject": subject,
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": data,
    }
    log.append(evt)
    return evt
