"""Item 3: the out-edge QUESTION on the one must-fail fixture EDGE_OUT passes (Digital Asset News ad47eab4, 'Let me
read that again.'), asked the build's way (out_edge.ask: its own window record, the 2 sentences before, the 3 after, the
render's model qwen@low) with the reply RECORDED (Router record_dir) so a test replays it frozen."""
import json, os, sys
from datetime import datetime, timezone
W, OUT = sys.argv[1], sys.argv[2]
REPLAY = len(sys.argv) > 3 and sys.argv[3] == "replay"
sys.path[:0] = [os.path.join(W, "pipeline"), os.path.join(W, "tests/package")]
import eligibility as E
import ledger_build as LB
import out_edge as OE
import proof_ly as PL
import providers as P
inp = json.load(open(os.path.join(W, "tests/package/proof/ledger_20261124_004415/inputs.json")))
m = next(x for x in inp["moments"] if x["moment_id"] == "ad47eab4a19c2324a9eb")
key = m["source_key"].split("@")[1]                     # the window this build cut the moment from
wp = next(v for v in LB.word_pass_index()[0].values()
          if v.get("video_id") == m["video_id"] and f"/windows/{key}." in str(v.get("window_record")))
src, path, why = LB.window_source(m, wp, E.Context(datetime.now(timezone.utc), {}))
assert src is not None, why
print("window record:", os.path.relpath(path, LB.STORE), "sha", wp["record_sha256"][:12])
before, nxt, ks = OE.around(m, src)
print(json.dumps({"clip": m["text"], "before": before, "next": nxt, "ks": ks}, indent=1))
r = P.Router(chains=PL.chains("heimdall_first"), routing="heimdall_first", record_dir=OUT, replay=REPLAY)
v = OE.ask(r, m, src, {})
print(json.dumps({k: v.get(k) for k in ("complete", "finishes_at", "why", "backend", "measured", "version", "sha256")},
                 indent=1))
