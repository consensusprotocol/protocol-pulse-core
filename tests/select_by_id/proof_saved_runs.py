#!/usr/bin/env python3
"""Proof of select_by_id on the saved universes (order 2026-11-12 00:32 ET, item 3). CPU only; read-only inputs;
the stand-in model's every reply recorded (tests replay them offline).

Per saved universe runs/<run>/TOPIC_SELECTION.json:
  1 its transcripts by the sha the run recorded (hash-checked; the shared store data/editorial, READ-ONLY, as
    pipeline/backtest.py replays a day), identity from the run's universe record, as eligibility Sources
  2 its DEC-13 candidate groups: the clusters the run recorded (member chunk ids, tier), or for a run older than DEC-13
    the same clustering recomputed on CPU from the run's CACHED embedding vectors (data/editorial/embeddings, read
    only; nothing is embedded): story_semantics.emergent_clusters(min_channels=2) + editorial_select.cluster_entry
  3 per group, 48 h tier then 72 h (until a line-up is accepted or MAX_STORY_CALLS is spent): story_table over the
    member chunks -> choose_story -> the story's word Sources (sentence-ready store word records, full-video times;
    never a run's window transcript) -> lineup_table -> choose_lineup
  4 the independent angle: every accepted id re-read from its record (resolution: the record found again by its
    segments sha and, for word records, the words actually used by their own sha256), then the whole selection
    re-judged by the same predicate with the run's story ledger (labelled as the same predicate, not a second angle)
The approved preview (pinned_20261111_172202): its four frozen word transcripts (tests/select_by_id/fixtures/preview,
hash-equal to references/pulse_preview_2026-11-11/SHA256SUMS) as one group, run clock = the Nov 10 run start.

Usage: python3 tests/select_by_id/proof_saved_runs.py [--runs NAME ...] [--replay] [--max-story-calls N]
"""
import argparse
import glob
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import numpy as np  # noqa: E402

import eligibility as E  # noqa: E402
import select_by_id as S  # noqa: E402
import transcript_store as ts  # noqa: E402

MAIN = os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse")      # read-only inputs (audit C2: not hard-wired)
RUNS = os.path.join(MAIN, "runs")
STORE = os.path.join(MAIN, "data", "editorial")
REF = os.path.join(MAIN, "references", "pulse_preview_2026-11-11")
ENV = os.path.join(MAIN, ".env")                       # read by name inside OpenAIStandIn only
REPLIES = os.path.join(HERE, "fixtures", "replies")
OUT = os.path.join(HERE, "proof")
SPEND = os.path.join(OUT, "SPEND.json")
PREVIEW = os.path.join(HERE, "fixtures", "preview", "preview_sources.json")
REG = json.load(open(os.path.join(REPO, "pipeline", "channels.json")))
SAVED = ("fresh_20261106_213852", "fresh_20261107_065702", "fresh_20261107_080503", "fresh_20261110_093150",
         "fresh_20261111_190259", "fresh_20261111_192645", "fresh_20261111_213954", "fresh_20261112_001448",
         "fresh_20261112_013452", "fresh_20261112_050611")
PREVIEW_RUN = "pinned_20261111_172202"
MAX_STORY_CALLS = 8
LEDGER = os.path.join(MAIN, "data", "pulse_check", "story_ledger.jsonl")   # story_ledger.LEDGER, read-only
WORDS_USED = {}                    # video_id -> (record path, sha256 of the words the proof used)


def words_sha256(rec):
    return hashlib.sha256(json.dumps([(w.get("word"), w.get("start"), w.get("end")) for w in rec.get("words") or []],
                                     ensure_ascii=False).encode()).hexdigest()


def ledger_entries():
    """The DEC-9 story ledger as of the proof (read-only): every entry, or () when nothing was ever delivered."""
    if not os.path.exists(LEDGER):
        return ()
    return tuple(json.loads(line) for line in open(LEDGER) if line.strip())
EMBED_REV = "a5beb1e3e68b"


# ── read-only inputs ──

