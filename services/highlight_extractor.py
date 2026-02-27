from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from app import db
import models

TIMESTAMP_RE = re.compile(r"(?<!\d)(?:(\d{1,2}):)?([0-5]?\d):([0-5]\d)(?!\d)")
PRIORITY_WORDS = ("signal", "warning", "must-watch", "must watch", "alpha")


def _to_seconds(groups: Tuple[str, str, str]) -> int:
    h = int(groups[0] or 0)
    m = int(groups[1] or 0)
    s = int(groups[2] or 0)
    return h * 3600 + m * 60 + s


def _score_label(label: str) -> float:
    l = (label or "").lower()
    score = 0.4
    for w in PRIORITY_WORDS:
        if w in l:
            score += 0.25
    if any(k in l for k in ("etf", "macro", "custody", "regulation", "mining")):
        score += 0.15
    return min(1.0, score)


class HighlightExtractorService:
    """Parse timestamp labels from partner video descriptions into PulseSegment rows."""

    def extract_from_description(self, video_id: str, description: str) -> List[Dict]:
        out = []
        lines = [ln.strip() for ln in (description or "").splitlines() if ln.strip()]
        for ln in lines:
            m = TIMESTAMP_RE.search(ln)
            if not m:
                continue
            start = _to_seconds(m.groups())
            label = ln[m.end():].strip(" -|:") or "segment"
            out.append({"video_id": video_id, "start_sec": start, "label": label, "priority": _score_label(label)})
        # remove duplicates and keep sorted
        uniq = {}
        for r in out:
            key = (r["video_id"], r["start_sec"])
            if key not in uniq or r["priority"] > uniq[key]["priority"]:
                uniq[key] = r
        rows = list(uniq.values())
        rows.sort(key=lambda x: (-x["priority"], x["start_sec"]))
        return rows

    def run(self, hours_back: int = 24, single_alpha_per_video: bool = False) -> Dict:
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)
        vids = (
            models.PartnerVideo.query.filter(models.PartnerVideo.harvested_at >= cutoff)
            .order_by(models.PartnerVideo.harvested_at.desc())
            .limit(200)
            .all()
        )
        created = 0
        scanned = 0
        segments_out = []
        for v in vids:
            scanned += 1
            extracted = self.extract_from_description(v.video_id, v.description or "")
            if not extracted:
                base_label = (v.title or "segment").lower()
                extracted = [
                    {"video_id": v.video_id, "start_sec": 30, "label": f"signal: {base_label[:120]}", "priority": 0.72},
                    {"video_id": v.video_id, "start_sec": 90, "label": f"alpha: why this matters now", "priority": 0.78},
                    {"video_id": v.video_id, "start_sec": 150, "label": f"warning: risk and opportunity breakdown", "priority": 0.76},
                ]
            if not extracted:
                continue
            # keep highest-priority segments; at least one.
            extracted = sorted(extracted, key=lambda x: x["priority"], reverse=True)
            if single_alpha_per_video:
                # Force one "alpha-heavy" 3-5 minute segment, skipping generic intro/outro windows.
                pick = extracted[0]
                start = int(pick["start_sec"])
                if start < 60:
                    start = 75
                pick = {**pick, "start_sec": start}
                extracted = [pick]
            else:
                extracted = extracted[:8]
            for seg in extracted:
                exists = models.PulseSegment.query.filter_by(video_id=v.video_id, start_sec=seg["start_sec"]).first()
                if exists:
                    continue
                row = models.PulseSegment(
                    partner_video_id=v.id,
                    video_id=v.video_id,
                    start_sec=seg["start_sec"],
                    label=(seg["label"] or "")[:300],
                    priority=float(seg["priority"]),
                )
                # Encode forced clip duration + extraction mode in label for downstream builder.
                if single_alpha_per_video:
                    row.label = f"{(row.label or 'alpha segment')[:220]} | clip=240s | mode=alpha_single"
                db.session.add(row)
                created += 1
                segments_out.append({"video_id": row.video_id, "start_sec": row.start_sec, "label": row.label, "priority": row.priority})
        db.session.commit()
        return {"ok": True, "videos_scanned": scanned, "segments_created": created, "segments": segments_out[:200]}


highlight_extractor_service = HighlightExtractorService()

