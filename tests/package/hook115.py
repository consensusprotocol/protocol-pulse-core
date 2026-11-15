#!/usr/bin/env python3
"""RULING 115 (3) (orchestrator 13:24 ET Nov 15), THE PROPER FIX, REPORT BEFORE USE: "a new hook-question version
carrying the approved hooks as positive examples AND five clear negatives from the near-miss file (the mid-conversation
openers rated 2, e.g. "you know, it's still an asset"). It takes the job only when it rates all five approved at 4 or
more AND all five negatives at 3 or less, on Grok and separately on qwen (qwen wins the job back if it passes both and
agrees at ruling 85's bar)."

THE VERSION (prompt_v2): package.HOOKS_PROMPT unchanged (ruling 52's ONE hook question, the same contract) with ONE
block after its first paragraph: PBX's approved openers (positives: they opened videos he approved) and five
mid-conversation openers (negatives), each with its channel. The block names no rating for any example: it says what
PBX approved and why the negatives fail, and the question then asks for each part as before.
THE TEST, as ordered: each of the ten asked ALONE (package.hook_ratings, one moment a call, cache None) at production's
seed 7, on Grok and on qwen. A model passes when every approved hook's own-job rating (min(scroll, alone), ruling 61)
is >= 4 and every negative's is <= 3. The ten rated ARE the examples the prompt carries, so a pass may only show the
model copying its examples: the same ten are therefore also asked LEAVE-ONE-OUT (the rated item left out of the block),
reported beside it. Report only: nothing here is read by a build; the hook job keeps ruling 115 (1)'s question.
SPEND: its own ledger SPEND_H115.json, vendor-reported; no call starts at STOP_USD.
Usage: python3 -B tests/package/hook115.py [--models grok,qwen] [--report-only]"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import eligibility as E  # noqa: E402
import hook112 as H  # noqa: E402
import package as PK  # noqa: E402
import providers as P  # noqa: E402
import replay85 as R  # noqa: E402

WT = R.WT
OUT = os.path.join(WT, "tests", "package", "proof", "hook115")
SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_H115.json")
LIMIT_USD, STOP_USD, SEED = 0.50, 0.25, 7   # the router's ceiling is ruling 115's cap (it reserves each call's
#   list-price upper bound, so it sits above our own stop on reported spend; audit 1436 C1, qwen)
MODELS = {"grok": "xai:grok-4.20-0309-reasoning", "qwen": "heimdall:qwen/qwen3.8-27b"}
NEGATIVES = (("adf6d9c528a27963f790", "Scott Melker"), ("f5f005b9a91b80840778", "CoinTelegraph"),
             ("d7578b88ff8e0129064f", "CNBC Television"), ("2e77a0a7af2aab66a3a4", "The Bitcoin Layer"),
             ("994ca307911a9ee1eb79", "Simply Bitcoin"))
#   ruling 112's 48 h (FUNNEL / NEAR_MISSES' source, hook112.all_ratings): rated 2 as mid-conversation openers, one per
#   channel; adf6d9c5 is the order's own example ("you know, it's still an asset").
BLOCK = """HOW PBX JUDGES OPENERS (his own verdicts; these are examples, NOT candidates, and are not rated here):
OPENERS PBX APPROVED: each one opened a video he approved for publishing.
{pos}
OPENERS THAT FAIL: each starts mid-conversation, leaning on something said before it ("you know", "all that said",
"though", "here", "as I've said"), so a viewer who hears it first has missed what it answers.
{neg}
"""


def negatives(proof=None):
    """The five negatives as the hook job reads a moment: the text their rating was given on (hook112.all_ratings over
    the builds of ruling 112's window), the channel on screen; an id of their own ("neg-<id>"), so no cache answers."""
    recs = H.build_records(proof or H.PROOF, since="ledger_20261113_161500")
    ra = H.all_ratings(recs, {})
    out = []
    for mid, ch in NEGATIVES:
        hit = next(((rater, x) for (m, rater), x in sorted(ra.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))
                    if m == mid and H.own_rating(x) == 2 and x.get("text")), None)
        if hit is None:
            raise ValueError(f"negative {mid} has no rating of 2 with its text in the window")
        rater, r = hit
        out.append({"moment_id": f"neg-{mid[:8]}", "text": r["text"], "channel_id": f"neg:{mid}", "channel_name": ch,
                    "label": f"rated 2 by {rater}: {(r.get('why') or '')[:90]}"})
    return out


def example(m):
    t = " ".join(m["text"].split())
    return f'  - "{t}" ({m["channel_name"]})'


def prompt_v2(pos, neg, leave_out=None):
    """package.HOOKS_PROMPT with the examples block after its first paragraph (braces escaped for its .format)."""
    keep = lambda ms: [m for m in ms if m["moment_id"] != leave_out]
    block = BLOCK.format(pos="\n".join(example(m) for m in keep(pos)), neg="\n".join(example(m) for m in keep(neg)))
    head, sep, rest = PK.HOOKS_PROMPT.partition("\n\n")
    if not sep:
        raise ValueError("HOOKS_PROMPT has no first paragraph")
    return head + sep + block.replace("{", "{{").replace("}", "}}") + "\n" + rest


def build_router(model, spend_path=SPEND):
    r = P.Router(env_path=R.ENV, spend_path=spend_path, limit_usd=LIMIT_USD, limit_basis="reported",
                 routing="heimdall_first")
    r.chains["coherence_verdict:hook"] = [model]
    return r


