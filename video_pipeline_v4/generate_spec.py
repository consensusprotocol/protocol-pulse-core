#!/usr/bin/env python3
"""
Generate episode_spec.json from data/signals.json for V4 Remotion pipeline.
Outputs: video_pipeline_v4/episode_spec.json
"""
import json
from datetime import datetime, timezone
from pathlib import Path

SIGNALS_PATH = Path(__file__).parent.parent / "data" / "signals.json"
OUTPUT_PATH = Path(__file__).parent / "episode_spec.json"

FPS = 30

SEGMENTS = [
    {"id": "cold_open", "label": "Cold Open", "duration_sec": 4},
    {"id": "narration", "label": "Market Narration", "duration_sec": 20},
    {"id": "intelligence", "label": "Intelligence Brief", "duration_sec": 30},
    {"id": "pip", "label": "Picture-in-Picture Analysis", "duration_sec": 45},
    {"id": "outro", "label": "Outro", "duration_sec": 15},
]


def generate():
    signals = json.loads(SIGNALS_PATH.read_text())
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    btc_price = signals.get("btc_price", {})
    fear_greed = signals.get("fear_greed", {})
    hashrate = signals.get("hashrate", {})
    difficulty = signals.get("difficulty_adjustment", {})
    signal_score = signals.get("signal_score", {})

    total_frames = sum(s["duration_sec"] * FPS for s in SEGMENTS)

    spec = {
        "date": today,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fps": FPS,
        "total_duration_sec": sum(s["duration_sec"] for s in SEGMENTS),
        "total_frames": total_frames,
        "signals": {
            "btc_price": btc_price.get("value"),
            "btc_change_24h": btc_price.get("change_24h"),
            "fear_greed_value": fear_greed.get("value"),
            "fear_greed_label": fear_greed.get("label"),
            "hashrate": hashrate.get("value"),
            "difficulty_pct": difficulty.get("percent"),
            "signal_score": signal_score,
        },
        "segments": [],
    }

    frame_offset = 0
    for seg in SEGMENTS:
        frames = seg["duration_sec"] * FPS
        spec["segments"].append({
            "id": seg["id"],
            "label": seg["label"],
            "duration_sec": seg["duration_sec"],
            "frames": frames,
            "from_frame": frame_offset,
            "to_frame": frame_offset + frames,
        })
        frame_offset += frames

    OUTPUT_PATH.write_text(json.dumps(spec, indent=2))
    print(f"[generate_spec] Written {OUTPUT_PATH} ({spec['total_duration_sec']}s, {total_frames} frames)")
    return str(OUTPUT_PATH)


if __name__ == "__main__":
    generate()
