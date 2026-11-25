#!/usr/bin/env python3
"""B2 (the owner, 08:38 ET Nov 25): what each paid call of build 172 CAN bill, from the code and the recorded replies
only (no vendor asked). Read only; prints a report (and --json writes nothing: it prints JSON).

  1. Does the output limit a call is sent bound what the vendor bills? For every paid back-end: the limit it is sent
     (max_out of the role's max_tokens), the largest output (reasoning included) on record, and how many replies passed
     their limit. xAI's reasoning tokens are billed as output and are NOT inside max_tokens (chat) or max_output_tokens
     (Responses): recorded replies pass them. No other parameter that caps them is in the code.
  2. Per role and back-end: the current limit, the largest recorded use, the bound this branch enforces.
  3. One package (package.completion_reserve, heimdall_first, ceiling mode): at today's reservations; at full list
     price (no calibrated fraction); and at each call's largest recorded usage priced at full list.
  4. The worst single overshoot of ONE call in flight (B2's one-at-a-time): the largest recorded usage of its back-end
     at full list price, its input at the enforced input bound, minus the smallest reservation that back-end gets.
Usage: python3 -B tests/package/lean/exposure_172.py [--json]"""
import glob
import json
import os
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.realpath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(REPO, "pipeline"), os.path.join(REPO, "tests", "package")]
import providers as P  # noqa: E402

REPLIES = os.path.join(REPO, "tests", "package", "fixtures", "replies")
CAP_SINCE = "2026-11-16T16:57:16Z"       # ruling 121 (1) live (1045fb30e): xAI sent at most 12,000 output tokens
OUTSIDE = "/home/ultron/protocol_pulse/data/spend/integrator_outside.jsonl"     # read only: the sign-off's raw usage
SIGNOFF_MAX_TOKENS = 500                 # lean-release pipeline/signoff.py: "max_tokens": 500 (grok-3-mini)


def recordings():
    out = []
    for f in glob.glob(os.path.join(REPLIES, "*", "*.json")):
        with open(f) as fo:
            r = json.load(fo)
        r["_file"] = f
        out.append(r)
    return out


def added_at(f):
    """When a recording entered git (its recorded_at when it has one)."""
    r = subprocess.run(["git", "-C", REPO, "log", "--diff-filter=A", "--format=%cI", "--", os.path.relpath(f, REPO)],
                       capture_output=True, text=True, timeout=60).stdout.split()
    return r[-1] if r else "?"