def rate(router, m, prompt, ctx, rate_fn=None):
    """One moment, alone, on `prompt` -> its record or {"error"}. No cache: nothing is read or written."""
    rate_fn = rate_fn or PK.hook_ratings
    wv, wf = PK._writers(router)
    with mock.patch.object(PK, "HOOKS_PROMPT", prompt):
        got, err = rate_fn(router, [m], ctx, wv, wf, cache=None, seed=SEED)
    r = got.get(m["moment_id"])
    return dict(r, own=H.own_rating(r)) if r else {"error": err or "no rating"}


def verdict(rows, model=None):
    """{"passes", "approved", "negatives"}: every approved own-job rating >= 4 and every negative's <= 3. A rating the
    named model did not give counts as none (audit 1436 C1, glm: the report never credits another model)."""
    own = lambda r: r.get("own") if model is None or r.get("backend") == model else None
    a = [own(r) for r in rows if r["kind"] == "approved"]
    n = [own(r) for r in rows if r["kind"] == "negative"]
    ok = len(a) == 5 and len(n) == 5 and all(isinstance(x, int) and x >= 4 for x in a) and \
        all(isinstance(x, int) and x <= 3 for x in n)
    return {"passes": ok, "approved": a, "negatives": n}


def spent_reported(path=None):
    """The ledger's VENDOR-REPORTED total (its usd_reported line), never the price table's estimate."""
    path = path or SPEND
    if not os.path.exists(path):
        return 0.0
    with open(path) as f:
        return round(float(json.load(f).get("usd_reported") or 0.0), 6)


def run(models, now=None):
    """Every model, both variants, the ten each -> the result, also written to QUESTION_V2_TEST.json."""
    now = now or datetime.now(timezone.utc)
    ctx = E.Context(now, H.registry())
    pos, neg = [m for m in H.ref_moments() if "error" not in m], negatives()
    if len(pos) != 5:
        raise ValueError(f"{5 - len(pos)} approved hook(s) cannot be read")
    out = {"ruling": "115 (3), report before use", "at": now.isoformat(timespec="seconds"), "seed": SEED,
           "question_v2": prompt_v2(pos, neg), "models": {}}
    for key in models:
        r = build_router(MODELS[key])
        res = {}
        for variant in ("as ordered", "leave-one-out"):
            rows = []
            for kind, m in [("approved", x) for x in pos] + [("negative", x) for x in neg]:
                if r.spent() >= STOP_USD:
                    rows.append({"kind": kind, "moment_id": m["moment_id"], "error": f"stopped at ${r.spent():.4f}"})
                    continue
                pr = prompt_v2(pos, neg, leave_out=m["moment_id"] if variant == "leave-one-out" else None)
                rows.append(dict(rate(r, m, pr, ctx), kind=kind, moment_id=m["moment_id"],
                                 channel=m["channel_name"]))
                print(f"  {key} {variant} {m['moment_id']}: {rows[-1].get('own')} "
                      f"({rows[-1].get('scroll')}/{rows[-1].get('alone')}/{rows[-1].get('setup')}) "
                      f"{rows[-1].get('error') or ''}; ${r.spent():.4f}", flush=True)
            res[variant] = {"rows": rows, **verdict(rows, MODELS[key])}
        out["models"][MODELS[key]] = res
    out["spent_usd_reported"] = spent_reported()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "QUESTION_V2_TEST.json"), "w") as f:
        json.dump(out, f, indent=1)
    return out


def report(path=None):
    with open(path or os.path.join(OUT, "QUESTION_V2_TEST.json")) as f:
        d = json.load(f)
    L = ["# RULING 115 (3): THE HOOK QUESTION WITH PBX'S EXAMPLES (report before use)", "",
         f"Measured {d['at']} (UTC), seed {d['seed']}, each hook asked alone. A model takes the job only when every "
         "approved hook's own-job rating (min(scroll, alone)) is >= 4 AND every negative's is <= 3. The ten rated are "
         "the examples the question carries; LEAVE-ONE-OUT asks each with itself left out of the examples.", "",
         "| model | variant | approved (5) | negatives (5) | passes |", "|---|---|---|---|---|"]
    for model, res in d["models"].items():
        for variant, v in res.items():
            L.append(f"| {model} | {variant} | {v['approved']} | {v['negatives']} | {'YES' if v['passes'] else 'no'} |")
    L += ["", "Every rating (scroll / alone / setup, and the model's reason):", ""]
    for model, res in d["models"].items():
        for variant, v in res.items():
            for r in v["rows"]:
                L.append(f"- {model}, {variant}, {r['kind']} {r['moment_id']} ({r.get('channel')}): "
                         + (f"{r.get('own')} ({r.get('scroll')}/{r.get('alone')}/{r.get('setup')}) by "
                            f"{r.get('backend')}: {r.get('why')}" if "error" not in r else f"NO RATING: {r['error']}"))
    L += ["", f"Spent ${d['spent_usd_reported']:.4f} (vendor-reported, SPEND_H115.json).", "",
          "The question as asked (as ordered: every example in):", "", "```", d["question_v2"], "```"]
    with open(os.path.join(OUT, "REPORT.md"), "w") as f:
        f.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="grok,qwen")
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args(argv)
    if not a.report_only:
        run([k for k in a.models.split(",") if k])
    report()
    print(open(os.path.join(OUT, "REPORT.md")).read()[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
