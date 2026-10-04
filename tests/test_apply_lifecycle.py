from __future__ import annotations

import copy

from apply_lifecycle import RULE, merge_rules


def test_empty_existing_yields_ours_only() -> None:
    out = merge_rules([], RULE)
    assert out == [RULE]


def test_unrelated_rule_preserved_byte_for_byte() -> None:
    unrelated = {
        "ID": "other-cleanup",
        "Status": "Enabled",
        "Filter": {"Prefix": "logs/"},
        "Expiration": {"Days": 30},
    }
    before = copy.deepcopy(unrelated)
    out = merge_rules([unrelated], RULE)
    assert out[0] == before, "existing rule mutated"
    assert out[-1] == RULE
    assert len(out) == 2


def test_legacy_top_level_prefix_rule_preserved() -> None:
    """Pre-2019 lifecycle rules used top-level `Prefix`, not `Filter.Prefix`."""
    legacy = {
        "ID": "legacy",
        "Prefix": "archive/",
        "Status": "Enabled",
        "Expiration": {"Days": 90},
    }
    out = merge_rules([legacy], RULE)
    assert legacy in out
    assert len(out) == 2


def test_rerun_is_idempotent() -> None:
    once = merge_rules([], RULE)
    twice = merge_rules(once, RULE)
    assert twice == once
    assert sum(1 for r in twice if r["ID"] == RULE["ID"]) == 1


def test_our_rule_replaces_on_rerun_with_changed_days() -> None:
    old = {**copy.deepcopy(RULE), "NoncurrentVersionExpiration": {"NoncurrentDays": 30}}
    out = merge_rules([old], RULE)
    assert len(out) == 1
    assert out[0]["NoncurrentVersionExpiration"]["NoncurrentDays"] == 7


def test_merge_does_not_mutate_inputs() -> None:
    existing = [{"ID": "x", "Status": "Enabled", "Filter": {"Prefix": "x/"}}]
    before = copy.deepcopy(existing)
    merge_rules(existing, RULE)
    assert existing == before
