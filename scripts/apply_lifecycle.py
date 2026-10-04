"""Merge our noncurrent-expiry rule into the site bucket's lifecycle (ADR-023, ADR-027).

PutBucketLifecycleConfiguration replaces the whole rule set. This script preserves every
existing rule verbatim (including legacy top-level `Prefix` rules) and upserts ours by ID.

Default = dry run. Use --apply to write.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys

import boto3
from botocore.exceptions import ClientError

BUCKET = "jurigregg-static-site"
RULE: dict = {
    "ID": "kiekkokeskus-noncurrent-expiry",
    "Status": "Enabled",
    "Filter": {"Prefix": "data/kiekkokeskus/"},
    "NoncurrentVersionExpiration": {"NoncurrentDays": 7},
}


def merge_rules(existing: list[dict], ours: dict) -> list[dict]:
    """Upsert by ID; preserve every other rule verbatim (incl. legacy `Prefix`)."""
    out = [copy.deepcopy(r) for r in existing if r.get("ID") != ours["ID"]]
    out.append(copy.deepcopy(ours))
    return out


def _fetch_existing(client) -> list[dict]:
    try:
        resp = client.get_bucket_lifecycle_configuration(Bucket=BUCKET)
        return resp.get("Rules", [])
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "NoSuchLifecycleConfiguration":
            return []
        raise


def _print_diff(existing: list[dict], merged: list[dict]) -> None:
    existing_ids = {r.get("ID") for r in existing}
    merged_ids = {r.get("ID") for r in merged}
    added = merged_ids - existing_ids
    changed = {
        r["ID"]
        for r in merged
        if r.get("ID") in existing_ids
        and r != next((e for e in existing if e.get("ID") == r.get("ID")), None)
    }
    preserved = len(existing_ids - added - changed)
    print(f"diff: added={sorted(added)} changed={sorted(changed)} preserved={preserved}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge our lifecycle rule (ADR-023, ADR-027)")
    parser.add_argument(
        "--apply", action="store_true", help="write merged rules (default = dry run)"
    )
    args = parser.parse_args()

    session = boto3.Session(profile_name="default")
    client = session.client("s3")

    existing = _fetch_existing(client)
    merged = merge_rules(existing, RULE)

    print("=== current rules ===")
    print(json.dumps(existing, indent=2, default=str))
    print("=== merged rules ===")
    print(json.dumps(merged, indent=2, default=str))
    _print_diff(existing, merged)

    if not args.apply:
        print("dry run (use --apply to write)")
        return 0

    if existing == merged:
        print("no change; skipping put")
        return 0

    client.put_bucket_lifecycle_configuration(
        Bucket=BUCKET,
        LifecycleConfiguration={"Rules": merged},
    )
    print("applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
