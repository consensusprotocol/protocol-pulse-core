"""RULING 132's 'service down' guard on the builder's side (the scorer outage of 15:26 ET Nov 16 to 09:46 ET Nov 17 went
unseen for 18 h): prints SCORER STALE when the stand-alone scorer has candidates of mine waiting unscored (no verdict
with the same text_sha256 in its verdicts file) and its last rating is over an hour old; prints nothing otherwise.
Read only. Usage: python3 -B scorer_stale.py"""
import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
C = os.path.join(REPO, "docs/audits/parallel/pp-selectid_SCORER_CANDIDATES.json")
V = "/home/ultron/protocol_pulse/data/stand_alone_scorer/verdicts/latest.json"
try:
    c, v = json.load(open(C)), json.load(open(V))
    done = {x.get("text_sha256") for x in (v.get("verdicts") or {}).values() if isinstance(x, dict)}
    cands = [x for x in c.get("candidates") or [] if isinstance(x, dict)]
    waiting = [x for x in cands if x.get("text_sha256") not in done]
    rated = datetime.fromisoformat(str(v.get("rated_at")).replace("Z", "+00:00"))
    age_h = (datetime.now(timezone.utc) - rated).total_seconds() / 3600
    if waiting and age_h > 1.0:
        print(f"SCORER STALE: {len(waiting)} of {len(cands)} candidate(s) wait unscored; the scorer's last rating "
              f"{rated.astimezone(ZoneInfo('America/New_York')):%H:%M ET %b %d} ({age_h:.1f} h ago).")
except (OSError, ValueError, TypeError, AttributeError) as e:
    print(f"SCORER UNREADABLE ({type(e).__name__}): the stale check could not run.")
