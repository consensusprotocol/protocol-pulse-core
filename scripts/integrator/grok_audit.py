"""Cycle-2 audit reviewer on xAI Grok (orchestrator 21:10: the audit law's reviewers include Grok; the xAI key is fenced
to the pipeline and LLM audits). Sends EXACTLY the messages Heimdall sent its panel (read from a raw_c1_*.json request),
writes the raw answer next to Heimdall's, prints the verdict and the vendor-reported cost. The key is read by name from
the repo's environment file and never printed.
Usage: python3 grok_audit.py <raw_c1_qwen27b.json> <out.json> [model]"""
import json
import sys
import time
import urllib.request

src, out = sys.argv[1], sys.argv[2]
model = sys.argv[3] if len(sys.argv) > 3 else "grok-4-0709"
with open(src) as f:
    req = json.load(f)["request"]
sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
from relay import get_key  # noqa: E402  (the pipeline's key loader, as pipeline/signoff.py: read by name, never printed)
key = get_key("XAI_API_KEY_MEDLEY")
body = {"model": model, "messages": req["messages"], "temperature": 0, "max_tokens": 8192}
t = time.time()
r = urllib.request.Request("https://api.x.ai/v1/chat/completions", data=json.dumps(body).encode(),
                           headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
with urllib.request.urlopen(r, timeout=175) as resp:
    data = json.loads(resp.read().decode())
lat = round(time.time() - t, 1)
content = data["choices"][0]["message"]["content"]
ticks = (data.get("usage") or {}).get("cost_in_usd_ticks")
rec = {"model": "xai:" + model, "latency_s": lat, "request": body, "response": data,
       "cost_usd_vendor": (ticks / 1e10) if isinstance(ticks, (int, float)) else None}
with open(out, "w") as f:
    json.dump(rec, f, indent=1)
print(f"{model}: {lat} s, vendor cost {rec['cost_usd_vendor']}")
print(content[:4000])
