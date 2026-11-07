#!/usr/bin/env python3
"""pipeline/editorial_select.py — transcript-first story selection for run_fresh.

LAW: titles/metadata are discovery hints; transcripts establish story identity.

Three independent scores, applied in this order:
  1. STORY IMPORTANCE      current / significant / Bitcoin-relevant
                           (local LLM ratings; the story-engine score is recorded and flagged
                           when its GPT-4o legs are unavailable — never treated as equivalent)
  2. CROSS-SOURCE COVERAGE independent channels whose transcripts are adjudicated SAME_EVENT,
                           each with verbatim-verified evidence chunk ids
  3. CLIP QUALITY          strongest complete statements inside the confirmed story cluster

Editorial universe = every enabled registry channel with a channel_id (layout approval is NOT
a filter here). Layout approval gates only which passages may become rendered clips.

Candidate stories = ranked story-engine items (all of them) + emergent transcript clusters
(bottom-up: what Bitcoin media is discussing). Every reasonable candidate is evaluated; HOLD only
when none is producible. Output: TOPIC_SELECTION.json, passages.json (the frozen select stage's
input contract, full-video seconds), sources.json.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import numpy as np

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE_DIR)
sys.path.insert(0, PIPELINE_DIR)

import transcript_store as ts  # noqa: E402

STORIES_PATH = os.path.join(REPO, "data", "intelligence", "candidate_stories.json")
CHANNELS_PATH = os.path.join(PIPELINE_DIR, "channels.json")

UNIVERSE_HOURS = 72
TOPUP_MAX_WHISPER_HOURS = 8.0      # in-run acquisition for uploads the background ingest missed
MAX_CANDIDATES = 24
BTC_RELEVANCE_MIN = 3
RETRIEVAL_MIN_SIM = 0.55
MAX_ADJUDICATE_PER_STORY = 14
MIN_COVERAGE_CHANNELS = 2
MIN_LAYOUT_CHANNELS = 2            # R5: clips from >= 2 distinct channels
HOOK_MIN_S, HOOK_MAX_S = 8.0, 12.0
CLIP_MIN_S, CLIP_MAX_S = 13.0, 25.0
HOOK_MIN_SCORE, CLIP_MIN_SCORE = 4.0, 3.5
N_CLIPS = 3                        # v2f format: hook + 3 clips
DEDUPE_SIM = 0.88
V2F_VIDEO_IDS = {"RBFN4CB60To", "Pxrak-iMT0g", "QCgW8RlTu5Q"}


class NoProducibleStory(Exception):
    pass


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _recency(age_h):
    if age_h is None:
        return 0.4
    return 1.0 if age_h <= 24 else 0.7 if age_h <= 48 else 0.4 if age_h <= 72 else 0.1


def layout_eligible(channel):
    """Any registered channel with an id is clip-eligible. Presentation safety is
    enforced later: approved channels crop; pending channels letterbox.
    """
    return bool(channel.get("channel_id"))


def story_engine_status(stories, path=STORIES_PATH):
    st = stories.get("stories", [])
    degraded = bool(st) and all(s.get("independent_corroboration", 1) == 1 and
                                s.get("unexpectedness") == 2 and s.get("tension") == 2
                                for s in st)
    return {"path": path, "generated_at": stories.get("generated_at"),
            "sha256": ts.sha256_file(path),
            "llm_legs": ("UNAVAILABLE — GPT-4o clustering/soft scoring returned defaults for every "
                         "story (OpenAI 429; xAI key absent); engine rank = recency + source quality "
                         "+ magnitude regex only") if degraded else "present"}


# ── passages (clip quality inputs) ──

# Quote-anchored windows (PBX 2026-11-06 18:03): code picks the cut, the model only scores it.
#   anchor   = the verified evidence quote, aligned to word timestamps
#   window   = exactly the sentence(s) holding the quote; never expanded or padded
#   boundary = a start must be a sentence boundary (else rejected, never trimmed or guessed)
#   dedupe   = overlapping windows of the same kind in one video collapse to the first kept
ANCHOR_MIN_RATIO = 0.85            # token-level match of quote vs aligned word span
ANCHOR_PAD_S = 30.0                # search the supporting chunks' span +/- this
CONTINUATION_OPENERS = {"and", "but", "or", "so", "because", "cause", "which", "also", "plus", "then",
                        "though", "although", "whereas", "nor", "yet"}
_TERMINAL = (".", "!", "?")


def _tok(w):
    return [t for t in re.split(r"[^a-z0-9]+", (w or "").lower().replace("’", "'").replace("'", "")) if t]


def _word_sentences(words):
    """Sentences as word-index ranges, split after terminal punctuation (same rule as
    transcript_store.sentences_from_words)."""
    out, s0 = [], 0
    for i, w in enumerate(words):
        if w["word"].rstrip().endswith(_TERMINAL):
            out.append((s0, i))
            s0 = i + 1
    if s0 < len(words):
        out.append((s0, len(words) - 1))
    return out


def align_quote(quote, words, t0, t1):
    """Locate a verified quote in word timestamps within [t0, t1]. Returns
    {"w0", "w1", "start", "end", "ratio"} or None. Never fabricates a location."""
    from difflib import SequenceMatcher
    qt = [t for w in (quote or "").split() for t in _tok(w)]
    toks = [(t, i) for i, w in enumerate(words) if t0 <= w["start"] <= t1 for t in _tok(w["word"])]
    if len(qt) < 5 or not toks:
        return None
    seq = [t for t, _ in toks]
    blk = max(SequenceMatcher(None, qt, seq, autojunk=False).get_matching_blocks(), key=lambda b: b.size)
    if blk.size < 3:
        return None
    base, best = blk.b - blk.a, None
    for s in range(max(0, base - 3), min(len(seq), base + 4)):
        for n in range(max(1, len(qt) - 3), len(qt) + 4):
            if s + n > len(seq):
                break
            r = SequenceMatcher(None, qt, seq[s:s + n], autojunk=False).ratio()
            if best is None or r > best[0] + 1e-9:
                best = (r, s, s + n - 1)
    r, s, e = best
    if r < ANCHOR_MIN_RATIO:
        return None
    w0, w1 = toks[s][1], toks[e][1]
    return {"w0": w0, "w1": w1, "start": words[w0]["start"], "end": words[w1]["end"], "ratio": round(r, 3)}


def start_is_boundary(words, sents, si):
    """A window start is a boundary only if the previous sentence ended with terminal punctuation,
    the first word opens a sentence (capital or digit) and is not a continuation conjunction."""
    w0 = sents[si][0]
    if si > 0 and not words[w0 - 1]["word"].rstrip().endswith(_TERMINAL):
        return False, "previous word has no terminal punctuation"
    first = re.sub(r"^[\"'(\[“‘$]+", "", words[w0]["word"].strip())
    if not first or not (first[0].isupper() or first[0].isdigit()):
        return False, f"starts lower-case ({words[w0]['word'].strip()!r})"
    t = _tok(first)
    if t and t[0] in CONTINUATION_OPENERS:
        return False, f"starts with continuation {first!r}"
    return True, "ok"


def anchored_window(words, sents, anchor, lo, hi):
    """PBX 2026-11-06 18:52: the window is EXACTLY the sentence(s) that hold the verified quote.
    No expansion into any sentence that does not contain the quote, no padding. Invalid if the
    duration is outside [lo, hi], the start is not a boundary, or it does not end on '.' or '!'.
    Returns (window, None) or (None, reason); the span is always reported for audit."""
    sa = next(i for i, (a, b) in enumerate(sents) if a <= anchor["w0"] <= b)
    se = next(i for i, (a, b) in enumerate(sents) if a <= anchor["w1"] <= b)
    st, en = words[sents[sa][0]]["start"], words[sents[se][1]]["end"]
    d = round(en - st, 2)
    span = {"start": st, "end": en, "duration": d,
            "first_sentence": " ".join(w["word"].strip() for w in words[sents[sa][0]:sents[sa][1] + 1]),
            "last_sentence": " ".join(w["word"].strip() for w in words[sents[se][0]:sents[se][1] + 1]),
            "n_sentences": se - sa + 1}
    ok, why = start_is_boundary(words, sents, sa)
    if not ok:
        return None, f"start rejected: {why}", span
    if d < lo:
        return None, f"quote sentence(s) {d} s < minimum {lo} s (no padding)", span
    if d > hi:
        return None, f"quote sentence(s) {d} s > maximum {hi} s", span
    if not words[sents[se][1]]["word"].rstrip().endswith((".", "!")):
        return None, "does not end on '.' or '!'", span
    text = " ".join(w["word"].strip() for w in words[sents[sa][0]:sents[se][1] + 1])
    return {**span, "text": text, "anchor_start": anchor["start"], "anchor_end": anchor["end"]}, None, span


def _form_score(text):
    from rank import _score_passage
    return _score_passage(text, [])


# ── main ──

class Checkpoint:
    """E4: atomic TOPIC_SELECTION.json checkpoints throughout evaluation."""

    def __init__(self, run_dir, rec):
        self.run_dir, self.rec, self.n = run_dir, rec, 0

    def __call__(self, phase, **progress):
        self.n += 1
        self.rec["progress"] = {"phase": phase, "checkpoint": self.n, "at": ts.now_iso(), **progress}
        _write(self.run_dir, "TOPIC_SELECTION.json", self.rec)


def _infra_error(msg):
    m = (msg or "").lower()
    return any(k in m for k in ("out of memory", "cuda", "cublas", "cudnn", "gpu0 release not proven"))


def select_story(run_dir, log=print, embedder=None, llm=None, universe_fn=None,
                 stories_path=STORIES_PATH, topup=True, now=None):
    rec = {"law": "titles/metadata are discovery hints; transcripts establish story identity",
           "started": ts.now_iso()}
    ck = Checkpoint(run_dir, rec)
    try:
        return _select_story(run_dir, rec, ck, log, embedder, llm, universe_fn, stories_path, topup, now)
    except NoProducibleStory:
        raise
    except Exception as e:
        import traceback
        rec["crashed"] = {"error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()}
        ck("crashed")
        raise


def _select_story(run_dir, rec, ck, log, embedder, llm, universe_fn, stories_path, topup, now):
    import story_semantics as sm
    from transcript_ingest import universe as ingest_universe
    t0 = time.time()
    now = now or datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    with open(CHANNELS_PATH) as f:
        registry = json.load(f)
    by_cid = {c["channel_id"]: c for c in registry if c.get("channel_id")}
    rec.update({"universe_hours": UNIVERSE_HOURS, "today": today,
                "editorial_channels": sorted(c["display_name"] for c in by_cid.values() if c.get("enabled", True)),
                "layout_eligible_channels": sorted(c["display_name"] for c in by_cid.values()
                                                   if layout_eligible(c)),
                "params": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float))}})
    ck("start")

    # 1. universe + transcripts (cache first; top-up only what background ingest has not covered)
    vids = (universe_fn or ingest_universe)(UNIVERSE_HOURS)
    vids = [v for v in vids if v["video_id"] not in V2F_VIDEO_IDS]
    budget, used, uni = TOPUP_MAX_WHISPER_HOURS * 3600, 0.0, []
    for v in sorted(vids, key=lambda v: (0 if layout_eligible(v["channel"]) else 1, v["age_h"])):
        r = ts.canonical_transcript(v["video_id"])
        status = "cached" if r else None
        if r is None and topup:
            try:
                r, status = ts.acquire(v["video_id"], rss=v["rss"], channel=v["channel"], allow_whisper=False)
                if r is None and status == "pending_whisper":
                    dur = ts.ensure_meta(v["video_id"])["duration"] or 0
                    if used + dur <= budget:
                        r, status = ts.acquire(v["video_id"], rss=v["rss"], channel=v["channel"],
                                               allow_whisper=True, try_captions=False)
                        used += dur
                    else:
                        status = "deferred_budget"
            except Exception as e:
                status = f"error:{type(e).__name__}"
        uni.append({"video_id": v["video_id"], "canonical_url": ts.canonical_url(v["video_id"]),
                    "channel": v["channel"]["display_name"], "channel_id": v["channel"]["channel_id"],
                    "title": v["rss"]["title"], "published_at": v["rss"]["published"], "age_h": v["age_h"],
                    "layout_eligible": layout_eligible(v["channel"]),
                    "transcript_status": status or "missing",
                    "transcript_method": r and r["transcript_method"], "transcript_model": r and r["transcript_model"],
                    "transcript_sha256": r and r["transcript_sha256"], "_rec": r})
    rec["universe"] = [{k: v for k, v in u.items() if k != "_rec"} for u in uni]
    rec["universe_summary"] = {"videos": len(uni), "with_transcript": sum(1 for u in uni if u["_rec"]),
                               "channels": len({u["channel_id"] for u in uni}),
                               "topup_whisper_audio_h": round(used / 3600, 2)}
    log(f"  universe: {rec['universe_summary']}")
    ts.release_whisper()
    ck("universe")

    # 2. attributed chunks + embeddings
    E = embedder or sm.Embedder()
    chunks, vecs = [], []
    for u in uni:
        if not u["_rec"]:
            continue
        cs = ts.chunks(u["_rec"])
        _, vv = E.chunk_vectors(u["_rec"], cs)
        for c in cs:
            c["age_h"], c["layout_eligible"] = u["age_h"], u["layout_eligible"]
        chunks += cs
        vecs.append(vv)
    vecs = np.vstack(vecs) if vecs else np.zeros((0, 768), np.float32)
    by_chunk = {c["chunk_id"]: c for c in chunks}
    rec["embedding_model"] = E.model_id
    rec["n_chunks"] = len(chunks)
    log(f"  chunks: {len(chunks)} from {rec['universe_summary']['with_transcript']} transcripts")

    L = llm or sm.LocalLLM().start()
    rec["llm"] = {"model": L.model, "host": L.host, "serve_env": getattr(L, "serve_env", None),
                  "attempts_per_call": sm.LLM_ATTEMPTS}
    ck("embedded")

    # 3. candidates: story engine (all) + emergent clusters with current-development evidence
    with open(stories_path) as f:
        stories = json.load(f)
    rec["story_engine"] = story_engine_status(stories, stories_path)
    cands = []
    rec["candidates"] = cands
    for s in stories.get("stories", []):
        cands.append({"origin": "story_engine", "engine_rank": s.get("rank"),
                      "engine_score": s.get("overall_score"), "headline": s.get("headline"),
                      "summary": s.get("summary"), "source_domain": s.get("source_domain"),
                      "age_h": (s.get("freshness_minutes") or 0) / 60})
    emergent = []
    rec["emergent_clusters"] = emergent
    for gi, g in enumerate(sm.emergent_clusters(chunks, vecs)):
        lab = sm.label_cluster(L, chunks, vecs, g, today)
        ages = [chunks[i]["age_h"] for i in g["chunk_idx"]]
        entry = {"channels": g["channels"], "n_chunks": len(g["chunk_idx"]), "label": lab}
        if not lab.get("current_ok"):
            entry["rejected"] = ("no verified current-development evidence"
                                 if lab.get("is_specific_event") else
                                 lab.get("error") or "not a specific current event")
        else:
            cdq = lab.get("current_development_chunk_id")
            entry["current_development_evidence"] = {
                "chunk_id": cdq, "quote": lab.get("current_development_quote"),
                "channel": by_chunk.get(cdq, {}).get("channel_name"),
                "canonical_url": by_chunk.get(cdq, {}).get("canonical_url")}
            cands.append({"origin": "transcript_cluster", "headline": lab["headline"],
                          "summary": lab.get("summary", ""), "source_domain": "transcript cluster",
                          "cluster_channels": g["channels"], "cluster_chunk_ids": lab.get("excerpt_chunk_ids"),
                          "current_development_evidence": entry["current_development_evidence"],
                          "age_h": min(ages) if ages else None})
        emergent.append(entry)
        ck("emergent", cluster=gi)
    log(f"  candidates: {len(cands)} ({sum(c['origin'] == 'transcript_cluster' for c in cands)} emergent, "
        f"{sum(1 for e in emergent if e.get('rejected'))} emergent clusters rejected)")

    # 4. STORY IMPORTANCE (+ E1 currentness gate)
    for ci, c in enumerate(cands[:MAX_CANDIDATES + len(emergent)]):
        try:
            q = sm.derive_story_query(L, c, today)
        except sm.LLMParseError as e:
            c["importance_gate"] = ["inconclusive: story-query derivation failed (LLM output unparseable)"]
            c["llm_error"] = {"error": str(e), "llm_attempts": e.attempts}
            ck("derive", candidate=ci, of=len(cands))
            continue
        c["query"] = q
        imp = {"llm_importance": q.get("importance"), "llm_bitcoin_relevance": q.get("bitcoin_relevance"),
               "is_specific_event": q.get("is_specific_event"), "event_date": q.get("event_date"),
               "event_recency": q.get("event_recency"), "recency": _recency(c.get("age_h")),
               "engine_score": c.get("engine_score"),
               "engine_score_note": rec["story_engine"]["llm_legs"] if c["origin"] == "story_engine" else None}
        try:
            imp["importance_score"] = round(0.45 * float(q.get("importance", 0)) / 5 +
                                            0.35 * float(q.get("bitcoin_relevance", 0)) / 5 +
                                            0.20 * imp["recency"], 3)
        except Exception:
            imp["importance_score"] = 0.0
        c["importance"] = imp
        gate = []
        if (q.get("bitcoin_relevance") or 0) < BTC_RELEVANCE_MIN:
            gate.append(f"bitcoin_relevance {q.get('bitcoin_relevance')} < {BTC_RELEVANCE_MIN}")
        if not q.get("is_specific_event", True):
            gate.append("not a specific event")
        c["model_date_hint"] = sm.model_date_hint(q, now, UNIVERSE_HOURS)   # E9: hint only, never a gate
        c["importance_gate"] = gate
        ck("derive", candidate=ci, of=len(cands))
    live = [c for c in cands if "query" in c and not c["importance_gate"]]
    if live:
        ev = E.encode([c["query"].get("underlying_event", c["headline"]) for c in live])
        for i, c in enumerate(live):
            for j in range(i):
                if not live[j].get("merged_into") and float(ev[i] @ ev[j]) >= DEDUPE_SIM:
                    keep, drop = (live[j], c) if live[j]["importance"]["importance_score"] >= \
                        c["importance"]["importance_score"] else (c, live[j])
                    drop["merged_into"] = keep["headline"]
    order = sorted([c for c in live if not c.get("merged_into")],
                   key=lambda c: -c["importance"]["importance_score"])
    rec["evaluation_order"] = [c["headline"] for c in order]
    ck("importance")

    # 5. CROSS-SOURCE COVERAGE (all candidates first)
    for oi, c in enumerate(order):
        q = c["query"]
        qv = E.encode(sm.query_texts(q), query=True)
        sims = (vecs @ qv.T).max(axis=1) if len(chunks) else np.zeros(0)
        pats = sm.alias_patterns(q)
        per_vid = {}
        for i, ch in enumerate(chunks):
            hits = sum(1 for p in pats if p.search(ch["text"]))
            if sims[i] >= RETRIEVAL_MIN_SIM or hits >= 2:
                per_vid.setdefault(ch["video_id"], []).append((float(sims[i]) + 0.03 * min(hits, 3), i))
        ranked_v = sorted(per_vid.items(), key=lambda kv: -max(s for s, _ in kv[1]))
        picked, seen_ch = [], set()
        for vid, lst in ranked_v:                       # channel diversity first
            ch0 = chunks[lst[0][1]]["channel_id"]
            if ch0 not in seen_ch:
                picked.append((vid, lst))
                seen_ch.add(ch0)
        for vid, lst in ranked_v:
            if len(picked) >= MAX_ADJUDICATE_PER_STORY:
                break
            if (vid, lst) not in picked:
                picked.append((vid, lst))
        picked = picked[:MAX_ADJUDICATE_PER_STORY]
        verdicts = []
        c["coverage"] = {"videos_evaluated": 0, "verdicts": verdicts, "status": "in_progress"}
        for vi, (vid, lst) in enumerate(picked):
            idx = [i for _, i in sorted(lst, reverse=True)[:4]]
            ex = [chunks[i] for i in sorted(idx, key=lambda i: chunks[i]["start"])]
            u = next(x for x in uni if x["video_id"] == vid)
            v = sm.adjudicate(L, q, {"title": u["title"], "channel": u["channel"],
                                     "published_at": u["published_at"]}, ex, today=today)
            v.update(video_id=vid, canonical_url=u["canonical_url"], channel=u["channel"],
                     channel_id=u["channel_id"], title=u["title"], published_at=u["published_at"],
                     layout_eligible=u["layout_eligible"], transcript_sha256=u["transcript_sha256"],
                     transcript_method=u["transcript_method"],
                     excerpts=[{"chunk_id": x["chunk_id"], "start": x["start"], "end": x["end"],
                                "text": x["text"]} for x in ex],
                     retrieval_score=round(max(s for s, _ in lst), 3))
            verdicts.append(v)
            c["coverage"]["videos_evaluated"] = len(verdicts)
            ck("adjudicate", candidate=oi, of=len(order), video=vi, of_videos=len(picked))
        same = [v for v in verdicts if v["counted_as_same_event"]]
        cov_ch = sorted({v["channel_id"] for v in same})
        lay_ch = sorted({v["channel_id"] for v in same if v["layout_eligible"]})
        c["coverage"].update(status="done", same_event_videos=len(same), independent_channels=len(cov_ch),
                             inconclusive=sum(1 for v in verdicts if v["verdict"] == "INCONCLUSIVE"),
                             channels=[by_cid.get(x, {}).get("display_name", x) for x in cov_ch],
                             layout_eligible_channels=[by_cid[x]["display_name"] for x in lay_ch])
        cur = sm.transcript_currentness(verdicts)            # E1/E9: transcripts decide currentness
        c["currentness"] = cur
        if cur["status"] == "CURRENT" and c.get("model_date_hint", {}).get("older_than_window"):
            c.setdefault("flags", []).append("model date hint contradicts transcript evidence (hint ignored)")
        log(f"  [{c['importance']['importance_score']:.2f}] {c['headline'][:70]} -> coverage "
            f"{len(cov_ch)} ch ({len(lay_ch)} layout-eligible), currentness {cur['status']}")
        if cur["status"] != "CURRENT":
            c["decision"] = f"inconclusive: currentness {cur['reason']}"
        elif len(cov_ch) < MIN_COVERAGE_CHANNELS:
            c["decision"] = f"rejected: coverage {len(cov_ch)} < {MIN_COVERAGE_CHANNELS} independent channels"
        elif len(lay_ch) < MIN_LAYOUT_CHANNELS:
            c["decision"] = (f"rejected: only {len(lay_ch)} layout-eligible channel(s) with evidence "
                             f"(clips need >= {MIN_LAYOUT_CHANNELS}); editorial coverage {len(cov_ch)}")
        else:
            c["decision"] = "coverage_qualified"
        ck("coverage", candidate=oi, of=len(order))

    # 6. E5: one GPU0 swap -> word-level transcripts for every coverage-qualified candidate
    qualified = [c for c in order if c.get("decision") == "coverage_qualified"]
    need = {}
    for c in qualified:
        for v in c["coverage"]["verdicts"]:
            if v["counted_as_same_event"] and v["layout_eligible"]:
                need[v["video_id"]] = v["channel_id"]
    words, arb = {}, {"videos": sorted(need)}
    rec["gpu_arbitration"] = arb
    todo = [vid for vid in need if (ts.canonical_transcript(vid) or {}).get("transcript_method") != "whisper_words"]
    for vid in need:
        if vid not in todo:
            words[vid] = (ts.canonical_transcript(vid), "cached")
    if todo:
        try:
            arb["release"] = sm.release_gpu0_for_whisper(L, log=log)
        except RuntimeError as e:
            arb["release_error"] = str(e)
            for vid in todo:
                words[vid] = (None, f"infra: {e}")
        else:
            for vid in todo:
                r, st = ts.acquire(vid, channel=by_cid[need[vid]], allow_whisper=True, prefer_words=True)
                err = ts.LAST_ERROR.get(vid, "")
                if r is None or r.get("transcript_method") != "whisper_words":
                    words[vid] = (None, f"infra: {err}" if _infra_error(err) else f"failed: {st} {err}")
                else:
                    words[vid] = (r, st)
                ck("word_transcripts", video=vid)
            ts.release_whisper()
            arb["after_whisper"] = sm.gpu0_memory()
    arb["results"] = {vid: st for vid, (r, st) in words.items()}
    ck("word_transcripts_done")

    # 7. CLIP QUALITY
    for oi, c in enumerate(qualified):
        cq = _clip_quality(c, [v for v in c["coverage"]["verdicts"] if v["counted_as_same_event"]],
                           E, L, by_cid, words, log)
        c["clip_quality"] = cq
        c["decision"] = "producible" if cq["producible"] else (
            ("INFRA_HOLD: " if cq.get("infra") else "rejected: ") + cq["reason"])
        ck("clip_quality", candidate=oi, of=len(qualified))

    producible = [c for c in order if c.get("decision") == "producible"]
    infra = [c for c in order if str(c.get("decision", "")).startswith("INFRA_HOLD")]
    L.stop()
    if embedder is None:
        E.close()
    rec["seconds"] = round(time.time() - t0)
    if not producible:
        rec["decision"] = ("HOLD (infrastructure): no producible candidate and "
                           f"{len(infra)} candidate(s) blocked by GPU/transcription infrastructure"
                           if infra else "HOLD: no candidate is producible (see candidates[].decision)")
        ck("done")
        raise NoProducibleStory(rec["decision"])
    win = max(producible, key=lambda c: (c["importance"]["importance_score"],
                                         c["coverage"]["independent_channels"],
                                         c["clip_quality"]["mean_chosen_score"]))
    rec["selected"] = {"headline": win["headline"], "origin": win["origin"],
                       "short_label": win["query"].get("short_label"),
                       "underlying_event": win["query"].get("underlying_event"),
                       "currentness": win["currentness"],
                       "model_date_hint": win.get("model_date_hint"),
                       "flags": win.get("flags", []),
                       "importance": win["importance"],
                       "coverage": {k: v for k, v in win["coverage"].items() if k != "verdicts"},
                       "clip_quality": {k: v for k, v in win["clip_quality"].items() if k != "candidates"},
                       "why": ("highest story importance among producible candidates; ties broken by "
                               "coverage then clip quality"),
                       "other_producible": [c["headline"] for c in producible if c is not win],
                       "infra_held": [c["headline"] for c in infra]}
    rec["decision"] = "SELECTED"
    chosen = win["clip_quality"]["chosen"]
    _write(run_dir, "passages.json", {"story": win["query"], "passages": win["clip_quality"]["candidates"],
                                      "chosen": chosen,
                                      "channels": sorted({p["channel"] for p in chosen})})
    srcs, seen = [], set()
    for p in chosen:
        if p["video_id"] in seen:
            continue
        seen.add(p["video_id"])
        srcs.append({"video_id": p["video_id"], "channel": p["channel"], "title": p["title"],
                     "url": ts.canonical_url(p["video_id"]), "published": p["published_at"],
                     "handle": p.get("handle", ""), "tier": p.get("tier", 9),
                     "transcript_sha256": p["transcript_sha256"]})
    _write(run_dir, "sources.json", srcs)
    ck("done")
    return win["query"].get("short_label") or win["headline"], rec


def _clip_quality(c, same, E, L, by_cid, words, log):
    import story_semantics as sm
    q = c["query"]
    qv = E.encode([q.get("underlying_event", c["headline"])], query=True)[0]
    cands, infra, missing, anchors = [], [], [], []
    for v in same:
        if not v["layout_eligible"]:
            continue                      # editorial evidence only; never a clip
        ch = by_cid[v["channel_id"]]
        r, st = words.get(v["video_id"], (None, "not prepared"))
        if r is None:
            (infra if str(st).startswith("infra") else missing).append((v["video_id"], st))
            continue
        a_rec = {"video_id": v["video_id"], "channel": ch["display_name"], "quote": v["evidence_quote"]}
        anchors.append(a_rec)
        ws = r.get("words") or []
        if not ws:
            a_rec["result"] = "no word timestamps in record"
            missing.append((v["video_id"], "no word timestamps"))
            continue
        spans = [ts.parse_chunk_id(x)[1:] for x in v["supporting_chunk_ids"]]
        anc = align_quote(v["evidence_quote"], ws, max(0, min(a for a, _ in spans) - ANCHOR_PAD_S),
                          max(b for _, b in spans) + ANCHOR_PAD_S)
        if anc is None:
            a_rec["result"] = "verified quote not found in word timestamps (no window)"
            continue
        a_rec.update(anchor_start=anc["start"], anchor_end=anc["end"], match_ratio=anc["ratio"], windows={})
        sents = _word_sentences(ws)
        for lo, hi, kind in ((HOOK_MIN_S, HOOK_MAX_S, "hook"), (CLIP_MIN_S, CLIP_MAX_S, "clip")):
            w, why, span = anchored_window(ws, sents, anc, lo, hi)
            a_rec.setdefault("spans", {})[kind] = {**span, "valid": w is not None, "why": why}
            if w is None:
                a_rec["windows"][kind] = f"none: {why}"
                continue
            dup = next((p for p in cands if p["video_id"] == v["video_id"] and p["kind"] == kind and
                        not (w["end"] <= p["start"] or w["start"] >= p["end"])), None)
            if dup:
                a_rec["windows"][kind] = f"deduped: overlaps {dup['source_chunk_id']}"
                continue
            a_rec["windows"][kind] = f"{w['start']:.2f}-{w['end']:.2f} ({w['duration']} s)"
            cands.append({**w, "kind": kind, "video_id": v["video_id"], "channel": ch["display_name"],
                          "channel_id": ch["channel_id"], "handle": ch.get("yt_handle", ""),
                          "tier": ch.get("tier", 9), "title": v["title"], "published_at": v["published_at"],
                          "canonical_url": v["canonical_url"], "transcript_sha256": r["transcript_sha256"],
                          "transcript_method": r["transcript_method"],
                          "anchor_quote": v["evidence_quote"],
                          "source_chunk_id": ts.chunk_id(v["video_id"], w["start"], w["end"])})
    base = {"infra_failures": infra, "other_failures": missing, "anchors": anchors,
            "window_rule": "quote-anchored, whole sentences, boundary start, overlap-deduped (code picks the cut)"}
    if infra and len({p["channel"] for p in cands}) < MIN_LAYOUT_CHANNELS:
        return {**base, "producible": False, "infra": True, "candidates": cands, "chosen": [],
                "mean_chosen_score": 0,
                "reason": f"word-level transcription blocked by infrastructure for {[v for v, _ in infra]}"}
    if not cands:
        return {**base, "producible": False, "reason": "no quote-anchored boundary window in layout-eligible evidence",
                "candidates": [], "chosen": [], "mean_chosen_score": 0}
    pv = E.encode([p["text"] for p in cands])
    for p, vv in zip(cands, pv):
        p["relevance"] = round(float(vv @ qv), 3)
        p["form"] = _form_score(p["text"])
    pre = sorted(cands, key=lambda p: -(p["relevance"] + p["form"] / 100))
    shortlist, per = [], {}
    for p in pre:
        k = (p["video_id"], p["kind"])
        if per.get(k, 0) < 4:
            shortlist.append(p)
            per[k] = per.get(k, 0) + 1
        if len(shortlist) >= 24:
            break
    for i, p in enumerate(shortlist):
        p["pid"] = f"p{i}"
    rating_errors = []
    for b in range(0, len(shortlist), 8):
        ratings, err = sm.rate_passages(L, q, shortlist[b:b + 8])
        if err:
            rating_errors.append(err)
        for p in shortlist[b:b + 8]:
            s, why = ratings.get(p["pid"], (0.0, "unrated"))
            p["clip_score"], p["clip_reason"] = s, why
    base["rating_errors"] = rating_errors
    hooks = sorted([p for p in shortlist if p["kind"] == "hook" and p["clip_score"] >= HOOK_MIN_SCORE],
                   key=lambda p: (-p["clip_score"], -p["relevance"]))
    clips = sorted([p for p in shortlist if p["kind"] == "clip" and p["clip_score"] >= CLIP_MIN_SCORE],
                   key=lambda p: (-p["clip_score"], -p["relevance"]))
    if not hooks:
        return {**base, "producible": False, "candidates": shortlist, "chosen": [], "mean_chosen_score": 0,
                "reason": (f"no hook passage scored >= {HOOK_MIN_SCORE}" +
                           (" (clip ratings inconclusive: LLM output unparseable)" if rating_errors else ""))}
    def assemble(hook):
        chosen = [hook]
        for p in clips:
            if len(chosen) >= 1 + N_CLIPS:
                break
            if any(x["video_id"] == p["video_id"] and not (p["end"] <= x["start"] or p["start"] >= x["end"])
                   for x in chosen) or sum(1 for x in chosen[1:] if x["channel"] == p["channel"]) >= 2:
                continue                                  # overlap dedupe / per-channel cap
            chosen.append(p)
        return chosen

    # hooks in score order; the first whose non-overlapping set is producible wins (a hook must not
    # consume the only qualifying clip of a channel). Falls back to the top hook for the record.
    chosen = None
    for h in hooks:
        trial = assemble(h)
        if len(trial) >= 3 and len({p["channel"] for p in trial}) >= MIN_LAYOUT_CHANNELS:
            chosen = trial
            break
    chosen = chosen or assemble(hooks[0])
    chans = {p["channel"] for p in chosen}
    if len(chosen) < 3 or len(chans) < MIN_LAYOUT_CHANNELS:
        return {**base, "producible": False, "candidates": shortlist, "chosen": [], "mean_chosen_score": 0,
                "infra": bool(infra),
                "reason": f"clip quality: {len(chosen) - 1} usable clips across {len(chans)} channel(s)" +
                          (f"; infrastructure-blocked videos {[v for v, _ in infra]}" if infra else "")}
    out = []
    for p in chosen:   # select_passages input contract (full-video seconds)
        out.append({"video_id": p["video_id"], "channel": p["channel"], "handle": p["handle"],
                    "title": p["title"], "tier": p["tier"], "start": round(p["start"], 2),
                    "end": round(p["end"], 2), "text": p["text"], "duration": p["duration"],
                    "score": round(p["clip_score"] * 20 + p["relevance"], 2),
                    "clip_score": p["clip_score"], "relevance": p["relevance"],
                    "published_at": p["published_at"], "canonical_url": p["canonical_url"],
                    "transcript_sha256": p["transcript_sha256"], "source_chunk_id": p["source_chunk_id"]})
    return {**base, "producible": True, "reason": "ok", "candidates": shortlist, "chosen": out,
            "mean_chosen_score": round(sum(p["clip_score"] for p in chosen) / len(chosen), 2),
            "channels": sorted(chans)}


def _write(run_dir, name, obj):
    p = os.path.join(run_dir, name)
    with open(p + ".tmp", "w") as f:
        json.dump(obj, f, indent=1, default=str, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(p + ".tmp", p)
