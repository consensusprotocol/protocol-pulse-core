"""
review_queue.py — human review queue for the social engine shadow run.
Queue:     data/intelligence/review_queue.json          (dict story_id -> record)
Decisions: data/intelligence/review_decisions.jsonl     (append-only; THE dataset)

Decision record: story_id, action (POST|EDIT|KILL), kill_reason, story_grade, copy_grade,
machine_text, final_text, register, decided_at, seconds_in_queue.
Nothing here posts. POSTING_PAUSED is untouched.
"""
import json, time, os
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(os.path.expanduser("~/protocol_pulse"))
QUEUE = BASE / "data" / "intelligence" / "review_queue.json"
DECISIONS = BASE / "data" / "intelligence" / "review_decisions.jsonl"

KILL_REASONS = ["BORING", "STALE", "COMMODITY_NEWS", "WEAK_INSIGHT", "TRY_HARD", "AI_VOICE",
                "BAD_HOOK", "WRONG_TOPIC", "UNSUPPORTED", "ALREADY_EVERYWHERE", "OTHER"]
GRADES = ["FIRE", "MEH", "NO"]

def load_queue():
    if not QUEUE.exists(): return {}
    try: return json.load(open(QUEUE))
    except Exception: return {}

def save_queue(q):
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    tmp = QUEUE.with_suffix(".tmp"); json.dump(q, open(tmp, "w"), indent=1, default=str); os.replace(tmp, QUEUE)

def seen_ids():
    ids = set(load_queue().keys())
    if DECISIONS.exists():
        for line in open(DECISIONS):
            try: ids.add(json.loads(line)["story_id"])
            except Exception: pass
    return ids

def enqueue(records):
    """Add writer records (from writer_test.write_story). Returns number newly queued."""
    q = load_queue(); seen = seen_ids(); n = 0
    for r in records:
        sid = r.get("story_id")
        if not sid or sid in seen: continue
        r["status"] = "pending"; r["queued_at"] = time.time()
        q[sid] = r; n += 1
    save_queue(q); return n

def pending():
    return sorted([r for r in load_queue().values() if r.get("status") == "pending"],
                  key=lambda r: (-(r.get("postable_count") or 0), r.get("queued_at", 0)))

def decide(story_id, action, kill_reason=None, story_grade=None, copy_grade=None,
           final_text=None, register=None, note=None):
    q = load_queue(); r = q.get(story_id)
    if not r: return None
    action = action.upper()
    assert action in ("POST", "EDIT", "KILL")
    if kill_reason and kill_reason not in KILL_REASONS: kill_reason = "OTHER"
    machine_text = (r.get("variants") or {}).get(register) if register else r.get("proposed")
    d = {
        "story_id": story_id, "action": action, "kill_reason": kill_reason if action == "KILL" else None,
        "story_grade": story_grade, "copy_grade": copy_grade,
        "register": register or r.get("proposed_register"),
        "machine_text": machine_text, "final_text": (final_text if action in ("POST", "EDIT") else None),
        "edited": bool(action == "EDIT" and final_text and final_text.strip() != (machine_text or "").strip()),
        "note": note,
        "headline": r.get("headline"), "verification_status": r.get("verification_status"),
        "editorial_type": r.get("editorial_type"), "event_age_hours": r.get("event_age_hours"),
        "report_count": r.get("report_count"), "independent_corroboration": r.get("independent_corroboration"),
        "postable_count": r.get("postable_count"), "edge": r.get("edge"),
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "seconds_in_queue": round(time.time() - (r.get("queued_at") or time.time())),
    }
    DECISIONS.parent.mkdir(parents=True, exist_ok=True)
    with open(DECISIONS, "a") as f: f.write(json.dumps(d, default=str) + "\n")
    r["status"] = "decided"; r["decision"] = d; q[story_id] = r; save_queue(q)
    return d

def stats():
    rows = []
    if DECISIONS.exists():
        for line in open(DECISIONS):
            try: rows.append(json.loads(line))
            except Exception: pass
    n = len(rows)
    approved = [r for r in rows if r["action"] in ("POST", "EDIT")]
    from collections import Counter
    return {
        "decided": n, "pending": len(pending()),
        "approved": len(approved), "approval_rate": (round(len(approved) / n, 2) if n else None),
        "edited": sum(1 for r in approved if r.get("edited")),
        "kill_reasons": dict(Counter(r["kill_reason"] for r in rows if r["action"] == "KILL")),
        "story_grades": dict(Counter(r.get("story_grade") for r in rows if r.get("story_grade"))),
        "copy_grades": dict(Counter(r.get("copy_grade") for r in rows if r.get("copy_grade"))),
        "great_story_bad_copy": sum(1 for r in rows if r.get("story_grade") == "FIRE" and r.get("copy_grade") == "NO"),
        "great_copy_bad_story": sum(1 for r in rows if r.get("copy_grade") == "FIRE" and r.get("story_grade") == "NO"),
        "recent": rows[-10:][::-1],
    }
