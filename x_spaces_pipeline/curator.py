#!/usr/bin/env python3
"""x_spaces_pipeline/curator.py"""
import json, logging, sys, time
from pathlib import Path
from datetime import datetime
sys.path.insert(0, "/home/ultron/protocol_pulse")
from x_spaces_scraper.spaces_state import SpaceStateDB
import anthropic
logger = logging.getLogger("spaces.curator")
RAW_DIR    = Path("/home/ultron/protocol_pulse/video_pipeline_v3/data/spaces/raw")
MOMENT_DIR = Path("/home/ultron/protocol_pulse/video_pipeline_v3/data/spaces/moments")
MAX_AGE    = 21600
MAX_WORDS  = 6000
CALL_LOG   = Path("/home/ultron/protocol_pulse/data/curator_calls.json")
CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
MAX_DAILY  = 10
def get_daily_calls():
    today = datetime.now().strftime("%Y%m%d")
    try:
        d = json.loads(CALL_LOG.read_text())
        return d.get("count", 0) if d.get("date") == today else 0
    except Exception: return 0
def inc_calls():
    today = datetime.now().strftime("%Y%m%d")
    CALL_LOG.write_text(json.dumps({"date": today, "count": get_daily_calls()+1}))
def curate_pending():
    MOMENT_DIR.mkdir(parents=True, exist_ok=True)
    db = SpaceStateDB()
    if get_daily_calls() >= MAX_DAILY:
        logger.warning("Daily cap reached")
        return
    env = Path("/home/ultron/protocol_pulse/.env").read_text()
    api_key = next((l.split("=",1)[1].strip() for l in env.splitlines() if "ANTHROPIC_API_KEY" in l and not l.startswith("#")), None)
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not in .env")
        return
    client = anthropic.Anthropic(api_key=api_key)
    prompt = "Bitcoin editor. Extract top 3 moments. Return ONLY JSON no markdown: {"moments":[{"rank":1,"start_sec":0.0,"end_sec":0.0,"quote":"words","speaker":"unknown","signal_type":"macro","quality_score":80}]}"
    for tf in sorted(RAW_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        if time.time() - tf.stat().st_mtime > MAX_AGE: continue
        if tf.name.endswith(".meta.json"): continue
        try: transcript = json.loads(tf.read_text())
        except Exception: continue
        handle = transcript.get("handle", "unknown")
        space_id = transcript.get("space_id", "unknown")
        stem = tf.stem
        mf = MOMENT_DIR / f"{stem}_moments.json"
        if mf.exists(): continue
        text = transcript.get("text", "")
        if len(text.split()) < 100: continue
        if get_daily_calls() >= MAX_DAILY: break
        truncated = " ".join(text.split()[:MAX_WORDS])
        try:
            resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=1000, messages=[{"role":"user","content": prompt+"

"+truncated}])
            inc_calls()
            data = json.loads(resp.content[0].text.strip())
            data["handle"] = handle
            data["space_id"] = space_id
            data["stem"] = stem
            data["transcript_file"] = str(tf)
            tmp = mf.with_suffix(".tmp.json")
            tmp.write_text(json.dumps(data, indent=2))
            tmp.rename(mf)
            db.upsert(space_id, summarized_at=datetime.now().isoformat())
            logger.info(f"@{handle}: {len(data.get('moments',[]))} moments")
        except Exception as e:
            logger.error(f"@{handle}: {e}")
            db.upsert(space_id, error=str(e)[:200])
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    curate_pending()
