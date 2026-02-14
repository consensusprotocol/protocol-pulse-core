#!/usr/bin/env python3
"""Protocol Pulse stability + media bureau self-check.

Exit code 0 only when route gates and media infra gates pass.
"""

from __future__ import annotations

import shutil
import subprocess
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


def _check_openclaw() -> tuple[bool, str]:
    exe = shutil.which("openclaw")
    if not exe:
        root = Path.home() / ".nvm" / "versions" / "node"
        if root.exists():
            matches = sorted(root.glob("*/bin/openclaw"))
            if matches:
                exe = str(matches[-1])
    if not exe:
        return False, "openclaw not found"
    try:
        proc = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
        ver = (proc.stdout or proc.stderr or "").strip().splitlines()
        if proc.returncode != 0:
            return False, "openclaw version check failed"
        return True, (ver[0] if ver else "ok")
    except Exception as exc:
        return False, f"openclaw check failed: {exc}"


def _check_clipjob_model() -> tuple[bool, str]:
    try:
        import models
        from app import db
        from sqlalchemy import inspect

        if not hasattr(models, "ClipJob"):
            return False, "models.ClipJob missing"
        with app.app_context():
            insp = inspect(db.engine)
            if "clip_job" not in set(insp.get_table_names()):
                return False, "clip_job table missing (run flask db upgrade)"
        return True, "clip_job model+table ok"
    except Exception as exc:
        return False, f"clip_job check failed: {exc}"


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

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

    ok, detail = _check_openclaw()
    if ok:
        print(f"[PASS] openclaw -> {detail}")
    else:
        print(f"[FAIL] openclaw -> {detail}")
        failures.append("openclaw:missing")

    ok, detail = _check_clipjob_model()
    if ok:
        print(f"[PASS] clipjob -> {detail}")
    else:
        print(f"[FAIL] clipjob -> {detail}")
        failures.append("clipjob:missing")

    # Article integrity (warn-only): newest 5 published must pass validation gate.
    try:
        import models
        from services.content_generator import validate_article_for_publish

        with app.app_context():
            newest = (
                models.Article.query.filter(models.Article.published.is_(True))
                .order_by(models.Article.created_at.desc())
                .limit(5)
                .all()
            )
        broken = 0
        for a in newest:
            ok, errs = validate_article_for_publish(a)
            if not ok:
                broken += 1
        if broken:
            msg = f"Broken published articles detected: {broken}"
            print(f"[WARN] {msg}")
            warnings.append(msg)
        else:
            print("[PASS] article integrity -> newest published ok")
    except Exception as exc:
        # Never fail the suite for this check yet.
        print(f"[WARN] article integrity check skipped: {exc}")

    if failures:
        print("ALL GREEN: NO")
        print("FAILURES: " + ", ".join(failures))
        return 1

    print("ALL GREEN: YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
