from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from services.video_ingest import video_ingest_service
from services.video_analyst import video_analyst_service
from services.voice_director import voice_director_service
from services.medley_assembler import medley_assembler_service


class SovereignMedleyPipeline:
    def __init__(self) -> None:
        self.project_root = Path("/home/ultron/protocol_pulse")
        self.report_path = self.project_root / "logs" / "medley_pipeline_report.json"

    def run_once(self) -> Dict:
        stage1 = video_ingest_service.run(hours_back=24)
        stage2 = video_analyst_service.run()
        stage3 = voice_director_service.run()
        stage4 = medley_assembler_service.run()
        out = {
            "ts": datetime.utcnow().isoformat(),
            "stage1_ingest": stage1,
            "stage2_analyst": stage2,
            "stage3_voice": stage3,
            "stage4_assembly": stage4,
            "ok": bool(stage4.get("ok")),
        }
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(json.dumps(out, ensure_ascii=True, indent=2), encoding="utf-8")
        return out


sovereign_medley_pipeline = SovereignMedleyPipeline()

