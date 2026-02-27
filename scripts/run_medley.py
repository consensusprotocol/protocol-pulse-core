#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from core.event_bus import emit_event
from core.governance import check_and_consume
from core.scoring_engine import score_medley_script

ROOT = Path("/home/ultron/protocol_pulse")


def run_dry() -> dict:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    run_id = uuid.uuid4().hex[:10]
    out_dir = ROOT / "artifacts" / "medley" / today / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    emit_event("medley_dry_run_start", "run_medley.py", lane="medley", title="medley dry-run start", detail=f"run_id={run_id}")

    gov = check_and_consume("medley_render", units=1)
    if not gov.get("ok"):
        emit_event("medley_dry_run_blocked", "run_medley.py", lane="medley", severity="warn", title="medley blocked", detail="governance cap exceeded")
        return {"ok": False, "error": "governance_cap_exceeded", "run_id": run_id}

    narration = (
        "hook: whales moved size while volatility stayed compressed. "
        "context: risk clusters show regional strain. "
        "escalation: watch liquidity pockets around major support. "
        "recap: stay sovereign, stay liquid, act early."
    )
    score = score_medley_script(narration)
    run_plan = {
        "run_id": run_id,
        "date": today,
        "mode": "dry-run",
        "sources": ["value_stream", "whale_events", "risk_events"],
        "segments": [
            {"role": "hook", "start": 0, "end": 20},
            {"role": "context", "start": 20, "end": 55},
            {"role": "escalation", "start": 55, "end": 90},
            {"role": "recap", "start": 90, "end": 120},
        ],
        "narration_script": narration,
        "score": score,
    }
    (out_dir / "run_plan.json").write_text(json.dumps(run_plan, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    (out_dir / "narration.txt").write_text(narration + "\n", encoding="utf-8")
    emit_event("medley_dry_run_progress", "run_medley.py", lane="medley", title="run plan written", detail=str(out_dir / "run_plan.json"))

    source_mp4 = ROOT / "logs" / "medley_smoke.mp4"
    output_artifact = out_dir / "medley_preview.mp4"
    if source_mp4.exists():
        shutil.copy2(source_mp4, output_artifact)
    else:
        (out_dir / "placeholder_asset.txt").write_text("no media artifact available; placeholder generated.\n", encoding="utf-8")
    emit_event("medley_dry_run_finish", "run_medley.py", lane="medley", title="medley dry-run finish", detail=f"output={output_artifact.name if output_artifact.exists() else 'placeholder'}")
    return {"ok": True, "run_id": run_id, "output_dir": str(out_dir), "artifact_exists": output_artifact.exists()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--today", action="store_true")
    args = parser.parse_args()
    if not args.dry_run:
        print("only --dry-run is supported in this safe mode build")
        return 1
    out = run_dry()
    print(json.dumps(out, ensure_ascii=True))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

