"""Capture a real NHL payload as a test fixture (TESTING.md Fixtures rule 1).

Usage:
    python scripts/fetch_fixture.py <url> [--slug SLUG] [--variant NAME] [--adr ADR]

Writes `tests/fixtures/{slug}__{captureDateET}[__{variant}].json.gz` and appends a provenance
row to `tests/fixtures/README.md`.

Date convention (PRP-03): the date in the filename is the ET date the fixture was captured,
computed here via `season.run_date_et`. The content's date (game, season, standings) lives in
the slug.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import sys
from datetime import UTC, datetime
from urllib.parse import urlparse

from kiekkokeskus import nhl, season

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
README = FIXTURES_DIR / "README.md"


def _default_slug(url: str) -> str:
    """Build a readable slug from the URL path when --slug isn't provided."""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p and p != "v1"]
    # Endpoint keeps internal dashes; "__" separates endpoint from each parameter (TESTING.md).
    if parts and parts[0] in {"schedule", "standings"} and len(parts) >= 2:
        return f"{parts[0]}__{parts[1]}"
    if parts[:1] == ["club-schedule-season"] and len(parts) >= 3:
        return f"club-schedule-season-{parts[1]}__{parts[2]}"
    if parts[:1] == ["club-stats"] and len(parts) >= 4:
        return f"club-stats-{parts[1]}__{parts[2]}__{parts[3]}"
    if parts[:1] == ["gamecenter"] and len(parts) >= 3:
        return f"boxscore__{parts[1]}"
    if "skater" in parts and "bios" in parts:
        return "skater-bios"
    if "goalie" in parts and "bios" in parts:
        return "goalie-bios"
    return "-".join(parts) or "fixture"


def _append_provenance_row(
    *, filename: str, url: str, fetched_at: str, status: int, variant_of: str, adr: str
) -> None:
    row = f"| {filename} | {url} | {fetched_at} | {status} | {variant_of or '-'} | {adr or '-'} |\n"
    text = README.read_text()
    if row in text:
        return  # idempotent
    README.write_text(text + row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture an NHL payload as a test fixture")
    parser.add_argument("url")
    parser.add_argument("--slug", help="override the derived slug")
    parser.add_argument("--variant", help="variant tag, e.g. 'unknown-state'")
    parser.add_argument("--adr", default="", help="ADR this fixture serves, e.g. 'ADR-013'")
    args = parser.parse_args()

    capture_date = season.run_date_et(datetime.now(UTC))
    fetched_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    slug = args.slug or _default_slug(args.url)
    variant_suffix = f"__{args.variant}" if args.variant else ""
    filename = f"{slug}__{capture_date.isoformat()}{variant_suffix}.json.gz"
    out_path = FIXTURES_DIR / filename

    result = nhl.fetch(args.url)
    body = result.body
    out_path.write_bytes(gzip.compress(body))
    sha = hashlib.sha256(body).hexdigest()[:16]

    rel = out_path.relative_to(REPO_ROOT)
    print(f"wrote {rel} ({len(body)} bytes, sha256={sha}, HTTP {result.status})")

    _append_provenance_row(
        filename=filename,
        url=args.url,
        fetched_at=fetched_at,
        status=result.status,
        variant_of=args.variant or "",
        adr=args.adr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
