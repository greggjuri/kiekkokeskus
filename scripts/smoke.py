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
BOLTS_PATH = "/data/kiekkokeskus/bolts.json"
LEIJONAT_PATH = "/data/kiekkokeskus/leijonat.json"
CSS_PATH = "/kiekkokeskus/kk.css"
JS_PATH = "/kiekkokeskus/i18n.js"

JS_CONTENT_TYPES = ("text/javascript", "application/javascript")


def _is_js_content_type(ct: str) -> bool:
    # Module scripts refuse anything but a JavaScript MIME type. Accept with or without a
    # charset suffix (ADR-039 Verify item 2).
    main = ct.split(";", 1)[0].strip().lower()
    return main in JS_CONTENT_TYPES


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

    health_data_date: str | None = None
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
        dd = payload.get("dataDate")
        health_data_date = dd if isinstance(dd, str) else None
        ok &= _check(
            "rawCount > 0",
            isinstance(payload.get("rawCount"), int) and payload["rawCount"] > 0,
            f"rawCount={payload.get('rawCount')!r}",
        )
        ok &= _check(
            'built includes "bolts"',
            "bolts" in (payload.get("built") or []),
            f"built={payload.get('built')!r}",
        )
        ok &= _check(
            'built includes "leijonat"',
            "leijonat" in (payload.get("built") or []),
            f"built={payload.get('built')!r}",
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

    bolts_data_date: str | None = None
    try:
        status, headers, body = _get(f"{BASE}{BOLTS_PATH}")
        ok &= _check("GET bolts 200", status == 200, f"status={status}")
        cache = headers.get("cache-control", "")
        ok &= _check(
            "bolts Cache-Control max-age=300",
            "max-age=300" in cache,
            f"cache-control={cache!r}",
        )
        payload = json.loads(body)
        ok &= _check(
            "bolts schemaVersion == 1",
            payload.get("schemaVersion") == 1,
            f"schemaVersion={payload.get('schemaVersion')!r}",
        )
        if health_data_date is not None:
            ok &= _check(
                "bolts.dataDate matches health",
                payload.get("dataDate") == health_data_date,
                f"bolts={payload.get('dataDate')!r} health={health_data_date!r}",
            )
        dd = payload.get("dataDate")
        bolts_data_date = dd if isinstance(dd, str) else None
        skaters = payload.get("skaters") or []
        ok &= _check(
            "bolts has >= 1 skater row",
            isinstance(skaters, list) and len(skaters) >= 1,
            f"len(skaters)={len(skaters)}",
        )
    except Exception as e:  # noqa: BLE001
        ok &= _check("bolts endpoint", False, repr(e))

    try:
        status, headers, body = _get(f"{BASE}{LEIJONAT_PATH}")
        ok &= _check("GET leijonat 200", status == 200, f"status={status}")
        cache = headers.get("cache-control", "")
        ok &= _check(
            "leijonat Cache-Control max-age=300",
            "max-age=300" in cache,
            f"cache-control={cache!r}",
        )
        payload = json.loads(body)
        ok &= _check(
            "leijonat schemaVersion == 1",
            payload.get("schemaVersion") == 1,
            f"schemaVersion={payload.get('schemaVersion')!r}",
        )
        if bolts_data_date is not None:
            # Fix 7: compare against bolts.json's dataDate, not the ops-only health file.
            ok &= _check(
                "leijonat.dataDate matches bolts",
                payload.get("dataDate") == bolts_data_date,
                f"leijonat={payload.get('dataDate')!r} bolts={bolts_data_date!r}",
            )
        skaters = payload.get("skaters") or []
        ok &= _check(
            "leijonat has >= 1 skater row",
            isinstance(skaters, list) and len(skaters) >= 1,
            f"len(skaters)={len(skaters)}",
        )
    except Exception as e:  # noqa: BLE001
        ok &= _check("leijonat endpoint", False, repr(e))

    # Shared assets (ADR-039). Confirms Cache-Control: public, max-age=300 and the right MIME.
    try:
        status, headers, _ = _get(f"{BASE}{CSS_PATH}")
        ok &= _check("GET kk.css 200", status == 200, f"status={status}")
        cache = headers.get("cache-control", "")
        ok &= _check(
            "kk.css Cache-Control max-age=300",
            "max-age=300" in cache,
            f"cache-control={cache!r}",
        )
        ctype = headers.get("content-type", "")
        ok &= _check(
            "kk.css content-type text/css",
            "text/css" in ctype.lower(),
            f"content-type={ctype!r}",
        )
    except Exception as e:  # noqa: BLE001
        ok &= _check("kk.css endpoint", False, repr(e))

    try:
        status, headers, _ = _get(f"{BASE}{JS_PATH}")
        ok &= _check("GET i18n.js 200", status == 200, f"status={status}")
        cache = headers.get("cache-control", "")
        ok &= _check(
            "i18n.js Cache-Control max-age=300",
            "max-age=300" in cache,
            f"cache-control={cache!r}",
        )
        ctype = headers.get("content-type", "")
        ok &= _check(
            "i18n.js is a JavaScript MIME type",
            _is_js_content_type(ctype),
            f"content-type={ctype!r}",
        )
    except Exception as e:  # noqa: BLE001
        ok &= _check("i18n.js endpoint", False, repr(e))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