def main(argv):
    import tempfile
    tmp = tempfile.mkdtemp(prefix="exposure_172_")
    led = os.path.join(tmp, "SPEND.json")          # an empty ledger of its own: the reservations' fractions apply
    router = P.Router(spend_path=led, routing="heimdall_first", ceiling=True)
    rows = [r for r in recordings() if r.get("backend") in router.backends]
    paid = [r for r in rows if not router.backends[r["backend"]].free() and r["backend"].split(":")[0] != "heimdall"
            and not isinstance(router.backends[r["backend"]], P.STTBackend)]
    rep = {"limits": {}, "over_limit": [], "roles": [], "signoff": None}
    by_b = defaultdict(list)
    for r in paid:
        b = router.backends[r["backend"]]
        u = r.get("usage") or {}
        sent = b.max_out(int(r.get("max_tokens") or 0))
        by_b[r["backend"]].append((r, sent, int(u.get("out") or 0), int(u.get("in") or 0),
                                   float(u.get("usd_reported") or 0.0)))
    for name, xs in sorted(by_b.items()):
        over = [(x, s, o) for x, s, o, _, _ in xs if o > s]
        rep["limits"][name] = {"calls": len(xs), "largest_out": max(o for _, _, o, _, _ in xs),
                               "largest_in": max(i for _, _, _, i, _ in xs),
                               "largest_bill": round(max(u for *_, u in xs), 6), "over_their_limit": len(over),
                               "largest_over": max((round(o / s, 2) for _, s, o in over), default=None)}
        for x, s, o in over:
            at = x.get("recorded_at") or added_at(x["_file"])
            if name.startswith("xai:") and at < CAP_SINCE:
                continue                                  # before ruling 121 the limit was not 12,000: not evidence
            rep["over_limit"].append({"backend": name, "role": x["role"], "sent": s, "out": o, "at": at,
                                      "bill": (x.get("usage") or {}).get("usd_reported")})
    roles = defaultdict(list)
    for name, xs in by_b.items():
        for x, s, o, i, u in xs:
            roles[(x["role"], name, int(x.get("max_tokens") or 0))].append((s, o, i, u, len(str(x.get("prompt") or ""))))
    for (role, name, mt), xs in sorted(roles.items()):
        b = router.backends[name]
        bound = ("no output bound enforceable: xAI bills reasoning outside the limit (sec. 1)"
                 if name.startswith(("xai:", "xai_vision:")) else
                 "the limit stands: never reached on record; whether thinking counts inside it is not established "
                 "offline")
        rep["roles"].append({"role": role, "backend": name, "max_tokens": mt, "limit_sent": xs[0][0], "calls": len(xs),
                             "largest_out": max(o for _, o, _, _, _ in xs), "largest_in": max(i for _, _, i, _, _ in xs),
                             "largest_bill": round(max(u for _, _, _, u, _ in xs), 6),
                             "input_bound_bytes": P.INPUT_BOUND_BYTES, "output_bound": bound})
    try:
        with open(OUTSIDE) as f:
            for line in f:
                e = json.loads(line)
                if e.get("vendor") == "xai:grok-3-mini" and isinstance((e.get("units") or {}).get("total_tokens"), int):
                    un = e["units"]
                    rep["signoff"] = {"at": e["at"], "prompt": un["prompt_tokens"], "completion": un["completion_tokens"],
                                      "reasoning": un["total_tokens"] - un["prompt_tokens"] - un["completion_tokens"],
                                      "max_tokens": SIGNOFF_MAX_TOKENS, "bill": e.get("usd")}
    except (OSError, ValueError):
        pass
    # 3. one package, three ways
    import package as PK
    cr = PK.completion_reserve(router)
    full = P.Router(spend_path=led, routing="heimdall_first", ceiling=True)
    for b in full.backends.values():
        b.spec = dict(b.spec, reserve_list_fraction=None)
    cr_full = PK.completion_reserve(full)

    def recorded_max_at_list(name):
        b = router.backends[name]
        lim = rep["limits"].get(name)
        if not lim:
            return None
        n_img = 1 if isinstance(b, P.XAIVisionBackend) else 0
        tin = P.INPUT_BOUND_BYTES + 200 + P.IMAGE_TOKENS_UPPER * n_img
        return round(b.usd({"in": tin, "out": lim["largest_out"]}), 6)
    pkg_rec = []
    for part in cr["parts"]:
        name = part["backend"]
        each = recorded_max_at_list(name) if name in router.backends else None
        pkg_rec.append(dict(part, at_recorded_max_list=each if each is not None else part["usd_each"]))
    rep["package"] = {"segments": cr["segments"], "today": cr["usd"], "full_list": cr_full["usd"],
                      "recorded_max_at_list": round(sum(x["calls"] * x["at_recorded_max_list"] for x in pkg_rec), 4),
                      "parts": pkg_rec}
    # 4. the worst single overshoot of one call in flight: its input at the enforced bound (INPUT_BOUND_BYTES; the
    #    worst content: 4-byte characters, so the reservation's characters / 3 counts the fewest tokens), up to
    #    IMAGE_BOUND[0] images, its output at the largest ever recorded for its back-end, at full list price; minus the
    #    reservation of that same call (its calibrated fraction, the smallest output limit it is sent)
    worst = []
    for name in sorted(rep["limits"]):
        b = router.backends[name]
        imgs = P.IMAGE_BOUND[0] if b.vision else 0
        tin = P.INPUT_BOUND_BYTES + 200 + P.IMAGE_TOKENS_UPPER * imgs
        top = round(b.usd({"in": tin, "out": rep["limits"][name]["largest_out"]}), 6)
        prompt = "\U0001F600" * (P.INPUT_BOUND_BYTES // 4)
        if b.vision:
            prompt = {"text": prompt, "images": ["x"] * imgs}
        frac = b.spec.get("reserve_list_fraction")
        held = b.upper_usd(prompt, 1)
        held = round(held * float(frac), 6) if frac else held
        worst.append({"backend": name, "max_at_list": top, "its_reservation": held,
                      "overshoot": round(max(0.0, top - held), 6), "fraction": frac})
    worst.append({"backend": "xai:grok-3-mini (the render's sign-off)", "max_at_list": None, "its_reservation": 0.05,
                  "overshoot": None, "note": "no list price in the code for grok-3-mini: its one bill $0.004013 "
                                             "(completion 143 + reasoning 1,279 tokens) is 12 x under its $0.05"})
    rep["worst"] = sorted(worst, key=lambda w: -(w["overshoot"] or 0.0))
    # 5. the exact constraint: the per-call cap R on an xAI call's output + reasoning (no such parameter is known) under
    #    which ONE package fits a HARD $1.50 at the code's list price: its xAI calls' input at their bound (the prompt
    #    the reserve counts, as bytes) + R output, plus its other calls at their reservations
    import visual_pin as VP
    def xai_part(part):
        b_ = router.backends.get(part["backend"] or "")
        return b_ if isinstance(b_, (P.XAIBackend, P.XAIVisionBackend)) else None
    fixed = sum(x["usd"] for x in cr["parts"] if xai_part(x) is None)
    per_in, n_x, out_price = 0.0, 0, None
    for x in cr["parts"]:
        b_ = xai_part(x)
        if b_ is None:
            continue
        if b_.vision:
            nb, imgs = len((VP.PROMPT + "x" * 1000).encode()), 1
        else:
            nb, imgs = PK.VERDICT_PROMPT_CHARS, 0
        per_in += x["calls"] * b_.usd({"in": nb + 200 + P.IMAGE_TOKENS_UPPER * imgs, "out": 0})
        n_x += x["calls"]
        out_price = b_.price[1]
    r_star = int((1.50 - fixed - per_in) / (n_x * out_price / 1e6)) if n_x else None
    rep["constraint"] = {"xai_calls_in_one_package": n_x, "their_input_usd": round(per_in, 4),
                         "other_calls_usd": round(fixed, 4), "out_price_per_1m": out_price,
                         "max_output_plus_reasoning_per_call_to_fit": r_star}
    import shutil
    shutil.rmtree(tmp, True)
    if "--json" in argv:
        print(json.dumps(rep, indent=1))
        return 0
    print("1. THE OUTPUT LIMIT AND WHAT IS BILLED (recorded replies)")
    for name, lim in rep["limits"].items():
        print(f"  {name}: {lim['calls']} calls; largest output (reasoning included) {lim['largest_out']}; "
              f"{lim['over_their_limit']} over the limit sent (largest x{lim['largest_over']}); largest bill "
              f"${lim['largest_bill']:.4f}")
    for x in rep["over_limit"]:
        print(f"    over its limit: {x['backend']} {x['role']}: sent {x['sent']}, used {x['out']} ({x['at']}), bill "
              f"{x['bill']}")
    if rep["signoff"]:
        s = rep["signoff"]
        print(f"  the sign-off (grok-3-mini, {s['at']}): max_tokens {s['max_tokens']}; completion {s['completion']} + "
              f"reasoning {s['reasoning']} = {s['completion'] + s['reasoning']} (prompt {s['prompt']}); ${s['bill']}")
    print("2. PER ROLE (limit sent | largest recorded output | largest input tokens | bound)")
    for r in rep["roles"]:
        print(f"  {r['role']} {r['backend']} max_tokens {r['max_tokens']}: sent {r['limit_sent']} | {r['largest_out']} | "
              f"{r['largest_in']} | input <= {r['input_bound_bytes']} bytes; {r['output_bound']}")
    pk = rep["package"]
    print(f"3. ONE PACKAGE ({pk['segments']} segments): today's reservations ${pk['today']:.4f}; full list "
          f"${pk['full_list']:.4f}; at each call's largest recorded usage, full list ${pk['recorded_max_at_list']:.4f}")
    for x in pk["parts"]:
        print(f"    {x['what']}: {x['calls']} x ${x['usd_each']:.4f} (today); x ${x['at_recorded_max_list']:.4f} "
              f"(recorded max at list)")
    c = rep["constraint"]
    print(f"5. THE EXACT CONSTRAINT: one package holds {c['xai_calls_in_one_package']} xAI calls (input ${c['their_input_usd']:.4f} "
          f"at list) + ${c['other_calls_usd']:.4f} of others; it fits a HARD $1.50 (at $0 carried in) only if each xAI call's "
          f"output + reasoning were capped at {c['max_output_plus_reasoning_per_call_to_fit']} tokens (${c['out_price_per_1m']}/M): "
          f"no such cap is in the code or the recordings")
    print("4. THE WORST SINGLE OVERSHOOT (one call in flight; input at its bound, output at the largest recorded, "
          "full list)")
    for w in rep["worst"]:
        print(f"  {w['backend']}: at most {w['max_at_list']} at list, its reservation {w['its_reservation']}, "
              f"overshoot {w['overshoot']}" + (f" ({w['note']})" if w.get("note") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
