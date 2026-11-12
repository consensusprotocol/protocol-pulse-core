#!/usr/bin/env python3
"""pipeline/story_ledger.py — DEC-9: every fresh (auto-mode) story delivered to the approval chat is recorded
once, by its counted evidence statements; the next auto run never selects an event that rests on one of them.

Identity is the same as the same-event merge (editorial_select._same_statement): the same video, a shared
supporting chunk and a shared run of words in the evidence quotes. A headline match is never used (the story
engine rewords one event many ways, Nov 10). Ledger: data/pulse_check/story_ledger.jsonl (append-only)."""
import json
import os
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(REPO, "data", "pulse_check", "story_ledger.jsonl")


def entries(path=None):
    path = path or LEDGER                 # read at call time (a default arg would freeze it)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def delivered_match(candidate, ledger):
    """The ledger entry whose evidence shares a statement with this candidate's counted evidence, or None."""
    import editorial_select as es
    ev = es._evidence(candidate)
    for e in ledger:
        for vid, chunks, quote in ((x["video_id"], set(x["chunk_ids"]), x["quote_tokens"]) for x in e["evidence"]):
            if any(vid == v and chunks & c and es._same_statement(quote, q) for v, c, q in ev):
                return e
    return None


def record(run_dir, path=None):
    """Append the delivered run's selected story (auto mode only). Idempotent per run directory."""
    path = path or LEDGER
    with open(os.path.join(run_dir, "TOPIC_SELECTION.json")) as f:
        sel = json.load(f)["selected"]
    run_id = os.path.basename(os.path.normpath(run_dir))
    if any(e["run"] == run_id for e in entries(path)):
        return None
    if not sel.get("evidence"):
        raise ValueError(f"{run_id}: selected story carries no counted evidence; nothing identifies it")
    e = {"run": run_id, "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "headline": sel.get("headline"), "short_label": sel.get("short_label"),
         "underlying_event": sel.get("underlying_event"), "evidence": sel["evidence"]}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(e) + "\n")
    return e


def record_if_approved(run_dir, delivery, mode, path=None):
    """Called by scripts/pulse_check_run.sh after a delivery: an AUTO run whose drop was authorised
    (release_auth) and completed, with BOTH finals captioned telegram.HOLD_OK, is recorded; anything else
    (pinned, an option, a partial drop) is not, so a story held for a defect is free to be produced again once
    the defect is fixed."""
    import telegram
    finals = [m for m in delivery["messages"] if "format" in m]
    if mode != "auto" or delivery.get("option") or len(finals) != 2 or delivery.get("authorised") is not True or \
            delivery.get("status") != "complete" or not all(m["caption"].startswith(telegram.HOLD_OK) for m in finals):
        return None
    return record(run_dir, path)


if __name__ == "__main__":
    import sys
    print(json.dumps(record(sys.argv[1]), indent=1))
