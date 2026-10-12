"""Deploy test: /leijonat sync runs after /bolts (which runs after shared), carries the
--exclude for test files, and uses _subprocess_env() like every other subprocess call
(ADR-024, ADR-039). Mirrors test_deploy_bolts.py."""

from __future__ import annotations

import subprocess

import deploy
import pytest

# --- _leijonat_sync_cmd shape ---


def test_leijonat_sync_cmd_pins_every_argument():
    cmd = deploy._leijonat_sync_cmd()
    assert cmd[0:3] == ["aws", "s3", "sync"]
    assert cmd[3] == "site/leijonat/"
    assert cmd[4] == "s3://jurigregg-static-site/leijonat/"
    assert "--delete" in cmd
    cc_idx = cmd.index("--cache-control")
    assert cmd[cc_idx + 1] == "public, max-age=300"
    prof_idx = cmd.index("--profile")
    assert cmd[prof_idx + 1] == "default"


def test_leijonat_sync_cmd_excludes_test_files():
    # Explicitly guard the regression: without this exclude, site/leijonat/view.test.js
    # would ship to prod alongside the real page assets.
    cmd = deploy._leijonat_sync_cmd()
    assert "--exclude" in cmd, "missing --exclude flag"
    exclude_idx = cmd.index("--exclude")
    assert cmd[exclude_idx + 1] == "*.test.js", (
        "the first --exclude value must be '*.test.js' (prevents view.test.js deploying)"
    )


def test_leijonat_sync_cmd_only_one_exclude():
    # Leijonat has no _dev/ dir and no package.json marker — keep the command minimal so the
    # dry-run upload count stays predictable (4 uploads: index.html, main.js, view.js,
    # hero.webp).
    cmd = deploy._leijonat_sync_cmd()
    excludes = [cmd[i + 1] for i, flag in enumerate(cmd) if flag == "--exclude"]
    assert excludes == ["*.test.js"], f"expected only *.test.js exclude, got {excludes}"


# --- page_sync order ---


def test_page_sync_runs_three_calls_in_order(monkeypatch, tmp_path):
    captured: list[dict] = []

    def fake_run(cmd, cwd=None, env=None, check=False):
        captured.append({"cmd": cmd, "cwd": cwd, "env": env, "check": check})
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(deploy.subprocess, "run", fake_run)
    monkeypatch.setattr(deploy, "NODE22_BIN", tmp_path)

    deploy.page_sync()

    # Three calls, in order
    assert len(captured) == 3, f"expected 3 subprocess calls, got {len(captured)}"
    assert captured[0]["cmd"] == deploy._shared_sync_cmd(), "1st call must be shared sync"
    assert captured[1]["cmd"] == deploy._bolts_sync_cmd(), "2nd call must be bolts sync"
    assert captured[2]["cmd"] == deploy._leijonat_sync_cmd(), "3rd call must be leijonat sync"

    # All three carry env=_subprocess_env()
    for i, call in enumerate(captured):
        assert call["check"] is True
        assert call["cwd"] == deploy.REPO_ROOT, f"call {i} wrong cwd"
        env = call["env"]
        assert isinstance(env, dict)
        assert env.get("AWS_PROFILE") == "default"
        assert str(tmp_path) in env.get("PATH", "")


def test_page_sync_leijonat_dest_check_allowed(monkeypatch, tmp_path):
    # If a future rewrite points the leijonat dest at a non-owned prefix, _check_allowed
    # must still intervene before the third subprocess fires.
    monkeypatch.setattr(deploy, "LEIJONAT_SYNC_DEST", "s3://jurigregg-static-site/other/")
    monkeypatch.setattr(deploy, "NODE22_BIN", tmp_path)

    call_count = {"n": 0}

    def fake_run(cmd, cwd=None, env=None, check=False):
        call_count["n"] += 1
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(deploy.subprocess, "run", fake_run)

    with pytest.raises(SystemExit):
        deploy.page_sync()
    # Shared + bolts ran; leijonat sync was blocked by _check_allowed before firing
    assert call_count["n"] == 2


# --- _check_allowed still accepts leijonat (it already did in init-02; pin it) ---


def test_check_allowed_accepts_leijonat_root():
    deploy._check_allowed("s3://jurigregg-static-site/leijonat/")


def test_check_allowed_accepts_leijonat_subpath():
    deploy._check_allowed("s3://jurigregg-static-site/leijonat/hero.webp")
