#!/usr/bin/env python3
"""ORCHESTRATOR ORDER 05:35 ET: tonight's package as WRITTEN BY THE ORCHESTRATOR, run through the corrected gates as
attempt 1 (no writer loop). Gates:

- VO fidelity: deterministic, then the blind CLASSIFYING verdict (A attribution / B fact / C production / D host
  commentary; orchestrator 05:25 items 1-2);
- context integrity: step A on each moment's own context (package-independent), then B and C on the package;
- the factory's own EDL rule R4 (edl_rules.rule_r4) and the 60-70 s runtime arithmetic;
- DUPLICATE;
- the exclusion verdict per moment (L-u);
- law L-v 2's second recognition pass per segment (the router's transcribe chain) on the saved audio windows;
- the blind coherence verdict.

Independent calls run concurrently (05:25 item 5). Vendor rule: the VO's author is the orchestrator (assumed a Claude
session), so every verdict on the VO avoids vendor anthropic and family claude. Step A and the exclusion verdicts judge
only the source moments and use the cheapest capable model (claude-opus-5-5, $0.01 a call measured).

Usage: python3 tests/package/run_given_package.py [--variant r4|full] [--bridge-alt] [--takeaway-alt]
Writes tests/package/proof/fresh_20261112_050611/given_<variant>.json and prints every line's class and verdict."""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
import context_integrity as CI  # noqa: E402
import eligibility as E  # noqa: E402
import moments as M  # noqa: E402
import package as PK  # noqa: E402
import proof_moments as PM  # noqa: E402
import providers as P  # noqa: E402
import transcript_truth as TT  # noqa: E402
import vo_fidelity as VF  # noqa: E402

RUN = "fresh_20261112_050611"
SCRATCH = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad"
AUDIO = os.path.join(SCRATCH, "lv2")
REPLIES = os.path.join(HERE, "fixtures", "replies")
OUT = os.path.join(HERE, "proof", RUN)
HOOK, WBD, LIVERA = "3b3050f4afd6f3c011e7", "876662b7dc4e961d47e1", "b0b787f8a62d97d81dbb"
AUTHOR = {"vendor": "anthropic", "family": "claude"}      # the orchestrator's text: verdicts avoid its vendor / family
CHAINS = {"context_verdict": ["anthropic:claude-opus-5-5", "xai:grok-4.20-0309-reasoning",
                              "heimdall:deepseek/deepseek-v4.1-flash"],
          "viewer_takeaway": ["anthropic:claude-opus-5-5", "xai:grok-4.20-0309-reasoning",
                              "heimdall:deepseek/deepseek-v4.1-flash"],
          "fidelity_verdict": ["xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash"],
          "coherence_verdict": ["xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash"],
          "exclusion_verdict": ["anthropic:claude-opus-5-5", "xai:grok-4.20-0309-reasoning"],
          "transcribe": ["openai_stt:gpt-4o-transcribe-diarize", "elevenlabs_stt:scribe_v1"]}


NATALIE = "5e38ec62aa36eae80132"
WBD2 = "4f9d38e1d86556b36d9c"


def recut(by_id, sources, base, w0, w1, k0, k1, why):
    """A moment re-cut by word range from the store record of its base moment (orchestrator 06:45 A / B): the same
    record, verbatim words, times from word timing; a new id (moments.moment_id)."""
    m0 = by_id[base]
    src = sources[m0["video_id"]]
    T = src.tokens
    m = dict(m0, words=[w0, w1], sentences=[k0, k1], start=E._time(T[w0], "start"), end=E._time(T[w1], "end"),
             text=E.spoken(T[w0:w1 + 1]), recut_from=base, recut_why=why)
    m["duration_s"] = round(m["end"] - m["start"], 2)
    m["moment_id"] = M.moment_id(src, w0, w1)
    return m


