"""Deploy KiekkokeskusStack and (future) sync site prefixes.

Hard rules:
- AWS profile is always 'default' (ADR-025).
- The page-sync section only allows the three owned prefixes (ADR-024).
- Node 22 is prepended to PATH so cdk picks up the keg-only install (init-02 Step 0).
"""

from __future__ import annotations

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


def cdk_deploy() -> None:
    cmd = ["npx", "cdk", "deploy", "KiekkokeskusStack", "--require-approval", "broadening"]
    subprocess.run(cmd, cwd=INFRA_DIR, env=_subprocess_env(), check=True)


def page_sync() -> None:
    """Placeholder for init-06. Each future sync must target an allowed prefix (ADR-024)."""
    # Example of the guard that will apply when init-06 fills this in:
    #   dest = "s3://jurigregg-static-site/bolts/"
    #   _check_allowed(dest)
    #   subprocess.run(
    #       ["aws", "s3", "sync", "site/bolts/", dest, "--profile", "default"], check=True
    #   )
    pass


def _check_allowed(dest: str) -> None:
    """Reject any sync whose destination isn't one of the three owned prefixes."""
    prefix_part = dest.split("/", 3)[-1] if dest.startswith("s3://") else dest
    if not any(prefix_part.startswith(p) for p in ALLOWED_PREFIXES):
        sys.exit(f"error: refusing to sync to {dest!r}: not in {ALLOWED_PREFIXES} (ADR-024)")


def main() -> None:
    cdk_deploy()
    page_sync()
    print("deploy: ok")


if __name__ == "__main__":
    main()
