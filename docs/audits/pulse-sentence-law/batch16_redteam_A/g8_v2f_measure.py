"""Claude-gates #5: does the approved v2f reference pass G8 through the production entry point? Read-only on the
reference; outputs to this scratch dir. Same source-clip wiring as run_fresh.stage_gates (16:9: qa/final_<clip>,
9:16: qa/vert_<clip>)."""
import json, os, sys
REPO = "/home/ultron/protocol_pulse"
sys.path.insert(0, os.path.join(REPO, "segment_v1"))
import qa_gates as Q
ref = os.path.join(REPO, "references", "v2f_2026-11-06", "run")
out = os.path.dirname(os.path.abspath(__file__))
res = {}
for fmt, final, pre in (("16x9", "segment.mp4", "final_"), ("9x16", "segment_vertical.mp4", "vert_")):
    segs = json.load(open(os.path.join(ref, "qa", f"concat_manifest_{fmt}.json")))["segments"]
    src = {s["label"]: os.path.join(ref, "qa", f"{pre}{s['label']}.mp4") for s in segs if s.get("type") == "talking_head"}
    finals = [f for f in os.listdir(os.path.join(ref, "out")) if f.endswith(".mp4")]
    path = os.path.join(ref, "out", final) if final in finals else None
    if path is None:
        cand = [f for f in finals if ("vert" in f) == (fmt == "9x16")]
        path = os.path.join(ref, "out", sorted(cand)[0])
    d = os.path.join(out, fmt)
    os.makedirs(d, exist_ok=True)
    ok, table = Q.gate_g8(path, segs, d, source_clips=src, fmt=fmt)
    res[fmt] = {"final": os.path.relpath(path, REPO), "pass": ok, "floor": Q.G8_SHARPNESS_FLOOR, "table": table}
json.dump(res, open(os.path.join(out, "g8_v2f.json"), "w"), indent=1, default=str)
for fmt, r in res.items():
    print(fmt, r["final"], "PASS" if r["pass"] else "FAIL", "floor", r["floor"])
    for row in r["table"]:
        print("   ", {k: row.get(k) for k in ("segment", "median", "ratio", "pass", "reason", "src_median", "soft_source")})
