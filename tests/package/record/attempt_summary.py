"""ORDER 17:50 ET Nov 16 (4): 'Line 1 after each attempt: what was tried, what stopped it, dollars.' From one build
record (its package.json and inputs.json, read only): the --only set, what stopped it (why_none, or each angle tried
and why), the story rows, the visual checks, and whether a pin was written (with its seal). Usage: attempt_summary.py DIR"""
import json
import os
import sys


def main(d):
    nn = os.path.join(d, "NOTHING_NEW.json")
    if not os.path.exists(os.path.join(d, "package.json")) and os.path.exists(nn):   # RULING 152 (3): a NOTHING NEW
        r = json.load(open(nn))                       # build writes no package.json (build 153's line read a traceback)
        same = r.get("same_as") or r.get("build") or r.get("of") or "an earlier build"
        print(f"NOTHING NEW (ruling 107 (1)): the inputs are {os.path.basename(str(same))}'s (fingerprint "
              f"{str(r.get('fingerprint'))[:12]}), which left nothing undone: no model was asked, $0.00")
        return
    if not os.path.exists(os.path.join(d, "package.json")):   # the verifier's row 12 (Nov 23): a STOPPED build (156,
        print("no build record: the build stopped before writing package.json (its log says why); nothing sealed")
        return                                                # 20:28) printed the same FileNotFoundError
    pk = json.load(open(os.path.join(d, "package.json")))
    inp = json.load(open(os.path.join(d, "inputs.json"))) if os.path.exists(os.path.join(d, "inputs.json")) else {}
    only = (inp.get("inputs") or {}).get("only")
    parts = []
    if only:
        parts.append(f"the set: {only['kept']} of {only['asked']} moments in the pool"
                     + (f" (not in it: {len(only['missing'])})" if only.get("missing") else ""))
    st = pk.get("stories")
    if isinstance(st, dict):
        rows = [f"{r.get('story_id', '?')[:12]} in pool {r.get('in_pool')}, cleared {r.get('cleared')}"
                for r in st.get("matched") or []]
        if rows:
            parts.append("stories: " + "; ".join(rows))
    tried = pk.get("tried") or []
    if tried:
        parts.append(f"{len(tried)} angle(s) tried: " + "; ".join(
            f"[{t.get('angle')}] {str(t.get('why') or 'line-up ' + str(bool(t.get('lineup'))))[:110]}" for t in tried[:4]))
    if pk.get("why_none"):
        parts.append("stopped by: " + str(pk["why_none"])[:260])
    v = pk.get("visual") or {}
    parts.append(f"the clean pass's vision checks: {v.get('calls', 0)} paid, {v.get('cached', 0)} cached, ${v.get('usd_reported', 0.0):.3f} "
                 f"reported")
    for name in ("MOMENTS_PIN_LEDGER.json", "SPOTLIGHT_PIN.json"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            pin = json.load(open(p))
            parts.append(f"PIN WRITTEN: {name}, story_id {pin.get('story_id')}")
    print(" | ".join(parts))


if __name__ == "__main__":
    main(sys.argv[1])
