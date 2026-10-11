"""Deploy helper tests: the shared-asset sync is wired, prefix-scoped, and leaves AWS_PROFILE
and the Node PATH set the same way cdk_diff/cdk_deploy do (ADR-024, ADR-039)."""

from __future__ import annotations

import subprocess

import deploy
import pytest

# --- _check_allowed ---


def test_check_allowed_accepts_kiekkokeskus_root():
    # Should not raise / exit.
    deploy._check_allowed("s3://jurigregg-static-site/kiekkokeskus/")


def test_check_allowed_accepts_kiekkokeskus_subpath():
    deploy._check_allowed("s3://jurigregg-static-site/kiekkokeskus/kk.css")


def test_check_allowed_accepts_bolts_and_leijonat():
    # Prefixes reserved for init-07 / init-08, still allowed by the guard.
    deploy._check_allowed("s3://jurigregg-static-site/bolts/")
    deploy._check_allowed("s3://jurigregg-static-site/leijonat/")


def test_check_allowed_refuses_bucket_root():
    with pytest.raises(SystemExit):
        deploy._check_allowed("s3://jurigregg-static-site/")


def test_check_allowed_refuses_data_prefix():
    with pytest.raises(SystemExit):
        deploy._check_allowed("s3://jurigregg-static-site/data/")


def test_check_allowed_refuses_other_prefix():
    with pytest.raises(SystemExit):
        deploy._check_allowed("s3://jurigregg-static-site/kielipuolto/")


# --- _shared_sync_cmd shape ---


def test_shared_sync_cmd_pins_every_argument():
    cmd = deploy._shared_sync_cmd()
    assert cmd[0:3] == ["aws", "s3", "sync"]
    assert cmd[3] == "site/kiekkokeskus/"
    assert cmd[4] == "s3://jurigregg-static-site/kiekkokeskus/"
    assert "--delete" in cmd
    # Three excludes, each as --exclude <value>
    excludes = [cmd[i + 1] for i, flag in enumerate(cmd) if flag == "--exclude"]
    assert set(excludes) == {"*.test.js", "_dev/*", "package.json"}
    # Cache-Control value
    cc_idx = cmd.index("--cache-control")
    assert cmd[cc_idx + 1] == "public, max-age=300"
    # Profile explicit (ADR-025)
    prof_idx = cmd.index("--profile")
    assert cmd[prof_idx + 1] == "default"


# --- page_sync wires subprocess with env=_subprocess_env() ---


def test_page_sync_runs_shared_cmd_with_env(monkeypatch):
    captured: dict[str, object] = {}

    def fake_run(cmd, cwd=None, env=None, check=False):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["env"] = env
        captured["check"] = check
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(deploy.subprocess, "run", fake_run)

    deploy.page_sync()

    assert captured["check"] is True
    assert captured["cmd"] == deploy._shared_sync_cmd()
    assert captured["cwd"] == deploy.REPO_ROOT

    # env matches _subprocess_env(): AWS_PROFILE=default and the Node 22 bin on PATH.
    env = captured["env"]
    assert isinstance(env, dict)
    assert env.get("AWS_PROFILE") == "default"
    assert str(deploy.NODE22_BIN) in env.get("PATH", "")


def test_page_sync_refuses_if_check_allowed_rejects(monkeypatch):
    # Belt-and-suspenders: if a future rewrite points page_sync at the wrong prefix, the
    # guard still intervenes before any subprocess runs.
    monkeypatch.setattr(deploy, "SHARED_SYNC_DEST", "s3://jurigregg-static-site/other/")
    monkeypatch.setattr(
        deploy,
        "_shared_sync_cmd",
        lambda: ["aws", "s3", "sync", "site/", "s3://jurigregg-static-site/other/"],
    )

    def must_not_run(*_a, **_kw):
        raise AssertionError("subprocess.run should not fire after _check_allowed rejects")

    monkeypatch.setattr(deploy.subprocess, "run", must_not_run)

    with pytest.raises(SystemExit):
        deploy.page_sync()
