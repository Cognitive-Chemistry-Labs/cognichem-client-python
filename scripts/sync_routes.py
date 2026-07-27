#!/usr/bin/env python3
"""Assert client ROUTES keys match a backend ROUTE_MAP snapshot.

Usage:
  # Against a checked-in snapshot (default):
  python scripts/sync_routes.py

  # Against a live monorepo path:
  python scripts/sync_routes.py --backend-config ../cognichem/apps/back-end-api/src/core/config.py
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT_CONSTANTS = ROOT / "src" / "cognichem_client" / "constants.py"
SNAPSHOT = ROOT / "scripts" / "route_map_keys.txt"

EXPECTED_KEYS = [
    "auth_login_email",
    "auth_check",
    "auth_refresh",
    "auth_logout",
    "auth_api_keys",
    "auth_api_keys_item",
    "auth_api_keys_rotate",
    "jobs_submit",
    "jobs_submit_multiple",
    "jobs_info",
    "jobs_list",
    "jobs_status",
    "jobs_result",
    "jobs_result_multiple",
    "jobs_cancel",
    "jobs_delete",
    "inference_submit",
    "inference_submit_batch",
    "inference_list",
    "inference_status",
    "inference_result",
    "inference_delete",
    "mpnn_user_models",
    "mpnn_public_models",
    "utils_submit",
    "utils_list",
    "utils_status",
    "utils_result",
    "utils_delete",
    "usage_limits",
]


def client_route_keys() -> set[str]:
    tree = ast.parse(CLIENT_CONSTANTS.read_text())
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "ROUTES" and isinstance(node.value, ast.Dict):
                keys: set[str] = set()
                for key in node.value.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        keys.add(key.value)
                return keys
    raise RuntimeError("ROUTES dict not found in constants.py")


def keys_from_backend_config(path: Path) -> set[str]:
    text = path.read_text()
    # Match string keys in ROUTE_MAP return dict literals: "jobs_submit":
    return set(re.findall(r'"([a-z0-9_]+)":\s*f?"?\{?b\}?', text)) & set(EXPECTED_KEYS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-config",
        type=Path,
        help="Optional path to cognichem apps/back-end-api/src/core/config.py",
    )
    parser.add_argument(
        "--write-snapshot",
        action="store_true",
        help="Write scripts/route_map_keys.txt from EXPECTED_KEYS",
    )
    args = parser.parse_args()

    if args.write_snapshot:
        SNAPSHOT.write_text("\n".join(EXPECTED_KEYS) + "\n")
        print(f"Wrote {SNAPSHOT}")
        return 0

    client_keys = client_route_keys()
    expected = set(EXPECTED_KEYS)
    if args.backend_config:
        expected = keys_from_backend_config(args.backend_config)
        if not expected:
            print("Failed to parse backend ROUTE_MAP keys", file=sys.stderr)
            return 1
    elif SNAPSHOT.exists():
        expected = {
            line.strip()
            for line in SNAPSHOT.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        }

    missing = expected - client_keys
    extra = client_keys - expected
    if missing or extra:
        if missing:
            print(f"Missing in client ROUTES: {sorted(missing)}", file=sys.stderr)
        if extra:
            print(f"Extra in client ROUTES: {sorted(extra)}", file=sys.stderr)
        return 1

    print(f"OK: {len(client_keys)} route keys match contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
