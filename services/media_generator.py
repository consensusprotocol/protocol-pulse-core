from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from services import ollama_runtime

logger = logging.getLogger(__name__)


class MediaGenerator:
    def __init__(self) -> None:
        self.project_root = Path("/home/ultron/protocol_pulse")
        self.briefs_path = self.project_root / "data" / "daily_briefs.json"
        self.state_path = self.project_root / "logs" / "media_generator_state.json"
        self.output_path = self.project_root / "static" / "media" / "daily_pulse.mp4"
        self.progress_path = self.project_root / "logs" / "daily_pulse.progress"
        self.report_path = self.project_root / "logs" / "daily_pulse.report.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_briefs(self) -> List[Dict]:
        try:
            payload = json.loads(self.briefs_path.read_text(encoding="utf-8"))
            return list(payload.get("briefs") or [])
        except Exception:
            return []

    def _load_state(self) -> Dict:
        try:
            if self.state_path.exists():
                return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"last_rendered_ts": None, "last_brief_ts": None}

    def _save_state(self, state: Dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")

    def _latest_brief(self) -> Dict:
        briefs = self._load_briefs()
        return briefs[-1] if briefs else {}

    def _build_script(self, brief: Dict) -> str:
        summary = str(brief.get("summary") or "").strip()
        urgent = brief.get("urgent_events") or []
        prompt = (
            "convert this sovereign brief into a 60-second narration script.\n"
            "style: lower-case, tactical, concise. max 130 words.\n"
            "must include one closing cta: 'track it live on protocol pulse.'\n\n"
            f"summary:\n{summary}\n\nurgent:\n{json.dumps(urgent, ensure_ascii=True)}"
        )
        script = ollama_runtime.generate(
            prompt=prompt,
            preferred_model="llama3.1",
            options={"temperature": 0.4, "num_predict": 180},
            timeout=10,
        )
        if not script:
            script = (
                "market structure is tightening while whale flows stay active. "
                "regulatory stress points remain on watch. "
                "risk is concentrated but liquidity windows still open. "
                "track it live on protocol pulse."
            )
        return script.strip()

    def _pick_assets(self, brief: Dict) -> List[str]:
        text = f"{brief.get('summary', '')} {' '.join(brief.get('urgent_events') or [])}".lower()
        assets: List[str] = []
        if "outflow" in text or "whale" in text:
            assets.append("whale-flows.mp4")
        if "regulatory" in text or "sec" in text:
            assets.append("regulatory-headlines.mp4")
        if "bank" in text:
            assets.append("bank-stress.mp4")
        if not assets:
            assets = ["market-charts.mp4"]
        return assets

    def _render_fast(self) -> Dict:
        cmd = [
            str(self.project_root / "venv" / "bin" / "python"),
            str(self.project_root / "medley_director.py"),
            "--output", str(self.output_path),
            "--progress-file", str(self.progress_path),
            "--report-file", str(self.report_path),
            "--duration", "60",
        ]
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = "1"
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, env=env)
        return {
            "ok": proc.returncode == 0 and self.output_path.exists(),
            "returncode": proc.returncode,
            "stderr_tail": (proc.stderr or "")[-300:],
        }

    def maybe_render_from_latest_brief(self) -> Dict:
        brief = self._latest_brief()
        if not brief:
            return {"rendered": False, "reason": "no_brief"}
        state = self._load_state()
        brief_ts = str(brief.get("ts") or "")
        last_brief_ts = str(state.get("last_brief_ts") or "")
        last_rendered = state.get("last_rendered_ts")
        if brief_ts and brief_ts == last_brief_ts:
            return {"rendered": False, "reason": "already_rendered_for_brief"}
        if last_rendered:
            try:
                if datetime.utcnow() - datetime.fromisoformat(last_rendered) < timedelta(minutes=30):
                    return {"rendered": False, "reason": "render_cooldown"}
            except Exception:
                pass

        script = self._build_script(brief)
        assets = self._pick_assets(brief)
        render = self._render_fast()
        report = {
            "ts": datetime.utcnow().isoformat(),
            "brief_ts": brief_ts,
            "script": script,
            "assets": assets,
            "render": render,
        }
        if render.get("ok"):
            state["last_rendered_ts"] = report["ts"]
            state["last_brief_ts"] = brief_ts
            self._save_state(state)
            return {"rendered": True, **report}
        return {"rendered": False, **report}


media_generator = MediaGenerator()

