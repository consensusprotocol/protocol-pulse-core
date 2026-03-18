"""
TOMBSTONED 2026-03-18
This file is part of the deprecated x_spaces_pipeline/ live-capture system.
It has been superseded by x_spaces_scraper/run_scraper.py which is the
single authoritative pipeline. SpaceStateDB is the authoritative state store.
DO NOT USE — DO NOT IMPORT — DO NOT EXECUTE
Live capture capability will be reintegrated as a clean stage in run_scraper.py.
"""
#!/usr/bin/env python3
"""x_spaces_pipeline/transcriber.py"""
import json, logging, sys, time
from pathlib import Path
from datetime import datetime
sys.path.insert(0, "/home/ultron/protocol_pulse")
from x_spaces_scraper.whisper_worker import WhisperWorker
from x_spaces_scraper.spaces_state import SpaceStateDB
logger = logging.getLogger("spaces.transcriber")
RAW_DIR = Path("/home/ultron/protocol_pulse/video_pipeline_v3/data/spaces/raw")
MAX_AGE = 86400
def transcribe_pending():
    db = SpaceStateDB()
    worker = WhisperWorker.get()
    if not worker.model:
        logger.error("WhisperWorker unavailable")
        return
    for meta_file in sorted(RAW_DIR.glob("*.meta.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        if time.time() - meta_file.stat().st_mtime > MAX_AGE:
            continue
        try: meta = json.loads(meta_file.read_text())
        except Exception: continue
        stem = meta_file.name.replace(".meta.json", "")
        audio_file = RAW_DIR / f"{stem}.m4a"
        transcript_file = RAW_DIR / f"{stem}.json"
        if transcript_file.exists(): continue
        if not audio_file.exists(): continue
        handle   = meta.get("handle", "unknown")
        space_id = meta.get("space_id", "unknown")
        result = worker.transcribe(str(audio_file))
        word_count = result.get("word_count", 0)
        if word_count < 50:
            db.upsert(space_id, error=f"too_short_{word_count}")
            continue
        result["handle"]   = handle
        result["space_id"] = space_id
        result["meta"]     = meta
        tmp = transcript_file.with_suffix(".tmp.json")
        tmp.write_text(json.dumps(result, indent=2))
        tmp.rename(transcript_file)
        db.upsert(space_id, transcribed_at=datetime.now().isoformat(), transcript_word_count=word_count)
        logger.info(f"Transcribed @{handle}: {word_count} words")
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    transcribe_pending()
