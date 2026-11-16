#!/usr/bin/env python3
"""Ruling 119 (1), after the run: add production's earlier verdicts on the same texts (the scorer service's results
store, matched by the text's sha256 prefix) to each clip, and print the per-clip table.
Usage: python3 -B ruling119_finish.py RUN.json OUT.json"""
import glob
import json
import os
import sys

STORE = "/home/ultron/protocol_pulse/data/stand_alone_scorer/results"


def earlier(text_sha256):
    out = []
    for f in sorted(glob.glob(os.path.join(STORE, f"*.{text_sha256[:16]}.*.json"))):
        with open(f) as fh:
            for e in json.load(fh):
                kind = e.get("kind") or "story"
                out.append({"file": os.path.basename(f), "kind": kind,
                            "prompt": "ALONE_PROMPT (this bar)" if kind == "moments"
                            else "the story prompt, with the video's event (not this bar)",
                            "event": e.get("event"), "duration": e.get("duration"), "score": e.get("score"),
                            "fault": e.get("fault"), "affirmed": e.get("affirmed"),
                            "scorer_sha": (e.get("scorer_sha") or "")[:12], "at_utc": e.get("at")})
    return out


def main(src, dst):
    with open(src) as f:
        doc = json.load(f)
    for v in doc["videos"]:
        for c in v["clips"]:
            c["earlier_production_verdicts"] = earlier(c["text_sha256"])
    doc["earlier_production_verdicts_note"] = (
        "from data/stand_alone_scorer/results, matched by the text's sha256: kind 'story' entries were asked the story "
        "prompt with the video's event (scorer f19aab6cc5cc, Nov 13) and are not this bar; kind 'moments' entries are")
    tmp = dst + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1)
    os.replace(tmp, dst)
    print(f"{'video':9} {'role':9} {'channel':20} {'pin shape':28} {'alone shape':28} cached  earlier(moments)")
    for v in doc["videos"]:
        for c in v["clips"]:
            def cell(shape):
                a = c["askings"][shape]
                return " ".join(f"{x['score']}{'' if x['affirmed'] else '✗'}/{(x['fault'] or 'ERR')[:5]}" for x in a)
            ca = c["cached"].get("alone") or c["cached"].get("pin")
            em = [e for e in c["earlier_production_verdicts"] if e["kind"] == "moments"]
            print(f"{c['video']:9} {c['role']:9} {c['channel'][:20]:20} {cell('pin'):28} {cell('alone'):28} "
                  f"{(str(ca['score']) + '/' + ca['fault'][:5]) if ca else '-':8} "
                  f"{', '.join(str(e['score']) for e in em) or '-'}")
    print(json.dumps(doc["summary"], indent=1) if doc.get("summary") else "no summary (the run did not finish)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
