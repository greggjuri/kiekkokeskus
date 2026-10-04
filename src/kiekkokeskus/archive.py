"""Raw archive and per-run manifest (ADR-006, ADR-020, ADR-022, ADR-023).

Keys live under `data/kiekkokeskus/raw/{runDateET}/` only (CLAUDE.md Rule 1).

PutObject signature here extends init-02's 4-arg form with an optional `content_encoding` so
raw gzipped objects can carry `Content-Encoding: gzip` without a second put API. All init-02
callers (health file) pass `content_encoding=None` and behave identically.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date, datetime

RAW_PREFIX_TMPL = "data/kiekkokeskus/raw/{run_date}/"
MANIFEST_SLUG = "_manifest.json"

# (key, body, content_type, cache_control, content_encoding | None)
PutObject = Callable[[str, bytes, str, str, str | None], None]


@dataclass
class ManifestRequest:
    slug: str
    url: str
    finalUrl: str
    status: int
    bytes: int
    sha256: str
    fetchedAt: str
    attempts: int
    error: str | None


@dataclass
class Manifest:
    runDateET: str
    dataDate: str
    season: str | None
    trigger: str
    startedAt: str
    version: str
    requests: list[ManifestRequest] = field(default_factory=list)
    finishedAt: str = ""
    schemaVersion: int = 1


def raw_key(run_date: date, slug: str) -> str:
    """Return the S3 key for a raw object. slug must be the final filename stem."""
    if not slug or "/" in slug or slug.startswith("_"):
        raise ValueError(f"invalid slug for raw archive: {slug!r}")
    return RAW_PREFIX_TMPL.format(run_date=run_date.isoformat()) + f"{slug}.json.gz"


def manifest_key(run_date: date) -> str:
    return RAW_PREFIX_TMPL.format(run_date=run_date.isoformat()) + MANIFEST_SLUG


def write_raw(*, put: PutObject, run_date: date, slug: str, body: bytes) -> tuple[str, str, int]:
    """Gzip-and-put a raw body. Returns (key, sha256_of_plain_body, len_plain_body)."""
    key = raw_key(run_date, slug)
    gz = gzip.compress(body)
    sha = hashlib.sha256(body).hexdigest()
    put(key, gz, "application/json", "public, max-age=31536000, immutable", "gzip")
    return key, sha, len(body)


def write_manifest(*, put: PutObject, run_date: date, manifest: Manifest, now_iso: str) -> str:
    """Serialize and put the manifest. Returns its key."""
    manifest.finishedAt = now_iso
    key = manifest_key(run_date)
    body = json.dumps(asdict(manifest), separators=(",", ":"), default=str).encode()
    put(key, body, "application/json", "public, max-age=300", None)
    return key


def make_request_row(
    *,
    slug: str,
    url: str,
    final_url: str,
    status: int,
    body: bytes | None,
    sha: str | None,
    fetched_at: str,
    attempts: int,
    error: str | None,
) -> ManifestRequest:
    return ManifestRequest(
        slug=slug,
        url=url,
        finalUrl=final_url,
        status=status,
        bytes=len(body) if body is not None else 0,
        sha256=sha or "",
        fetchedAt=fetched_at,
        attempts=attempts,
        error=error,
    )


def iso_z(now: datetime) -> str:
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")