def load_record(video_id, sha):
    """The record whose segments hash to `sha` (transcript_store's own hash), read-only; None if absent."""
    for p in sorted(glob.glob(os.path.join(STORE, "transcripts", video_id, "transcript.*.json"))):
        try:
            with open(p) as f:
                rec = json.load(f)
        except (OSError, ValueError):
            continue
        if rec.get("transcript_sha256") == sha and ts.segments_sha256(rec.get("segments") or []) == sha:
            return rec
    return None


def with_identity(rec, u):
    """A record's missing provenance taken from the run's universe record (as transcript_store.chunks takes it from
    meta.json, E-FAIL-030); a field the record has is never overridden."""
    r = dict(rec)
    fill = {"video_id": u["video_id"], "canonical_url": u.get("canonical_url"), "channel_id": u.get("channel_id"),
            "channel_name": u.get("channel"), "exact_title": u.get("title"), "published_at": u.get("published_at")}
    for k, v in fill.items():
        if r.get(k) is None:
            r[k] = v
    return r


def source_of(rec, u):
    """A full-video store record of a universe upload: asserts the media start and an upload (audit M3)."""
    timing, toks = S.tokens_from_record(rec)
    return E.Source(u["video_id"], u.get("channel_id"), u.get("channel"), u.get("published_at"),
                    rec.get("transcript_sha256"), rec.get("transcript_method"), toks, timing=timing,
                    title=u.get("title") or "", file_head=True, vod=True)


def word_source(u, ctx):
    """A sentence-ready word record of this video from the store (full-video timestamps), punctuated record first."""
    vid = u["video_id"]
    paths = sorted(glob.glob(os.path.join(STORE, "transcripts", vid, "transcript.whisper_words*.json")),
                   key=lambda p: "punct" not in p)
    for p in paths:
        try:
            rec = json.load(open(p))
        except (OSError, ValueError):
            continue
        if rec.get("transcript_sha256") != ts.segments_sha256(rec.get("segments") or []):
            continue
        src = source_of(with_identity(rec, u), u)
        if E.sentence_ready(src):
            WORDS_USED[vid] = (p, words_sha256(rec))
            return src
    return None


def vectors(video_id, sha, ids):
    for name in (f"{sha[:16]}.{EMBED_REV}.t2.npz", f"{sha[:16]}.{EMBED_REV}.npz"):
        p = os.path.join(STORE, "embeddings", video_id, name)
        if os.path.exists(p):
            z = np.load(p, allow_pickle=False)
            if list(z["ids"]) == ids:
                return z["vecs"]
    return None


def groups_of(saved, uni, sources):
    """DEC-13 groups as (entry, {video_id: [(t0, t1), ...]}), tier order (48 h, then 72 h)."""
    em = saved.get("emergent_clusters") or []
    recorded = bool(em) and all("member_chunk_ids" in e and "screen" in e for e in em)
    log = {"recorded": recorded}
    if not recorded:
        import editorial_select as es
        import story_semantics as sm
        chunks, vecs, missing = [], [], []
        for vid, u in uni.items():
            rec = sources[vid]["rec"]
            cs = ts.chunks(rec)
            v = vectors(vid, u["transcript_sha256"], [c["chunk_id"] for c in cs])
            if v is None or not cs:
                missing.append(vid)
                continue
            for c in cs:
                c["age_h"], c["layout_eligible"] = u.get("age_h"), E.layout_ok(next(
                    (r for r in REG if r.get("channel_id") == u.get("channel_id")), None))
            chunks += cs
            vecs.append(v)
        vecs = np.vstack(vecs) if vecs else np.zeros((0, 768), np.float32)
        t0 = time.time()
        gs = sm.emergent_clusters(chunks, vecs, min_channels=es.MIN_COVERAGE_CHANNELS, max_clusters=None)
        em = [es.cluster_entry(chunks, vecs, g) for g in gs]
        log.update(recomputed_s=round(time.time() - t0, 1), chunks=len(chunks), no_vectors=missing)
    out = []
    for tier in ("48h", "72h"):
        for e in em:
            if e.get("screen") != tier:
                continue
            spans = {}
            for cid in e["member_chunk_ids"]:
                vid, a, b = ts.parse_chunk_id(cid)
                spans.setdefault(vid, []).append((a, b))
            out.append((e, spans))
    log.update(groups=len(em), screened={t: sum(1 for e in em if e.get("screen") == t) for t in ("48h", "72h")})
    return out, log


