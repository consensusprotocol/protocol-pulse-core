#!/usr/bin/env python3
"""Minimal route self-check using Flask test_client."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app  # noqa: E402

ROUTES_TO_CHECK = [
    "/",
    "/hub",
    "/sentry",
    "/start",
    "/command",
    "/privacy",
    "/terms",
    "/live",
    "/whale-watcher",
    "/dashboard",
    "/clips",
]

ALLOWED_STATUS = {200, 302}


def main() -> int:
    failures: list[str] = []
    with app.test_client() as client:
        for route in ROUTES_TO_CHECK:
            resp = client.get(route, follow_redirects=False)
            code = resp.status_code
            if code in ALLOWED_STATUS:
                print(f"[PASS] {route} -> {code}")
            else:
                print(f"[FAIL] {route} -> {code}")
                failures.append(f"{route}:{code}")

        network_resp = client.get("/api/network-data", follow_redirects=False)
        if network_resp.status_code == 200:
            print("[PASS] /api/network-data -> 200")
        else:
            print(f"[FAIL] /api/network-data -> {network_resp.status_code}")
            failures.append(f"/api/network-data:{network_resp.status_code}")

        cmd_resp = client.post("/api/command/test-connection", json={}, follow_redirects=False)
        if cmd_resp.status_code == 200:
            print("[PASS] /api/command/test-connection -> 200")
        else:
            print(f"[FAIL] /api/command/test-connection -> {cmd_resp.status_code}")
            failures.append(f"/api/command/test-connection:{cmd_resp.status_code}")

    try:
        from services.medley_assembler import MedleyAssemblerService
        svc = MedleyAssemblerService()
        if callable(getattr(svc, "run", None)):
            print("[PASS] media smoke test -> medley_assembler init ok")
        else:
            print("[FAIL] media smoke test -> run() missing")
            failures.append("media_smoke:run_missing")
    except Exception as exc:
        print(f"[FAIL] media smoke test -> {exc}")
        failures.append("media_smoke:init_failed")

    if failures:
        print("ALL GREEN: NO")
        print("FAILURES: " + ", ".join(failures))
        return 1

    print("ALL GREEN: YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

