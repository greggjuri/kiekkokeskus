from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from kiekkokeskus import __version__

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

PutObject = Callable[[str, bytes, str, str], None]


def _default_put() -> PutObject:
    import boto3

    client = boto3.client("s3")
    bucket = os.environ["BUCKET"]

    def put(key: str, body: bytes, content_type: str, cache_control: str) -> None:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
            CacheControl=cache_control,
        )

    return put


def _now_default() -> datetime:
    return datetime.now(UTC)


def handler(
    event: dict[str, Any],
    context: Any,
    *,
    put: PutObject | None = None,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Writes _health.json. forceError=True raises for alarm testing (ADR-032)."""
    log.info(json.dumps({"event": "invoked", "payload": event}))
    if event.get("forceError"):
        raise RuntimeError("forced error for alarm test")
    put = put or _default_put()
    now = now or _now_default
    prefix = os.environ["PREFIX"]
    key = f"{prefix}_health.json"
    trigger = "schedule" if event.get("source") == "scheduled" else "manual"
    payload = {
        "schemaVersion": 1,
        "generatedAt": now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ok",
        "version": __version__,
        "trigger": trigger,
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    put(key, body, "application/json", "public, max-age=300")
    log.info(json.dumps({"event": "health_written", "key": key, "trigger": trigger}))
    return {"status": "ok", "key": key}