# ── checks after acceptance ──

def resolve(span, preview=None):
    """The accepted span re-read from its record by sha: the same words, the same sentence indices."""
    src = span.source
    if preview is not None:
        v = next(x for x in preview["videos"] if x["video_id"] == src.video_id)
        raw = open(os.path.join(REF, "transcripts", f"{src.video_id}.json"), "rb").read()
        if hashlib.sha256(raw).hexdigest() != src.transcript_sha256 or v["transcript_sha256"] != src.transcript_sha256:
            return False, "reference transcript hash differs"
        rec = {"words": json.loads(raw)["words"]}
    elif src.timing == "word" and src.video_id in WORDS_USED:
        path, sha = WORDS_USED[src.video_id]
        rec = json.load(open(path))
        if words_sha256(rec) != sha or rec.get("transcript_sha256") != src.transcript_sha256:
            return False, "the word record changed since it was read"
    else:
        rec = load_record(src.video_id, src.transcript_sha256)
        if rec is None:
            return False, "no record with that sha"
    _, toks = S.tokens_from_record(rec)
    sents = E.split_sentences(toks)
    if not span.k1 < len(sents):
        return False, "sentence index out of range"
    text = E.spoken(toks[sents[span.k0][0]:sents[span.k1][1] + 1])
    return (text == span.text), ("same words" if text == span.text else f"text differs: {text[:80]!r}")


def summary_span(sp, ctx):
    reg = ctx.channel(sp.source.channel_id) or {}
    return {"channel": reg.get("display_name") or sp.source.channel_name, "video_id": sp.source.video_id,
            "sentences": [sp.k0, sp.k1], "start": sp.start, "end": sp.end,
            "seconds": round(sp.end - sp.start, 2) if sp.source.timing == "word" else None, "text": sp.text}


# ── one run (through select_by_id.run_pools, the production entry) ──

def finish(rec, out, ctx, preview=None):
    """Per-group record, then the second angle on an accepted selection: every id re-read from its record by sha,
    the whole line-up re-judged by eligibility with a fresh Context."""
    rec["groups"] = out["groups"]
    rec["pools"] = out["pools"]
    rec["story_calls"] = sum(1 for g in out["groups"] if (g.get("story") or {}).get("attempts"))
    rec["lineup_calls"] = sum(1 for g in out["groups"] if (g.get("lineup") or {}).get("attempts"))
    sel = out["selected"]
    if sel is None:
        return rec
    st, lo = sel["story"], sel["lineup"]
    spans = list(st.story) + [lo.hook] + list(lo.clips)
    res = [resolve(sp, preview) for sp in spans]
    recheck = E.eligible(E.Lineup(story=tuple(st.story), claim=st.claim, hook=lo.hook, clips=tuple(lo.clips)),
                         E.Context(ctx.now, REG, ledger=ctx.ledger))     # the same predicate, with the run's ledger
    segs = [("hook", lo.hook)] + [(f"clip_{i + 1:02d}", c) for i, c in enumerate(lo.clips)]
    rec["result"] = {"lineup": True, "pool": sel["pool"], "group": sel["group"],
                     "ids_resolve": all(ok for ok, _ in res), "resolution": [w for _, w in res],
                     "eligibility_recheck": recheck.ok, "eligibility_reasons": recheck.why(),
                     "eligibility_recheck_note": "the same predicate again (with the ledger); ids_resolve is the "
                                                 "independent angle",
                     "claim": summary_span(st.claim, ctx), "story_tier": st.eligibility.facts.get("tier"),
                     "story": [summary_span(s, ctx) for s in st.story],
                     "segments": [dict(summary_span(sp, ctx), segment=lab) for lab, sp in segs],
                     "passages": S.to_passages(st, lo)["chosen"]}
    return rec


