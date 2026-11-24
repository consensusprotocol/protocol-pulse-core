"""Item 1 (orchestrator 09:50 ET Nov 24): the exclusion checker's judgment on three REAL clips, asked the build's way
(package.ad_read_out -> ad_before_soft -> exclusion_for on each clip's own word record and context), the replies
RECORDED (Router record_dir; the in-house deepseek only: no paid call) so a test replays them frozen.
  ad47eab4 (Digital Asset News): a news read after 'link in the description' -> must PASS, judgment recorded;
  6e79ceaa (Natalie Brunell): the first line of The Bitcoin Way's BitKey read, no magic word -> must REFUSE;
  41e3bcce (Noq6txZU91c): 'no one has made it easier than our friends over at Bitkey' -> must REFUSE."""
import json, os, sys
from datetime import datetime, timezone
W, OUT = sys.argv[1], sys.argv[2]
REPLAY = len(sys.argv) > 3 and sys.argv[3] == "replay"
sys.path[:0] = [os.path.join(W, "pipeline"), os.path.join(W, "tests/package")]
import eligibility as E
import ledger_build as LB
import package as PK
import proof_ly as PL
import providers as P
CASES = (("ledger_20261124_004415", "ad47eab4a19c2324a9eb", "PASS"),
         ("ledger_20261117_152630", "6e79ceaa8e76", "REFUSE"),
         ("ledger_20261113_145246", "41e3bcce1a3a", "REFUSE"))
ctx = E.Context(datetime.now(timezone.utc), {})
ch = PL.chains("heimdall_first")
ch["exclusion_verdict"] = ["heimdall:google/gemma-4-31b-it", "heimdall:minimax/minimax-m3.1-flash"]   # in-house
#   only: ruling 96's deepseek gave no answer at 09:47 ET Nov 24; never qwen (the miner of these clips); never the
#   paid Grok under the freeze
r = P.Router(chains=ch, routing="heimdall_first", record_dir=OUT, replay=REPLAY)
out = []
for run, mid, want in CASES:
    inp = json.load(open(os.path.join(W, "tests/package/proof", run, "inputs.json")))
    m = next(x for x in inp["moments"] if x["moment_id"].startswith(mid))
    if m.get("source_key"):
        key = m["source_key"].split("@")[1]
        wp = next(v for v in LB.word_pass_index()[0].values()
                  if v.get("video_id") == m["video_id"] and f"/windows/{key}." in str(v.get("window_record")))
        src, path, why = LB.window_source(m, wp, ctx)
        if src is not None:                          # the build's way: the caption record it was mined from (L-s)
            import ast
            mined = ast.literal_eval(m["mined"]) if isinstance(m.get("mined"), str) else (m.get("mined") or {})
            lid = mined.get("ledger_moment_id")             # the ledger row it was mined from names its caption record
            ing = os.path.join(LB.INGEST_ROOT, "data", "editorial")
            rows = [json.loads(x) for x in open(os.path.join(ing, "moments", "moment_ledger.jsonl")) if lid in x]
            row_sha = next(r["transcript_sha256"] for r in rows if r.get("moment_id") == lid)
            src.context_source, cwhy = LB.caption_source(dict(m, transcript_sha256=row_sha), ctx, LB.STORE, ing)
            cap_path = cwhy if src.context_source is not None else None
            assert src.context_source is not None, (mid, cwhy)
    else:
        wp, cap_path = None, None
        src, path, why = LB.word_source(m, ctx)
    assert src is not None, (mid, why)
    sources = {(m.get("source_key") or m["video_id"]): src}
    ad_read = PK.ad_read_out([m], sources)
    soft = PK.ad_before_soft([m], ad_read, False)
    if m["moment_id"] in ad_read and m["moment_id"] not in soft:
        v = {"verdict": "exclude", "why": ad_read[m["moment_id"]], "backend": "deterministic", "measured": True}
    else:
        v = PK.exclusion_for(r, m, sources, {})
    got = "PASS" if v.get("verdict") == "keep" else "REFUSE" if v.get("measured") else "HELD (no answer)"
    row = {"caption_record": cap_path if m.get("source_key") else None,
           "moment": m["moment_id"], "video": m["video_id"], "span": [m["start"], m["end"]], "text": m["text"],
           "record": os.path.relpath(path, LB.STORE), "screen": ad_read.get(m["moment_id"]),
           "ad_before": m.get("ad_before"), "verdict": v.get("verdict"), "risks": v.get("risks"),
           "why": v.get("why"), "backend": v.get("backend"), "measured": v.get("measured"),
           "replayed": v.get("replayed"), "WANT": want, "GOT": got}
    out.append(dict(row, word_pass=wp, moment_record=m))
    print(json.dumps({k: row[k] for k in ("moment", "screen", "ad_before", "verdict", "risks", "why", "backend",
                                          "replayed", "WANT", "GOT")}))
json.dump(out, open(os.path.join(OUT, "CASES.json"), "w"), indent=1)
