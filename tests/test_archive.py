from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, date, datetime

import pytest

from kiekkokeskus.archive import (
    Manifest,
    iso_z,
    make_request_row,
    manifest_key,
    raw_key,
    write_manifest,
    write_raw,
)


class FakePut:
    """Matches archive.PutObject: (key, body, ctype, cache, content_encoding | None)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes, str, str, str | None]] = []

    def __call__(
        self,
        key: str,
        body: bytes,
        ctype: str,
        cache: str,
        content_encoding: str | None,
    ) -> None:
        self.calls.append((key, body, ctype, cache, content_encoding))


RUN_DATE = date(2026, 10, 3)
FIXED_NOW = datetime(2026, 10, 3, 14, 0, 12, tzinfo=UTC)


def test_raw_key_scoped_to_prefix() -> None:
    assert (
        raw_key(RUN_DATE, "schedule-2026-10-02")
        == "data/kiekkokeskus/raw/2026-10-03/schedule-2026-10-02.json.gz"
    )


def test_raw_key_rejects_reserved_and_traversal() -> None:
    with pytest.raises(ValueError, match="invalid slug"):
        raw_key(RUN_DATE, "_manifest")
    with pytest.raises(ValueError, match="invalid slug"):
        raw_key(RUN_DATE, "../etc/passwd")
    with pytest.raises(ValueError, match="invalid slug"):
        raw_key(RUN_DATE, "")


def test_manifest_key() -> None:
    assert manifest_key(RUN_DATE) == "data/kiekkokeskus/raw/2026-10-03/_manifest.json"


def test_write_raw_gzips_and_sets_headers() -> None:
    put = FakePut()
    body = b'{"hello":"world"}'
    key, sha, nbytes = write_raw(put=put, run_date=RUN_DATE, slug="example", body=body)

    assert key == "data/kiekkokeskus/raw/2026-10-03/example.json.gz"
    assert sha == hashlib.sha256(body).hexdigest()
    assert nbytes == len(body)
    assert len(put.calls) == 1
    stored_key, stored_body, ctype, cache, enc = put.calls[0]
    assert stored_key == key
    assert gzip.decompress(stored_body) == body
    assert ctype == "application/json"
    assert cache == "public, max-age=31536000, immutable"
    assert enc == "gzip"


def test_write_manifest_body_and_headers() -> None:
    put = FakePut()
    m = Manifest(
        runDateET="2026-10-03",
        dataDate="2026-10-02",
        season="20262027",
        trigger="manual",
        startedAt=iso_z(FIXED_NOW),
        version="0.1.0",
        requests=[
            make_request_row(
                slug="schedule-2026-10-02",
                url="https://api-web.nhle.com/v1/schedule/2026-10-02",
                final_url="https://api-web.nhle.com/v1/schedule/2026-10-02",
                status=200,
                body=b'{"ok":1}',
                sha="abc",
                fetched_at="2026-10-03T14:00:00Z",
                attempts=1,
                error=None,
            )
        ],
    )
    write_manifest(put=put, run_date=RUN_DATE, manifest=m, now_iso=iso_z(FIXED_NOW))

    assert len(put.calls) == 1
    key, body, ctype, cache, enc = put.calls[0]
    assert key == "data/kiekkokeskus/raw/2026-10-03/_manifest.json"
    assert ctype == "application/json"
    assert cache == "public, max-age=300"
    assert enc is None

    doc = json.loads(body)
    assert doc["schemaVersion"] == 1
    assert doc["runDateET"] == "2026-10-03"
    assert doc["dataDate"] == "2026-10-02"
    assert doc["season"] == "20262027"
    assert doc["finishedAt"] == "2026-10-03T14:00:12Z"
    assert doc["requests"][0]["slug"] == "schedule-2026-10-02"
    assert doc["requests"][0]["error"] is None
    assert doc["requests"][0]["bytes"] == len(b'{"ok":1}')


def test_manifest_with_error_row_still_writes() -> None:
    """ADR-032/PRP-03: manifest is written even when a request errored."""
    put = FakePut()
    m = Manifest(
        runDateET="2026-10-03",
        dataDate="2026-10-02",
        season=None,
        trigger="manual",
        startedAt=iso_z(FIXED_NOW),
        version="0.1.0",
        requests=[
            make_request_row(
                slug="schedule-2026-10-02",
                url="https://api-web.nhle.com/v1/schedule/2026-10-02",
                final_url="",
                status=500,
                body=None,
                sha=None,
                fetched_at="2026-10-03T14:00:00Z",
                attempts=3,
                error="gave up after 3 attempts: HTTP 500",
            )
        ],
    )
    write_manifest(put=put, run_date=RUN_DATE, manifest=m, now_iso=iso_z(FIXED_NOW))
    doc = json.loads(put.calls[0][1])
    assert doc["season"] is None
    assert doc["requests"][0]["error"] == "gave up after 3 attempts: HTTP 500"
    assert doc["requests"][0]["bytes"] == 0


def test_manifest_dataclass_serializable() -> None:
    """asdict round-trip plus json dump stays stable."""
    m = Manifest(
        runDateET="2026-10-03",
        dataDate="2026-10-02",
        season="20262027",
        trigger="schedule",
        startedAt=iso_z(FIXED_NOW),
        version="0.1.0",
    )
    serialized = json.dumps(asdict(m), separators=(",", ":"), default=str)
    assert '"schemaVersion":1' in serialized
    assert '"season":"20262027"' in serialized