def fields(variant, bridge_alt, takeaway_alt, bridge_text=None, caption_text=None):
    """The orchestrator's lines. The renderer plays hook -> intro VO -> clip_01 -> bridge(after 1) -> clip_02 ->
    bridge(after 2) -> shout-out (render16.py:306-334, render_vertical.py:853-880). 'r4' / 'full': the 05:35 package
    (Livera); 'v0600': the 06:00 package (orchestrator decisions 06:00 item 5: Natalie Brunell last, three VO lines)."""
    if variant == "v0700":                      # orchestrator 06:45: clip_02 to "emerges.", clip_01 replaced
        ids = [HOOK, "WBD2_RECUT", "NATALIE_EXT"]
        return {"order": ids, "after": [1, 2],
                "intro": {"text": "Nobody is in charge of Bitcoin. That's not a flaw. That's the design.",
                          "cites": [HOOK, "WBD2_RECUT"]},
                "bridges": [{"text": bridge_text or "Next, from Natalie Brunell's show: what does a system with no one "
                                                    "in charge have to get right?", "cites": ["NATALIE_EXT"]},
                            {"text": "No ruler. Just rules nobody gets to bend. That's the idea.", "cites": []}],
                "title": {"text": "Nobody is in charge of Bitcoin.", "cites": ids},
                "caption": {"text": caption_text or "no authority. three voices on why that is the point.", "cites": ids},
                "type": "moments", "angle": "Nobody is in charge of Bitcoin, and that is the point."}
    if variant == "v0600":
        vo2 = bridge_text or ("Here's Natalie Brunell on what that takes." if bridge_alt else
                              "So what does a system with no one in charge actually have to get right? Here's Natalie "
                              "Brunell.")
        vo3 = "No ruler. Just rules. That's the whole idea." if takeaway_alt else \
            "No ruler. Just rules nobody gets to bend. That's the whole idea, and it's the part people miss."
        ids = [HOOK, WBD, NATALIE]
        return {"order": ids, "after": [1, 2],
                "intro": {"text": "Nobody is in charge of Bitcoin. That's not a flaw. That's the design. So the next "
                                  "time you hear about a hack, ask what actually got hacked.", "cites": [HOOK, WBD]},
                "bridges": [{"text": vo2, "cites": [NATALIE]}, {"text": vo3, "cites": []}],
                "title": {"text": "Nobody is in charge of Bitcoin.", "cites": ids},
                "caption": {"text": caption_text or "no authority. three voices on why that is the point.", "cites": ids},
                "type": "moments", "angle": "Nobody is in charge of Bitcoin, and that is the point."}
    ids = [HOOK, WBD, LIVERA]
    hand_off = bridge_text or ("And Stephan Livera thinks it's still underpriced." if bridge_alt else
                               "And Stephan Livera thinks the market still hasn't priced that in.")
    takeaway = "No ruler. No back door. That's the whole idea." if takeaway_alt else \
        "No ruler. No back door. That's what you're actually buying into."
    intro = "Nobody is in charge of Bitcoin. That's not a flaw. That's the design."
    if variant == "full":
        intro += " So the next time you hear about a hack, ask what actually got hacked."
        bridges = [{"text": hand_off, "cites": [LIVERA]}, {"text": takeaway, "cites": []}]
    else:
        bridges = [{"text": hand_off, "cites": [LIVERA]}]
    return {"order": ids, "after": [1, 2] if variant == "full" else [1], "intro": {"text": intro, "cites": ids},
            "bridges": bridges, "title": {"text": "Nobody is in charge of Bitcoin", "cites": ids},
            "caption": {"text": caption_text or "no authority. no back door. three voices on why that is the point.",
                        "cites": ids},
            "type": "moments", "angle": "Nobody is in charge of Bitcoin, and that is the point."}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("r4", "full", "v0600", "v0700"), default="v0700")
    ap.add_argument("--cheap-only", action="store_true", help="the free gates only (no model call)")
    ap.add_argument("--bridge-alt", action="store_true")
    ap.add_argument("--takeaway-alt", action="store_true")
    ap.add_argument("--bridge-text", help="a line fix for the bridge (the order allows 2 per line)")
    ap.add_argument("--caption-text", help="a line fix for the caption")
    ap.add_argument("--intro-text", help="a line fix for VO 1 (the intro)")
    ap.add_argument("--takeaway-text", help="a line fix for VO 3 (the takeaway)")
    ap.add_argument("--tag", default="", help="suffix of the output file")
    ap.add_argument("--to-does", action="store_true", help="07:25: clip_02 through 'does.'")
    ap.add_argument("--xai-heimdall", action="store_true", help="07:25: Anthropic and OpenAI are out of credit")
    a = ap.parse_args(argv)
    t_start = time.time()
    led0 = json.load(open(PM.SPEND))["usd_estimate"]
    chains = CHAINS
    if a.xai_heimdall:                          # orchestrator 07:25: xAI, Heimdall and local only
        chains = {r: [b for b in c if not b.startswith(("anthropic:", "openai:"))] for r, c in CHAINS.items()}
        chains = {r: (c + ["heimdall:deepseek/deepseek-v4.1-flash"] if len(c) < 2 and r != "transcribe" else c)
                  for r, c in chains.items()}
    router = P.Router(env_path=P.ENV_PATH, record_dir=REPLIES, spend_path=PM.SPEND, limit_usd=PM.LIMIT_USD,
                      chains=chains)
    say_chains = {r: c for r, c in chains.items()}
    rec_m = json.load(open(os.path.join(PM.OUT, RUN, "moments.json")))
    by_id = {m["moment_id"]: m for m in rec_m["moments"]}
    words, captions, ctx, saved = PM.universe_sources(RUN)
    sources = {s.video_id: s for s in words}
    f = fields(a.variant, a.bridge_alt, a.takeaway_alt, a.bridge_text, a.caption_text)
    if a.variant == "v0700":
        T = sources["c1JGheQBPH4"].tokens
        w_us = next(i for i in range(7326, 7387) if (T[i].get("word") or "") == ".S." and
                    (T[i - 1].get("word") or "") == "U")             # the store tokenises "U.S." as 'U' + '.S.'

        wbd = recut(by_id, sources, WBD2, 7325, w_us, 464, 464,
                    "clip_01 replaced (06:45 B): the store's sentence 464 cut at 'U.S.': the independent recogniser "
                    "ends a sentence there ('in the US. Um, you know')")
        if a.to_does:                           # orchestrator 07:25: 'emerges' runs into 'And' with no pause
            nat = recut(by_id, sources, NATALIE, 1417, 1456, 108, 111,
                        "clip_02 extended to 'does.' (07:25): the cutter found no pause after 'emerges.'; the "
                        "recognisers and the cutter's own M19 pause test end it at 'does.'")
        else:
            nat = recut(by_id, sources, NATALIE, 1417, 1447, 108, 110,
                        "clip_02 extended to 'emerges.' (06:45 A): the speaker runs on 'secure, and that's what "
                        "emerges.'")
        by_id[wbd["moment_id"]], by_id[nat["moment_id"]] = wbd, nat
        swap = {"WBD2_RECUT": wbd["moment_id"], "NATALIE_EXT": nat["moment_id"]}
        f["order"] = [swap.get(x, x) for x in f["order"]]
        for ln in [f["intro"], f["title"], f["caption"]] + f["bridges"]:
            ln["cites"] = [swap.get(x, x) for x in ln["cites"]]
    if a.intro_text:
        f["intro"] = dict(f["intro"], text=a.intro_text)
    if a.takeaway_text and len(f["bridges"]) > 1:
        f["bridges"][-1] = dict(f["bridges"][-1], text=a.takeaway_text)
    pk = PK.assemble(f["order"], by_id, f, ctx, f"written by the orchestrator, variant {a.variant}")
    pk["vo"]["bridges_after_clip"] = list(f["after"])           # a takeaway may follow the last clip (06:00 ruling 4)
    levels = PK.current_levels(sources.values(), ctx)
    contexts = CI.contexts_from_sources(pk, sources, ctx.now)
    log = []
    say = lambda s: (log.append(s), print(s, flush=True))
    say(f"PACKAGE {a.variant}: runtime estimate {pk['runtime_s_estimate']} s ({pk['runtime_note']})")
    say(f"CHAINS: {json.dumps(say_chains)}")
    r4_ok, r4_why = PK.r4(pk)
    say(f"R4: {r4_why}")
    say(f"VO: intro {len(pk['vo']['intro'].split())} words; bridges {[len(b.split()) for b in pk['vo']['bridges']]} "
        f"after clips {pk['vo']['bridges_after_clip']}; sign-off: {pk['vo']['signoff']!r}")
    if a.cheap_only:
        v, det, dup, rt_ok, r4r = PK.cheap_checks(pk, {}, PK.current_levels(sources.values(), ctx), ctx.now)
        say(f"CHEAP GATES (speakers unverified until step A): {json.dumps(v)}")
        return 0
    # 1. step A (package-independent; the cheapest capable model) -> verified speakers for the fidelity check
    t0 = time.time()
    a_by, a_backend = CI.step_a(router, contexts, writer_vendor=None)
    say(f"step A ({a_backend}, {time.time() - t0:.0f} s): " + "; ".join(
        f"{lb}: fails {CI.a_failures(x) or 'none'}, speaker {x.get('speaker_is')} verified {x.get('speaker_verified')}"
        f" ({x.get('speaker_evidence')!r:.60})" for lb, x in a_by.items()))
    segs_v = {}
    for sg in pk["segments"]:
        ver = a_by[sg["label"]].get("speaker_verified")
        segs_v[sg["moment_id"]] = {"show": sg["channel"], "speaker": sg["channel"] if ver else None,
                                   "names": [sg["channel"]] if ver else [], "video_id": sg["video_id"], "text": sg["text"]}
    lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": ctx.now.strftime("%Y-%m-%d")}
    # 2. everything else that is independent, concurrently
    t0 = time.time()
    def covering_wav(sg):
        """A saved window of this video covering the clip with >= 1 s of context on both sides, or None (fetched)."""
        for x in sorted(os.listdir(AUDIO)):
            parts = x[:-4].rsplit("_", 2) if x.endswith(".wav") else []
            if len(parts) == 3 and parts[0] == sg["video_id"]:
                a_, b_ = int(parts[1]) / 1000.0, int(parts[2]) / 1000.0
                if a_ <= float(sg["start"]) - 1.0 and b_ >= float(sg["end"]) + 1.0:
                    return os.path.join(AUDIO, x), a_
        return None, None

    def truth(sg):
        w, ws = covering_wav(sg)
        return TT.verify_segment(router, sg["video_id"], float(sg["start"]), float(sg["end"]), sg["text"], AUDIO,
                                 wav=w, wav_start=ws)

    exc_cache = {}

    def exclusion(sg):
        return PK.exclusion_for(router, by_id[sg["moment_id"]], sources, exc_cache)

    with ThreadPoolExecutor(max_workers=10) as ex:
        f_fid = ex.submit(VF.check, router, segs_v, lines, AUTHOR["vendor"], 7, man, levels, AUTHOR["family"])
        f_ctx = ex.submit(CI.check_contexts, router, pk, contexts, AUTHOR["vendor"], 7,
                          {lb: x for lb, x in a_by.items()}, AUTHOR["family"], True)
        f_exc = {sg["label"]: ex.submit(exclusion, sg) for sg in pk["segments"]}
        f_tru = {sg["label"]: ex.submit(truth, sg) for sg in pk["segments"]}
        fid, ctx_ = f_fid.result(), f_ctx.result()
        exc = {k: v.result() for k, v in f_exc.items()}
        tru = {}
        for k, v in f_tru.items():
            try:
                tru[k] = v.result()
            except Exception as e:
                tru[k] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
    say(f"concurrent gates: {time.time() - t0:.0f} s")
    dup = PK.duplicates(pk)
    ok_c, coh = PK.coherence(router, pk, AUTHOR["vendor"], writer_family=AUTHOR["family"])
    # report
    say("VO FIDELITY deterministic: " + ("PASS" if fid["deterministic"]["ok"] else "FAIL " + json.dumps(
        fid["deterministic"]["violations"])))
    say(f"VO FIDELITY verdict ({fid['backend']}): " + ("PASS" if (fid["verdict"] or {}).get("ok") else "FAIL"))
    for c in (fid["verdict"] or {}).get("claims") or []:
        say(f"   [{c.get('line')}] {c.get('class')}: {c.get('words')!r} -> {c.get('supported')} "
            f"{json.dumps(c.get('tests')) if c.get('class') == 'commentary' else json.dumps(c.get('support'))[:240]}")
    for v in (fid["verdict"] or {}).get("violations") or []:
        say(f"   VIOLATION {v['slot']}: {v['rule']}: {v['detail']}")
    say(f"CONTEXT INTEGRITY (A {ctx_['backends'].get('A')}, B {ctx_['backends'].get('B')}, C "
        f"{ctx_['backends'].get('C')}): " + ("PASS" if ctx_["ok"] else "FAIL " + json.dumps(ctx_["violations"])))
    for lb, x in (ctx_.get("segments") or {}).items():
        say(f"   {lb}: A '{x['A']['proposition']}' ({x['A']['certainty']}) | B '{x['B']['asserts']}' "
            f"({x['B']['certainty']}) | B0 clip alone ({x['B0']['certainty']}) | C {x['C']}")
    for n in ctx_.get("notes") or []:
        say(f"   note: {n}")
    say(f"   relations: {ctx_.get('relations')}")
    say("DUPLICATE: " + ("PASS" if not dup else "FAIL " + json.dumps(dup)))
    say("EXCLUSION: " + "; ".join(f"{k}: {v['verdict']} ({v.get('backend')}: {v['why'][:80]})" for k, v in exc.items()))
    say("L-v 2 SECOND PASS: " + "; ".join(f"{k}: {'PASS' if v.get('ok') else 'FAIL'} ({v.get('model')}, disagree "
                                          f"{v.get('disagree')}, speakers {v.get('speakers')}, err {v.get('error')})"
                                          for k, v in tru.items()))
    say("CUTTABLE (independent recogniser's boundaries): " + "; ".join(
        f"{k}: {'PASS' if (v.get('edges') or {}).get('cuttable') else 'FAIL'} IN {(v.get('edges') or {}).get('in')} "
        f"OUT {(v.get('edges') or {}).get('out')}" for k, v in tru.items()))
    say(f"COHERENCE ({coh.get('backend')}): {'PASS' if ok_c else 'FAIL'} {json.dumps(coh)[:500]}")
    rt_ok = PK.RUNTIME_S[0] <= pk["runtime_s_estimate"] <= PK.RUNTIME_S[1]
    gates = {"vo_fidelity_deterministic": fid["deterministic"]["ok"], "vo_fidelity_verdict": bool((fid["verdict"] or {}).get("ok")),
             "price_now_measured": fid["deterministic"].get("price_now_measured"), "duplicate": not dup,
             "runtime": rt_ok, "r4": r4_ok, "context": ctx_["ok"], "exclusion": all(v["verdict"] == "keep" for v in exc.values()),
             "second_pass": all(v.get("ok") for v in tru.values()),
             "cuttable": all((v.get("edges") or {}).get("cuttable") is True for v in tru.values()), "coherence": ok_c}
    led1 = json.load(open(PM.SPEND))["usd_estimate"]
    say(f"GATES: {json.dumps(gates)}")
    say(f"ALL PASS: {all(v for k, v in gates.items() if k != 'price_now_measured')} | wall {time.time() - t_start:.0f} s | "
        f"spend this attempt ${led1 - led0:.2f} (ledger ${led1:.2f} of ${PM.LIMIT_USD})")
    pk["gates"] = PK.inventory(fid, dup, rt_ok, (r4_ok, r4_why), ctx_, a_by, exc, tru, ok_c, coh)
    pk["cut_evidence"] = {lb: {"video_id": t.get("video_id"), "start": t.get("start"), "end": t.get("end"),
                               "model": t.get("model"), "audio": t.get("audio"), "in": (t.get("edges") or {}).get("in"),
                               "out": (t.get("edges") or {}).get("out")} for lb, t in tru.items()}
    say("INVENTORY: " + "; ".join(f"{k} {v['status']}" for k, v in pk["gates"].items()))
    pk["checks_given"] = {"fidelity": fid, "context": ctx_, "duplicates": dup, "exclusion": exc, "truth": tru,
                          "coherence": coh, "r4": [r4_ok, r4_why], "runtime_ok": rt_ok, "gates": gates,
                          "step_a": a_by, "current_levels": levels, "author": AUTHOR,
                          "wall_s": round(time.time() - t_start, 1), "usd": round(led1 - led0, 4)}
    os.makedirs(OUT, exist_ok=True)
    name = f"given_{a.variant}{'_balt' if a.bridge_alt else ''}{'_talt' if a.takeaway_alt else ''}{a.tag}.json"
    json.dump(pk, open(os.path.join(OUT, name), "w"), indent=1, default=str)
    open(os.path.join(OUT, name.replace(".json", ".log")), "w").write("\n".join(log) + "\n")
    say(f"written {os.path.join(OUT, name)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