def run_saved(name, model, max_calls, checks=None):
    saved = json.load(open(os.path.join(RUNS, name, "TOPIC_SELECTION.json")))
    started = datetime.fromisoformat(saved["started"])
    assert started.tzinfo is not None, f"{name}: run start {saved['started']!r} has no timezone (audit C2)"
    now = started.astimezone(timezone.utc)
    ledger = ledger_entries()
    ctx = E.Context(now, REG, ledger=ledger)
    rec = {"run": name, "now": now.isoformat(), "result": {"lineup": False},
           "ledger": {"path": LEDGER, "entries": len(ledger)}}
    uni = {u["video_id"]: u for u in saved.get("universe") or []
           if u.get("transcript_sha256") and u["video_id"] not in E.V2F_VIDEO_IDS}
    sources, missing = {}, []
    for vid, u in uni.items():
        r = load_record(vid, u["transcript_sha256"])
        if r is None:
            missing.append(vid)
            continue
        r = with_identity(r, u)
        sources[vid] = {"rec": r, "src": source_of(r, u)}
    uni = {v: u for v, u in uni.items() if v in sources}
    rec["universe"] = {"videos": len(uni), "records_missing": missing,
                       "methods": {m: sum(1 for s in sources.values() if (s["src"].transcript_method or "").split(":")[0] == m)
                                   for m in sorted({(s["src"].transcript_method or "").split(":")[0] for s in sources.values()})}}
    groups, glog = groups_of(saved, uni, sources)
    rec["clusters"] = glog
    em = [e for e, _ in groups]
    srcs = {v: x["src"] for v, x in sources.items()}
    pools = [(f"channel_clusters_{t}", lambda t=t: S.cluster_groups(em, srcs, t)) for t in ("48h", "72h")]
    wcache = {}

    def words_fn(vids):
        for v in vids:
            if v not in wcache:
                wcache[v] = word_source(uni[v], ctx)
        return {v: wcache[v] for v in vids}
    out = S.run_pools(model, ctx, pools, words_fn, log=lambda s: None, max_story_calls=max_calls, checks=checks)
    rec["wire_pool"] = "not run in this CPU replay: wire retrieval needs the GPU0 embedder (DEC-13: wire only after clusters)"
    return finish(rec, out, ctx)


