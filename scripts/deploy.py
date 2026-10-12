"""Deploy KiekkokeskusStack and (future) sync site prefixes.

Default behavior is `cdk diff`, which exits without modifying anything. Pass `--approved` to
actually deploy — that uses `cdk deploy --require-approval never`, because the approval gate
belongs to the human workflow (/execute-prp: show diff, get go, then run with --approved), not
to CDK's TTY prompt. See ADR-032.

Hard rules:
- AWS profile is always 'default' (ADR-025).
- The page-sync section only allows the three owned prefixes (ADR-024).
- Node 22 is prepended to PATH so cdk picks up the keg-only install (init-02 Step 0).
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
INFRA_DIR = REPO_ROOT / "infra"
NODE22_BIN = pathlib.Path("/opt/homebrew/opt/node@22/bin")
ALLOWED_PREFIXES: tuple[str, ...] = ("bolts/", "leijonat/", "kiekkokeskus/")


def _subprocess_env() -> dict[str, str]:
    if not NODE22_BIN.is_dir():
        sys.exit(f"error: {NODE22_BIN} not found. Run `brew install node@22` (init-02 Step 0).")
    env = {**os.environ, "AWS_PROFILE": "default"}
    env["PATH"] = f"{NODE22_BIN}:{env.get('PATH', '')}"
    return env


def cdk_diff() -> None:
    cmd = ["npx", "cdk", "diff", "KiekkokeskusStack"]
    subprocess.run(cmd, cwd=INFRA_DIR, env=_subprocess_env(), check=True)


def cdk_deploy() -> None:
    cmd = [
        "npx",
        "cdk",
        "deploy",
        "KiekkokeskusStack",
        "--require-approval",
        "never",
    ]
    subprocess.run(cmd, cwd=INFRA_DIR, env=_subprocess_env(), check=True)


SHARED_SYNC_DEST = "s3://jurigregg-static-site/kiekkokeskus/"
SHARED_SYNC_SOURCE = "site/kiekkokeskus/"
BOLTS_SYNC_DEST = "s3://jurigregg-static-site/bolts/"
BOLTS_SYNC_SOURCE = "site/bolts/"
LEIJONAT_SYNC_DEST = "s3://jurigregg-static-site/leijonat/"
LEIJONAT_SYNC_SOURCE = "site/leijonat/"


def _shared_sync_cmd() -> list[str]:
    return [
        "aws",
        "s3",
        "sync",
        SHARED_SYNC_SOURCE,
        SHARED_SYNC_DEST,
        "--delete",
        "--exclude",
        "*.test.js",
        "--exclude",
        "_dev/*",
        "--exclude",
        "package.json",
        "--cache-control",
        "public, max-age=300",
        "--profile",
        "default",
    ]


def _bolts_sync_cmd() -> list[str]:
    # --exclude "*.test.js" is mandatory: site/bolts/view.test.js lives next to the real page
    # modules, and without the exclude it would ship to prod alongside main.js.
    return [
        "aws",
        "s3",
        "sync",
        BOLTS_SYNC_SOURCE,
        BOLTS_SYNC_DEST,
        "--delete",
        "--exclude",
        "*.test.js",
        "--cache-control",
        "public, max-age=300",
        "--profile",
        "default",
    ]


def _leijonat_sync_cmd() -> list[str]:
    # --exclude "*.test.js" is mandatory for the same reason bolts has it: site/leijonat/
    # view.test.js lives next to the real page modules and must not deploy.
    return [
        "aws",
        "s3",
        "sync",
        LEIJONAT_SYNC_SOURCE,
        LEIJONAT_SYNC_DEST,
        "--delete",
        "--exclude",
        "*.test.js",
        "--cache-control",
        "public, max-age=300",
        "--profile",
        "default",
    ]


def page_sync() -> None:
    """Sync shared → bolts → leijonat (ADR-024, ADR-039).

    Order matters: the shared prefix must land first so that /bolts and /leijonat never
    reference a module (page.js, controller.js, view.js's imports) that isn't on S3 yet.
    Leijonat lands after bolts for the same reason — nothing on /bolts depends on /leijonat,
    but keeping a consistent order keeps the deploy script simple. --delete is scoped per
    prefix. Cache-Control is set per-object so a deploy is visible within ~5 min (the
    distribution's legacy default is 1 h, see ADR-022 verified note).

    Pre-deploy workflow (do before the first real leijonat sync — PRP-08 Step 7):
      - aws s3 ls s3://jurigregg-static-site/leijonat/ --recursive --profile default
      - aws s3 sync site/leijonat/ s3://jurigregg-static-site/leijonat/ --delete \
            --exclude "*.test.js" --dryrun --profile default
      Any delete: line or a count other than 4 uploads should stop the deploy.
    """
    _check_allowed(SHARED_SYNC_DEST)
    # env=_subprocess_env() keeps AWS_PROFILE=default and the Node 22 PATH prefix in sync with
    # cdk_diff / cdk_deploy.
    subprocess.run(_shared_sync_cmd(), cwd=REPO_ROOT, env=_subprocess_env(), check=True)
    _check_allowed(BOLTS_SYNC_DEST)
    subprocess.run(_bolts_sync_cmd(), cwd=REPO_ROOT, env=_subprocess_env(), check=True)
    _check_allowed(LEIJONAT_SYNC_DEST)
    subprocess.run(_leijonat_sync_cmd(), cwd=REPO_ROOT, env=_subprocess_env(), check=True)


def _check_allowed(dest: str) -> None:
    """Reject any sync whose destination isn't one of the three owned prefixes."""
    prefix_part = dest.split("/", 3)[-1] if dest.startswith("s3://") else dest
    if not any(prefix_part.startswith(p) for p in ALLOWED_PREFIXES):
        sys.exit(f"error: refusing to sync to {dest!r}: not in {ALLOWED_PREFIXES} (ADR-024)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Default: cdk diff and exit. --approved: cdk deploy + page sync."
    )
    parser.add_argument(
        "--approved",
        action="store_true",
        help="run cdk deploy after you have reviewed the diff (ADR-032)",
    )
    args = parser.parse_args()

    if not args.approved:
        cdk_diff()
        print("deploy.py: diff shown. Re-run with --approved to deploy.")
        return

    cdk_deploy()
    page_sync()
    print("deploy: ok")


if __name__ == "__main__":
    main()
