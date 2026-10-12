"""Deploy test: /bolts sync runs after /kiekkokeskus sync, carries the --exclude for test
files, and uses _subprocess_env() like the other subprocess calls (ADR-024, ADR-039)."""

from __future__ import annotations

import subprocess

import deploy
import pytest

# --- _bolts_sync_cmd shape ---


def test_bolts_sync_cmd_pins_every_argument():
    cmd = deploy._bolts_sync_cmd()
    assert cmd[0:3] == ["aws", "s3", "sync"]
    assert cmd[3] == "site/bolts/"
    assert cmd[4] == "s3://jurigregg-static-site/bolts/"
    assert "--delete" in cmd
    cc_idx = cmd.index("--cache-control")
    assert cmd[cc_idx + 1] == "public, max-age=300"
    prof_idx = cmd.index("--profile")
    assert cmd[prof_idx + 1] == "default"


def test_bolts_sync_cmd_excludes_test_files():
    # Explicitly guard the regression: without this exclude, site/bolts/view.test.js would
    # ship to prod alongside the real page assets.
    cmd = deploy._bolts_sync_cmd()
    assert "--exclude" in cmd, "missing --exclude flag"
    exclude_idx = cmd.index("--exclude")
    assert cmd[exclude_idx + 1] == "*.test.js", (
        "the first --exclude value must be '*.test.js' (prevents view.test.js deploying)"
    )


def test_bolts_sync_cmd_no_dev_or_package_json_excludes_needed():
    # bolts/ has no _dev/ dir and no package.json marker — those excludes belong to the shared
    # sync only. Keeping the bolts command minimal makes the dry-run upload count predictable.
    cmd = deploy._bolts_sync_cmd()
    excludes = [cmd[i + 1] for i, flag in enumerate(cmd) if flag == "--exclude"]
    assert excludes == ["*.test.js"], f"expected only *.test.js exclude, got {excludes}"


# --- page_sync order ---


def test_page_sync_runs_shared_first_then_bolts(monkeypatch, tmp_path):
    captured: list[dict] = []

    def fake_run(cmd, cwd=None, env=None, check=False):
        captured.append({"cmd": cmd, "cwd": cwd, "env": env, "check": check})
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(deploy.subprocess, "run", fake_run)
    monkeypatch.setattr(deploy, "NODE22_BIN", tmp_path)

    deploy.page_sync()

    # Post-init-08, page_sync fires 3 calls (shared → bolts → leijonat). This test still
    # pins the shared and bolts calls' order and shape; the full 3-call ordering is
    # covered in test_deploy_leijonat.py::test_page_sync_runs_three_calls_in_order.
    assert len(captured) >= 2
    assert captured[0]["cmd"] == deploy._shared_sync_cmd(), "first call must be the shared sync"
    assert captured[1]["cmd"] == deploy._bolts_sync_cmd(), "second call must be the bolts sync"

    # Shared + bolts both carry env=_subprocess_env() — AWS_PROFILE + Node 22 PATH prefix
    for call in captured[:2]:
        assert call["check"] is True
        assert call["cwd"] == deploy.REPO_ROOT
        env = call["env"]
        assert isinstance(env, dict)
        assert env.get("AWS_PROFILE") == "default"
        assert str(tmp_path) in env.get("PATH", "")


def test_page_sync_bolts_dest_check_allowed(monkeypatch, tmp_path):
    # Belt-and-suspenders: if a future rewrite points the bolts dest at a non-owned prefix,
    # _check_allowed must still intervene before subprocess fires.
    monkeypatch.setattr(deploy, "BOLTS_SYNC_DEST", "s3://jurigregg-static-site/other/")
    # Keep the shared sync happy (it runs first)
    monkeypatch.setattr(deploy, "NODE22_BIN", tmp_path)

    call_count = {"n": 0}

    def fake_run(cmd, cwd=None, env=None, check=False):
        call_count["n"] += 1
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(deploy.subprocess, "run", fake_run)

    with pytest.raises(SystemExit):
        deploy.page_sync()
    # Shared sync ran once; bolts sync was blocked by _check_allowed before firing
    assert call_count["n"] == 1


# --- _check_allowed still accepts bolts (it already did, but pin it) ---


def test_check_allowed_still_accepts_bolts_root():
    deploy._check_allowed("s3://jurigregg-static-site/bolts/")


def test_check_allowed_still_accepts_bolts_subpath():
    deploy._check_allowed("s3://jurigregg-static-site/bolts/hero.webp")