def run_preview(model, checks=None):
    import canon
    from dataclasses import replace
    sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
    from test_eligibility import span_for
    d = json.load(open(PREVIEW))
    now = datetime.fromisoformat(d["now"])
    ctx = E.Context(now, REG)
    srcs = []
    for v in d["videos"]:
        timing, toks = S.tokens_from_record({"words": v["words"]})
        srcs.append(E.Source(v["video_id"], v["channel_id"], v["channel_name"], v["published_at"], v["transcript_sha256"],
                             "whisper_words", toks, timing=timing, title=v["title"], file_head=True, vod=True))
    rec = {"run": PREVIEW_RUN, "now": now.isoformat(), "result": {"lineup": False},
           "universe": {"videos": 4, "note": "the preview's four frozen word transcripts (5-10 min windows at offset 0)"}}
    by = {s.video_id: s for s in srcs}
    pools = [("preview", lambda: [("the preview's four sources", [(s, [(0, 1e9)]) for s in srcs], None)])]
    out = S.run_pools(model, ctx, pools, lambda vids: {v: by.get(v) for v in vids}, log=lambda s: None, checks=checks)
    finish(rec, out, ctx, preview=d)
    edl = json.load(open(os.path.join(REF, "edl.json")))
    approved = [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl["clips"]]
    got = rec["result"].get("segments") or []
    accepted = next((g["story"] for g in rec["groups"] if (g.get("story") or {}).get("status") == "accepted"), None)
    on = None
    if accepted:                    # the approved passages judged with the MODEL's story: why each is or is not reachable
        mspans = [E.Span(by[m["video_id"]], m["k0"], m["k1"]) for m in accepted["story"]]
        claim = next(sp for sp, m in zip(mspans, accepted["story"]) if m == accepted["claim"])
        on = E.Context(now, REG, story=tuple(E.statement_entry(sp) for sp in mspans), event=claim.text)
    rec["overlap_with_approved"] = []
    for lab, a in approved:
        hit = next((g for g in got if g["video_id"] == a["video_id"] and not (g["end"] <= a["word_start"] or
                                                                              g["start"] >= a["word_end"])), None)
        o = {"approved": lab, "channel": a["channel"], "approved_text": a["text"],
             "chosen": hit and hit["segment"], "chosen_text": hit and hit["text"],
             "same_words": bool(hit and canon.same(hit["text"], a["text"])),
             "overlap_s": hit and round(min(hit["end"], a["word_end"]) - max(hit["start"], a["word_start"]), 2)}
        if on is not None:
            r = E.eligible(span_for(by[a["video_id"]], a["text"]), replace(on, role="hook" if lab == "hook" else "clip"))
            o.update(eligible_with_the_models_story=r.ok, reasons_with_the_models_story=r.why())
        rec["overlap_with_approved"].append(o)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*")
    ap.add_argument("--replay", action="store_true", help="recorded replies only; never call out")
    ap.add_argument("--max-story-calls", type=int, default=MAX_STORY_CALLS)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--standin", choices=("auto", "anthropic", "openai"), default="auto",
                    help="auto: gpt-6.1-sol when a one-call probe succeeds, else claude-fable-5-2 (orchestrator 02:00)")
    ap.add_argument("--generator-name", help="replay: the generator name recorded in the run files")
    ap.add_argument("--judge-t0", action="store_true",
                    help="the judge at temperature 0 with the attempt's seed (production parity; its own recordings)")
    a = ap.parse_args(argv)
    import standins
    probe = (False, "replay: not probed") if a.replay else standins.openai_alive(ENV)
    use_openai = a.standin == "openai" or (a.standin == "auto" and probe[0])
    live = (standins.OpenAIStandIn if use_openai else standins.AnthropicStandIn)(ENV, SPEND)
    judge = standins.GrokJudge(ENV, SPEND, temperature=0 if a.judge_t0 else None)
    gen_name = a.generator_name or live.name
    model = S.Replay(gen_name, REPLIES) if a.replay else S.Recorder(live, REPLIES)    # every reply kept (the order)
    checks = S.ModelChecks(S.ChatJSON(S.Replay(judge.name, REPLIES) if a.replay else S.Recorder(judge, REPLIES)))
    print(f"generator {gen_name} | judge {judge.name} | openai probe {probe[1]}", flush=True)
    os.makedirs(a.out, exist_ok=True)
    names = a.runs or list(SAVED) + [PREVIEW_RUN]
    rows = []
    for name in names:
        t0 = time.time()
        try:
            rec = run_preview(model, checks) if name == PREVIEW_RUN else run_saved(name, model, a.max_story_calls, checks)
        except S.SpendLimit as e:
            rec = {"run": name, "stopped": f"SPEND GUARD: {e}", "result": {"lineup": False}}
            json.dump(rec, open(os.path.join(a.out, f"{name}.json"), "w"), indent=1, default=str)
            rows.append(rec)
            print(f"{name}: SPEND GUARD {e}", flush=True)
            break
        rec["seconds"] = round(time.time() - t0, 1)
        rec["models"] = {"generator": gen_name, "judge (ModelChecks)": judge.name, "openai_probe": probe[1]}
        rec["code"] = {f: hashlib.sha256(open(os.path.join(REPO, "pipeline", f), "rb").read()).hexdigest()[:16]
                       for f in ("select_by_id.py", "eligibility.py")}            # which code produced this row
        json.dump(rec, open(os.path.join(a.out, f"{name}.json"), "w"), indent=1, default=str)
        rows.append(rec)
        r = rec["result"]
        print(f"{name}: story calls {rec['story_calls']}, line-up calls {rec['lineup_calls']}, line-up "
              f"{'YES' if r.get('lineup') else 'no'}, ids resolve {r.get('ids_resolve')}, eligibility "
              f"{r.get('eligibility_recheck')} ({rec['seconds']} s)", flush=True)
    return rows


if __name__ == "__main__":
    main()
