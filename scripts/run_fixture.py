"""Exit test for Layer 3.5. Runs a regression fixture through auditor + external verifier
with NO out-of-pipeline research. Prints per-claim results and the POST/NO_POST decision."""
import sys, json, time, os
sys.path.insert(0, os.path.expanduser("~/protocol_pulse"))
from dotenv import load_dotenv; load_dotenv(os.path.expanduser("~/protocol_pulse/.env"))
import services.story_engine as se
import services.claim_verifier as cv

FIX = sys.argv[1] if len(sys.argv) > 1 else "trump_usd1_toll_booth_thread"
base = os.path.expanduser("~/protocol_pulse/data/intelligence/regression_fixtures/")
meta = json.load(open(base + FIX + ".json"))
text = open(base + FIX + ".txt").read().strip()

item = {"title": text.split(".")[0][:200], "summary": text, "url": "https://x.com/unknown/status/0",
        "source_domain": "x.com", "published_ts": time.time() - 3600, "discovered_ts": time.time(),
        "origin": "fixture", "domain_tag": "macro", "_signals": {"source_quality": 0.6, "recency": 0.9}}
t0 = time.time()
se.adversarial_verify(item)
print("AUDITOR status:", item["verification_status"], "| eligible:", item["writer_eligible"],
      "| facts:", len(item.get("facts") or []))
cv.apply(item, text=text)
ev = item["external_verification"]
print("\nEXTERNAL VERIFICATION  overall:", ev["overall"], "| fresh:", ev["fresh"],
      "| verified/stale/contradicted/unverifiable:", ev["n_verified"], ev["n_stale"], ev["n_contradicted"], ev["n_unverifiable"],
      "| cost $%.3f | %.0fs" % (ev["cost_usd"], time.time() - t0))
if item.get("event_age_hours") is not None: print("underlying event age: %.0fh" % item["event_age_hours"])
print("\nPER-CLAIM:")
for r in ev["claims"]:
    line = f"  [{r['result']:13s}] ({r['type']}) {r['claim'][:90]}"
    if r.get("candidate_value") is not None and r.get("observed_value") is not None:
        line += f"\n{'':19s}claimed {r.get('candidate_value')} | observed {str(r.get('observed_value'))[:70]}"
    if r.get("original_date"): line += f"\n{'':19s}original_date {r['original_date']}" + (f" | latest {r['latest_date']}" if r.get("latest_date") else "")
    if r.get("note"): line += f"\n{'':19s}note: {r['note']}"
    if r.get("source_url"): line += f"\n{'':19s}{r['source_url'][:100]}"
    print(line)
decision = "POST-ELIGIBLE" if item["writer_eligible"] else "NO_POST"
print("\nDECISION:", decision, "| status:", item["verification_status"])
print("EXPECTED:", meta["expected_outcome"])
print("PASS" if (decision == "NO_POST") == (meta["expected_outcome"] == "NO_POST") else "FAIL")
json.dump(item, open(f"/tmp/fixture_result_{FIX}.json", "w"), indent=2, default=str)
