#!/usr/bin/env python3
"""Builds adjacent_reaction_fixture.json (D4, PBX 2026-11-09 01:34) from REAL records only:
runs/fresh_20261107_080503/TOPIC_SELECTION.json (Binance candidate query + counted verdicts) and the
immutable whisper_words transcripts in data/editorial/transcripts/. Nothing is edited: each case keeps
the real word timestamps of every sentence within 60 s of the verified anchor."""
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import editorial_select as es  # noqa: E402
import transcript_store as ts  # noqa: E402

RUN = os.path.join(REPO, "runs", "fresh_20261107_080503", "TOPIC_SELECTION.json")
CASES = {  # video_id -> what the case is for (D4 tests)
    "9La50F_lmd0": "positive candidate: Binance anchor + host reaction 'That's like a pittance ... chump change.'",
    "L9tzgg6PXi8": "negative 2: neighbours are market commentary / another item with no backward reference",
    "y0SjcqQPdpA": "negative 3: 'that CFDC perp story' refers back lexically but is a different news item",
}


def main():
    sel = json.load(open(RUN))
    cand = next(c for c in sel["candidates"] if c["headline"].startswith("Elliptic says Binance"))
    out = {"source_run": "runs/fresh_20261107_080503", "topic_selection_sha256":
           hashlib.sha256(open(RUN, "rb").read()).hexdigest(), "candidate": cand["headline"],
           "query": cand["query"], "cases": {}}
    for v in cand["coverage"]["verdicts"]:
        if v["video_id"] not in CASES or not v["counted_as_same_event"]:
            continue
        p = os.path.join(REPO, "data", "editorial", "transcripts", v["video_id"], "transcript.whisper_words.json")
        rec = json.load(open(p))
        ws = rec["words"]
        spans = [ts.parse_chunk_id(x)[1:] for x in v["supporting_chunk_ids"]]
        anc = es.align_quote(v["evidence_quote"], ws, max(0, min(a for a, _ in spans) - 30),
                             max(b for _, b in spans) + 30)
        lo, hi = anc["start"] - 60, anc["end"] + 60
        out["cases"][v["video_id"]] = {
            "purpose": CASES[v["video_id"]], "channel": v["channel"], "evidence_quote": v["evidence_quote"],
            "verdict": v["verdict"], "support": v["support"], "supporting_chunk_ids": v["supporting_chunk_ids"],
            "transcript_sha256": rec["transcript_sha256"], "transcript_method": rec["transcript_method"],
            "transcript_model": rec["transcript_model"],
            "words": [w for w in ws if lo <= w["start"] <= hi]}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adjacent_reaction_fixture.json")
    json.dump(out, open(path, "w"), indent=1)
    print(path, {k: len(c["words"]) for k, c in out["cases"].items()})


if __name__ == "__main__":
    main()
