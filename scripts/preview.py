"""Local preview server for the dev harness. stdlib only.

Serves `site/` at `/` on `127.0.0.1:8006`. Maps `/data/kiekkokeskus/{bolts,leijonat}.json` to
`tests/golden/` by default, or to `--data DIR`.

Flags:
  --port N      bind port (default 8006)
  --data DIR    directory holding bolts.json / leijonat.json (default: tests/golden)
  --fresh       rewrite generatedAt to now before serving (so stale banner can be seen off)
  --break NAME  swap schemaVersion to 999 for bolts|leijonat (error-banner demo)

Never writes to disk, never calls AWS or the NHL. ADR-003 (same-origin only).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import http.server
import json
import mimetypes
import pathlib
import socketserver
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE_DIR = REPO_ROOT / "site"
DEFAULT_DATA = REPO_ROOT / "tests" / "golden"

# Ensure the mime map matches what AWS CLI's Python mimetypes delivers (and what module
# scripts need): .js → text/javascript, .css → text/css.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")

DATA_PREFIX = "/data/kiekkokeskus/"
KNOWN_FILES = ("bolts.json", "leijonat.json")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--port", type=int, default=8006)
    parser.add_argument("--data", type=pathlib.Path, default=DEFAULT_DATA)
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="rewrite generatedAt to current UTC time before serving",
    )
    parser.add_argument(
        "--break",
        dest="break_",
        choices=("bolts", "leijonat"),
        default=None,
        help="serve schemaVersion: 999 for the named file (demo error banner)",
    )
    return parser.parse_args(argv)


def transform(
    name: str, raw: bytes, *, fresh: bool, break_: str | None, now_iso: str | None = None
) -> bytes:
    """Apply --fresh / --break to a golden file's bytes. Pure; used in tests."""
    if not fresh and break_ != name.removesuffix(".json"):
        return raw
    payload: dict[str, Any] = json.loads(raw)
    if fresh:
        iso = now_iso or _dt.datetime.now(tz=_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload["generatedAt"] = iso
    if break_ == name.removesuffix(".json"):
        payload["schemaVersion"] = 999
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def resolve_data_path(data_dir: pathlib.Path, request_path: str) -> pathlib.Path | None:
    """Return a path inside data_dir for a /data/kiekkokeskus/<file> request, else None."""
    if not request_path.startswith(DATA_PREFIX):
        return None
    name = request_path[len(DATA_PREFIX) :]
    if name not in KNOWN_FILES:
        return None
    return data_dir / name


class Handler(http.server.SimpleHTTPRequestHandler):
    # Set per-instance via a factory below.
    data_dir: pathlib.Path = DEFAULT_DATA
    fresh: bool = False
    break_: str | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        # Quiet: one line per request to stderr, no HTML.
        sys.stderr.write(f"preview: {self.address_string()} - {format % args}\n")

    def do_GET(self) -> None:  # noqa: N802
        data_path = resolve_data_path(self.data_dir, self.path.split("?", 1)[0])
        if data_path is not None:
            self._serve_data(data_path)
            return
        super().do_GET()

    def _serve_data(self, data_path: pathlib.Path) -> None:
        if not data_path.exists():
            self.send_error(404, f"missing golden file: {data_path.name}")
            return
        raw = data_path.read_bytes()
        body = transform(data_path.name, raw, fresh=self.fresh, break_=self.break_)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "public, max-age=300")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _make_handler(args: argparse.Namespace) -> type[Handler]:
    class _H(Handler):
        data_dir = args.data.resolve()
        fresh = args.fresh
        break_ = args.break_

    return _H


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.data.exists():
        print(f"preview: --data {args.data} does not exist", file=sys.stderr)
        return 2
    handler_cls = _make_handler(args)
    with socketserver.ThreadingTCPServer(("127.0.0.1", args.port), handler_cls) as httpd:
        print(
            f"preview: http://127.0.0.1:{args.port}/kiekkokeskus/_dev/harness.html"
            f"  (data={args.data}, fresh={args.fresh}, break={args.break_})"
        )
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
