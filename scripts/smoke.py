"""Post-deploy smoke tests (TESTING.md layer 6). stdlib only.

Exits non-zero on any failure. Also verifies the rest of the site is untouched
(CLAUDE.md Rule 1): / and /sports must still return 200.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import UTC, datetime

BASE = "https://jurigregg.com"
HEALTH_PATH = "/data/kiekkokeskus/_health.json"


def _get(url: str) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "kiekkokeskus-smoke/0.1"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()


def _check(name: str, cond: bool, detail: str = "") -> bool:
    marker = "PASS" if cond else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"{marker} {name}{suffix}")
    return cond


def main() -> int:
    ok = True

    try:
        status, _, _ = _get(f"{BASE}/")
        ok &= _check("GET /", status == 200, f"status={status}")
    except Exception as e:  # noqa: BLE001
        ok &= _check("GET /", False, repr(e))

    try:
        status, _, _ = _get(f"{BASE}/sports")
        ok &= _check("GET /sports", status == 200, f"status={status}")
    except Exception as e:  # noqa: BLE001
        ok &= _check("GET /sports", False, repr(e))

    try:
        status, headers, body = _get(f"{BASE}{HEALTH_PATH}")
        ok &= _check("GET health 200", status == 200, f"status={status}")
        cache = headers.get("cache-control", "")
        ok &= _check(
            "Cache-Control max-age=300", "max-age=300" in cache, f"cache-control={cache!r}"
        )
        payload = json.loads(body)
        ok &= _check(
            "status == 'ok'",
            payload.get("status") == "ok",
            f"status={payload.get('status')!r}",
        )
        ok &= _check("schemaVersion == 1", payload.get("schemaVersion") == 1)
        ok &= _check(
            "dataDate present",
            isinstance(payload.get("dataDate"), str) and len(payload["dataDate"]) == 10,
            f"dataDate={payload.get('dataDate')!r}",
        )
        ok &= _check(
            "rawCount > 0",
            isinstance(payload.get("rawCount"), int) and payload["rawCount"] > 0,
            f"rawCount={payload.get('rawCount')!r}",
        )
        gen = payload.get("generatedAt", "")
        try:
            gen_dt = datetime.strptime(gen, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            age_h = (datetime.now(UTC) - gen_dt).total_seconds() / 3600
            ok &= _check("generatedAt < 26h old", age_h < 26, f"age={age_h:.1f}h")
        except ValueError:
            ok &= _check("generatedAt parses", False, f"generatedAt={gen!r}")
    except Exception as e:  # noqa: BLE001
        ok &= _check("health endpoint", False, repr(e))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
