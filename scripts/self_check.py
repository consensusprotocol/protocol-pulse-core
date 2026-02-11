#!/usr/bin/env python3
"""
Protocol Pulse stability self-check gates.

Exit code 0 only when all gates pass.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BASE_URL = os.environ.get("SELF_CHECK_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
SELF_CHECK_HEADERS = {"X-Self-Check": "1"}
EVENTS_PATH = PROJECT_ROOT / "data" / "pulse_events.jsonl"
RUNTIME_STATUS_PATH = PROJECT_ROOT / "logs" / "runtime_status.json"


def _print(status: str, gate: str, detail: str = "") -> None:
    print(f"[{status}] {gate}" + (f" :: {detail}" if detail else ""))


def gate_a_routes() -> tuple[bool, str]:
    routes = [
        ("/", {}),
        ("/hub", SELF_CHECK_HEADERS),
        ("/value-stream", {}),
        ("/signal-terminal", {}),
        ("/mining-risk", {}),
    ]
    failed = []
    for path, headers in routes:
        r = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=10, allow_redirects=False)
        if r.status_code != 200:
            failed.append(f"{path}:{r.status_code}")
    if failed:
        return False, "route failures " + ", ".join(failed)
    return True, "all core routes returned 200"


def gate_b_value_stream() -> tuple[bool, str]:
    from app import app, db
    import models
    from services import value_stream_service as vss

    with app.app_context():
        platforms = {str(p[0] or "").lower() for p in db.session.query(models.CuratedPost.platform).distinct().all()}
        bad = sorted([p for p in platforms if p in {"twitter", "stacker_news"}])
        if bad:
            return False, f"platform mismatch detected: {bad}"

        # Submit validation
        r = requests.post(
            f"{BASE_URL}/api/value-stream/submit",
            json={"url": "not-a-url"},
            timeout=10,
        )
        if r.status_code == 200 and (r.json() or {}).get("success"):
            return False, "submit endpoint accepted invalid URL"

        # Zap verification gate: no payment_hash -> pending and no score inflation.
        post = models.CuratedPost(platform="x", original_url="https://x.com/example/status/1", title="self-check zap")
        post.calculate_signal_score()
        before_score = float(post.signal_score or 0.0)
        before_sats = int(post.total_sats or 0)
        db.session.add(post)
        db.session.commit()
        try:
            result = vss.process_zap(post.id, None, 1000, payment_hash="")
            db.session.refresh(post)
            if result.get("status") != "pending":
                return False, "zap without verification did not remain pending"
            if int(post.total_sats or 0) != before_sats or float(post.signal_score or 0.0) != before_score:
                return False, "pending zap changed totals/signal_score"
        finally:
            db.session.query(models.ZapEvent).filter_by(post_id=post.id).delete()
            db.session.delete(post)
            db.session.commit()
    return True, "platforms canonical + submit validation + pending zap behavior ok"


def gate_c_streaming() -> tuple[bool, str]:
    # SSE heartbeat/data
    saw_data = False
    saw_heartbeat = False
    start = time.time()
    with requests.get(f"{BASE_URL}/api/signal-terminal/stream", stream=True, timeout=(5, 30)) as r:
        if r.status_code != 200:
            return False, f"sse status {r.status_code}"
        for raw in r.iter_lines(decode_unicode=True):
            if raw is None:
                continue
            line = str(raw)
            if line.startswith("data:"):
                saw_data = True
            if line.startswith(": heartbeat"):
                saw_heartbeat = True
            if saw_data and saw_heartbeat:
                break
            if time.time() - start > 22:
                break
    if not (saw_data or saw_heartbeat):
        return False, "sse produced no data or heartbeat"

    # SocketIO local connect smoke
    try:
        import socketio as sio_client
        client = sio_client.Client(reconnection=False, logger=False, engineio_logger=False)
        client.connect(
            f"{BASE_URL}?self_check=1",
            namespaces=["/hub"],
            headers=SELF_CHECK_HEADERS,
            transports=["polling"],
            wait_timeout=5,
        )
        ok = client.connected
        client.disconnect()
        if not ok:
            return False, "socketio connect failed"
    except Exception as e:
        return False, f"socketio connect exception: {e}"
    return True, "sse + socketio smoke passed"


def gate_d_whale() -> tuple[bool, str]:
    from app import app
    from scripts.intelligence_loop import run_whale_watcher_cycle

    with app.app_context():
        result = run_whale_watcher_cycle()
    if not isinstance(result, dict):
        return False, "whale cycle returned non-dict"
    if not RUNTIME_STATUS_PATH.exists():
        return False, "runtime_status.json missing"
    status = json.loads(RUNTIME_STATUS_PATH.read_text(encoding="utf-8"))
    whale_last = ((status.get("whale") or {}).get("last_run"))
    if not whale_last:
        return False, "whale last_run not recorded"
    return True, f"whale cycle ok scanned={result.get('scanned')} inserted={result.get('inserted')}"


def gate_e_sentry_dry() -> tuple[bool, str]:
    from app import app
    from scripts.intelligence_loop import run_x_sentry_cycle, SignalLogger

    seed_posts = [
        {
            "handle": "saylor",
            "post_id": "1234567890123",
            "text": "bitcoin hashrate rose while fiat policy lost credibility. sovereignty in code.",
        }
    ]
    with app.app_context():
        result = run_x_sentry_cycle(dry_run=True, seed_posts=seed_posts)
    SignalLogger().sentry_update(result)
    if int(result.get("drafted", 0)) < 1:
        return False, "dry-run did not draft expected reply artifact"
    if not EVENTS_PATH.exists():
        return False, "pulse event stream file missing"
    tail = EVENTS_PATH.read_text(encoding="utf-8").splitlines()[-20:]
    if not any('"tag": "sentry"' in ln for ln in tail):
        return False, "structured sentry event not emitted"
    return True, "x-sentry dry-run drafted and emitted structured event"


def gate_f_risk() -> tuple[bool, str]:
    p = PROJECT_ROOT / "config" / "mining_locations.json"
    if not p.exists():
        return False, "mining_locations.json missing"
    data = json.loads(p.read_text(encoding="utf-8"))
    entries = data.get("jurisdictions") or data.get("locations") or []
    if not entries:
        return False, "mining locations file empty"
    r = requests.get(f"{BASE_URL}/api/risk-data", headers=SELF_CHECK_HEADERS, timeout=10)
    if r.status_code != 200:
        return False, f"/api/risk-data status {r.status_code}"
    payload = r.json()
    if not (payload.get("jurisdictions") or []):
        return False, "risk api returned empty jurisdictions"
    return True, "risk dataset and api payload are non-empty"


def gate_g_medley() -> tuple[bool, str]:
    out = PROJECT_ROOT / "logs" / "medley_smoke.mp4"
    prog = PROJECT_ROOT / "logs" / "medley_smoke.progress"
    rep = PROJECT_ROOT / "logs" / "medley_smoke.report.json"
    for p in (out, prog, rep):
        try:
            p.unlink()
        except Exception:
            pass
    cmd = [
        str(PROJECT_ROOT / "venv" / "bin" / "python"),
        str(PROJECT_ROOT / "medley_director.py"),
        "--output",
        str(out),
        "--progress-file",
        str(prog),
        "--report-file",
        str(rep),
        "--duration",
        "6",
    ]
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "1"
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        return False, f"medley smoke failed rc={proc.returncode} stderr={proc.stderr[:180]}"
    if not out.exists() or out.stat().st_size <= 0:
        return False, "medley output artifact missing"
    return True, f"medley smoke artifact ok size={out.stat().st_size}"


def main() -> int:
    gates = [
        ("GATE A (routes)", gate_a_routes),
        ("GATE B (value stream)", gate_b_value_stream),
        ("GATE C (streaming)", gate_c_streaming),
        ("GATE D (whale watcher)", gate_d_whale),
        ("GATE E (x-sentry dry)", gate_e_sentry_dry),
        ("GATE F (risk oracle)", gate_f_risk),
        ("GATE G (medley smoke)", gate_g_medley),
    ]
    all_ok = True
    for name, fn in gates:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"exception: {e}"
        _print("PASS" if ok else "FAIL", name, detail)
        if not ok:
            all_ok = False
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

