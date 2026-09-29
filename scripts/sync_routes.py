#!/usr/bin/env python3
"""Assert client ROUTES cover the backend ROUTE_MAP with identical paths.

Every backend ``Settings.ROUTE_MAP`` key must exist in the client's
``ROUTES`` with the same path. The client may carry extra routes that
ROUTE_MAP does not list (health, templates, lookup, …); those are reported
but do not fail the check.

Usage:
  # Against the checked-in snapshot (default):
  python scripts/sync_routes.py

  # Against a live monorepo checkout:
  python scripts/sync_routes.py --backend-config ../cognichem/apps/back-end-api/src/core/config.py

  # Refresh the snapshot from a monorepo checkout:
  python scripts/sync_routes.py --backend-config <path> --write-snapshot
"""  # noqa: E501

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT_CONSTANTS = ROOT / "src" / "cognichem_client" / "constants.py"
SNAPSHOT = ROOT / "scripts" / "route_map.txt"
API_V1_STR = "/api/v1"

# ``"jobs_submit": f"{b}/jobs/submit"`` or the parenthesized multi-line form.
_BACKEND_ENTRY = re.compile(r'"([a-z0-9_]+)":\s*\(?\s*f"\{b\}([^"]*)"')


def client_routes() -> dict[str, str]:
    """Return the client's ROUTES as ``{key: path}``."""
    tree = ast.parse(CLIENT_CONSTANTS.read_text())
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "ROUTES"
            and isinstance(node.value, ast.Dict)
        ):
            routes: dict[str, str] = {}
            for key, value in zip(node.value.keys, node.value.values, strict=True):
                assert isinstance(key, ast.Constant) and isinstance(key.value, str)
                routes[key.value] = _render(value)
            return routes
    raise RuntimeError("ROUTES dict not found in constants.py")


def _render(value: ast.expr) -> str:
    """Render a ROUTES value (literal or ``f"{API_V1_STR}…"``) to a path."""
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    if isinstance(value, ast.JoinedStr):
        parts: list[str] = []
        for part in value.values:
            if isinstance(part, ast.Constant):
                parts.append(str(part.value))
            elif (
                isinstance(part, ast.FormattedValue)
                and isinstance(part.value, ast.Name)
                and part.value.id == "API_V1_STR"
            ):
                parts.append(API_V1_STR)
            else:
                raise RuntimeError(f"Unsupported ROUTES value: {ast.dump(value)}")
        return "".join(parts)
    raise RuntimeError(f"Unsupported ROUTES value: {ast.dump(value)}")


def backend_routes(path: Path) -> dict[str, str]:
    """Parse ``Settings.ROUTE_MAP`` from the backend config source."""
    text = path.read_text()
    start = text.find("def ROUTE_MAP")
    if start == -1:
        return {}
    body = text[start:]
    end = body.find("\n    def ", 1)
    body = body if end == -1 else body[:end]
    return {
        key: API_V1_STR + suffix.replace("{{", "{").replace("}}", "}")
        for key, suffix in _BACKEND_ENTRY.findall(body)
    }


def read_snapshot() -> dict[str, str]:
    """Read ``route_map.txt`` (``key path`` per line)."""
    routes: dict[str, str] = {}
    for line in SNAPSHOT.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, path = line.split(maxsplit=1)
            routes[key] = path
    return routes


def main() -> int:
    """Run the drift check and return a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-config",
        type=Path,
        help="Path to cognichem apps/back-end-api/src/core/config.py",
    )
    parser.add_argument(
        "--write-snapshot",
        action="store_true",
        help="Write scripts/route_map.txt from --backend-config",
    )
    args = parser.parse_args()

    if args.backend_config:
        expected = backend_routes(args.backend_config)
        if not expected:
            print("Failed to parse backend ROUTE_MAP", file=sys.stderr)
            return 1
    elif args.write_snapshot:
        print("--write-snapshot needs --backend-config", file=sys.stderr)
        return 1
    else:
        expected = read_snapshot()

    if args.write_snapshot:
        lines = ["# Backend Settings.ROUTE_MAP: key path"]
        lines += [f"{key} {path}" for key, path in expected.items()]
        SNAPSHOT.write_text("\n".join(lines) + "\n")
        print(f"Wrote {SNAPSHOT} ({len(expected)} routes)")
        return 0

    client = client_routes()
    missing = sorted(set(expected) - set(client))
    changed = sorted(
        key for key in set(expected) & set(client) if expected[key] != client[key]
    )
    extra = sorted(set(client) - set(expected))
    for key in missing:
        print(f"Missing in client ROUTES: {key} {expected[key]}", file=sys.stderr)
    for key in changed:
        print(
            f"Path mismatch for {key}: backend {expected[key]} != client {client[key]}",
            file=sys.stderr,
        )
    if missing or changed:
        return 1
    print(
        f"OK: {len(expected)} backend routes match; "
        f"{len(extra)} client-only routes ({', '.join(extra)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
