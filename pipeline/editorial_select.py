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
    return channel.get("layout_status") == "approved" and bool(channel.get("channel_id"))


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

def _sentence_windows(segs, lo, hi, region):
    """Windows that start at a sentence start and end at a sentence end, within region."""
    out = []
    a0, a1 = region
    starts = [i for i, s in enumerate(segs)
              if a0 <= s["start"] <= a1 and (i == 0 or segs[i - 1]["text"].rstrip().endswith((".", "!", "?")))]
    for i in starts:
        text = []
        for j in range(i, len(segs)):
            text.append(segs[j]["text"])
            d = segs[j]["end"] - segs[i]["start"]
            if d > hi:
                break
            if d >= lo and segs[j]["text"].rstrip().endswith((".", "!")):
                out.append({"start": segs[i]["start"], "end": segs[j]["end"],
                            "duration": round(d, 2), "text": " ".join(text)})
    return out


def _form_score(text):
    from rank import _score_passage
    return _score_passage(text, [])


# ── main ──

def select_story(run_dir, log=print, embedder=None, llm=None, universe_fn=None,
                 stories_path=STORIES_PATH, topup=True):
    import story_semantics as sm
    from transcript_ingest import universe as ingest_universe
    t0 = time.time()
    today = _today()
    with open(CHANNELS_PATH) as f:
        registry = json.load(f)
    by_cid = {c["channel_id"]: c for c in registry if c.get("channel_id")}
    rec = {"law": "titles/metadata are discovery hints; transcripts establish story identity",
           "started": ts.now_iso(), "universe_hours": UNIVERSE_HOURS,
           "editorial_channels": sorted(c["display_name"] for c in by_cid.values() if c.get("enabled", True)),
           "layout_eligible_channels": sorted(c["display_name"] for c in by_cid.values()
                                              if layout_eligible(c)),
           "params": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float))}}

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
    ts._WHISPER = None  # release the editorial Whisper model before loading the LLM

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
    rec["embedding_model"] = E.model_id
    rec["n_chunks"] = len(chunks)
    log(f"  chunks: {len(chunks)} from {rec['universe_summary']['with_transcript']} transcripts")

    L = llm or sm.LocalLLM().start()
    rec["llm"] = {"model": L.model, "host": L.host, "serve_env": getattr(L, "serve_env", None)}

    # 3. candidates: story engine (all) + emergent clusters
    with open(stories_path) as f:
        stories = json.load(f)
    rec["story_engine"] = story_engine_status(stories, stories_path)
    cands = []
    for s in stories.get("stories", []):
        cands.append({"origin": "story_engine", "engine_rank": s.get("rank"),
                      "engine_score": s.get("overall_score"), "headline": s.get("headline"),
                      "summary": s.get("summary"), "source_domain": s.get("source_domain"),
                      "age_h": (s.get("freshness_minutes") or 0) / 60})
    emergent = []
    for g in sm.emergent_clusters(chunks, vecs):
        lab = sm.label_cluster(L, chunks, vecs, g, today)
        ages = [chunks[i]["age_h"] for i in g["chunk_idx"]]
        emergent.append({"channels": g["channels"], "n_chunks": len(g["chunk_idx"]), "label": lab})
        if lab.get("is_specific_event") and lab.get("headline"):
            cands.append({"origin": "transcript_cluster", "headline": lab["headline"],
                          "summary": lab.get("summary", ""), "source_domain": "transcript cluster",
                          "cluster_channels": g["channels"], "cluster_chunk_ids": lab.get("excerpt_chunk_ids"),
                          "age_h": min(ages) if ages else None})
    rec["emergent_clusters"] = emergent
    log(f"  candidates: {len(cands)} ({sum(c['origin'] == 'transcript_cluster' for c in cands)} emergent)")

    # 4. STORY IMPORTANCE (derive semantic query per candidate)
    for c in cands[:MAX_CANDIDATES + len(emergent)]:
        q = sm.derive_story_query(L, c, today)
        c["query"] = q
        imp = {"llm_importance": q.get("importance"), "llm_bitcoin_relevance": q.get("bitcoin_relevance"),
               "is_specific_event": q.get("is_specific_event"), "recency": _recency(c.get("age_h")),
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
        c["importance_gate"] = gate
    # merge near-duplicate candidates (same underlying event)
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

    # 5. CROSS-SOURCE COVERAGE  6. CLIP QUALITY
    for c in order:
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
        for vid, lst in picked:
            idx = [i for _, i in sorted(lst, reverse=True)[:4]]
            ex = [chunks[i] for i in sorted(idx, key=lambda i: chunks[i]["start"])]
            u = next(x for x in uni if x["video_id"] == vid)
            v = sm.adjudicate(L, q, {"title": u["title"], "channel": u["channel"]}, ex)
            v.update(video_id=vid, canonical_url=u["canonical_url"], channel=u["channel"],
                     channel_id=u["channel_id"], title=u["title"], published_at=u["published_at"],
                     layout_eligible=u["layout_eligible"], transcript_sha256=u["transcript_sha256"],
                     transcript_method=u["transcript_method"],
                     excerpt_spans=[(x["chunk_id"], x["start"], x["end"]) for x in ex],
                     retrieval_score=round(max(s for s, _ in lst), 3))
            verdicts.append(v)
        same = [v for v in verdicts if v["counted_as_same_event"]]
        cov_ch = sorted({v["channel_id"] for v in same})
        lay_ch = sorted({v["channel_id"] for v in same if v["layout_eligible"]})
        c["coverage"] = {"videos_evaluated": len(verdicts), "same_event_videos": len(same),
                         "independent_channels": len(cov_ch),
                         "channels": [by_cid.get(x, {}).get("display_name", x) for x in cov_ch],
                         "layout_eligible_channels": [by_cid[x]["display_name"] for x in lay_ch],
                         "verdicts": verdicts}
        log(f"  [{c['importance']['importance_score']:.2f}] {c['headline'][:70]} -> coverage "
            f"{len(cov_ch)} ch ({len(lay_ch)} layout-eligible)")
        if len(cov_ch) < MIN_COVERAGE_CHANNELS:
            c["decision"] = f"rejected: coverage {len(cov_ch)} < {MIN_COVERAGE_CHANNELS} independent channels"
            continue
        if len(lay_ch) < MIN_LAYOUT_CHANNELS:
            c["decision"] = (f"rejected: only {len(lay_ch)} layout-eligible channel(s) with evidence "
                             f"(clips need >= {MIN_LAYOUT_CHANNELS}); editorial coverage {len(cov_ch)}")
            continue
        c["clip_quality"] = _clip_quality(c, same, chunks, E, L, by_cid, log)
        if c["clip_quality"]["producible"]:
            c["decision"] = "producible"
        else:
            c["decision"] = "rejected: " + c["clip_quality"]["reason"]

    producible = [c for c in order if c.get("decision") == "producible"]
    rec["candidates"] = [{k: v for k, v in c.items()} for c in cands]
    rec["evaluation_order"] = [c["headline"] for c in order]
    L.stop()
    if embedder is None:
        E.close()
    rec["seconds"] = round(time.time() - t0)
    if not producible:
        rec["decision"] = "HOLD: no candidate is producible (see candidates[].decision)"
        _write(run_dir, "TOPIC_SELECTION.json", rec)
        raise NoProducibleStory(rec["decision"])
    win = max(producible, key=lambda c: (c["importance"]["importance_score"],
                                         c["coverage"]["independent_channels"],
                                         c["clip_quality"]["mean_chosen_score"]))
    rec["selected"] = {"headline": win["headline"], "origin": win["origin"],
                       "short_label": win["query"].get("short_label"),
                       "underlying_event": win["query"].get("underlying_event"),
                       "importance": win["importance"],
                       "coverage": {k: v for k, v in win["coverage"].items() if k != "verdicts"},
                       "clip_quality": {k: v for k, v in win["clip_quality"].items() if k != "candidates"},
                       "why": ("highest story importance among producible candidates; ties broken by "
                               "coverage then clip quality"),
                       "other_producible": [c["headline"] for c in producible if c is not win]}
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
    _write(run_dir, "TOPIC_SELECTION.json", rec)
    return win["query"].get("short_label") or win["headline"], rec


def _clip_quality(c, same, chunks, E, L, by_cid, log):
    import story_semantics as sm
    q = c["query"]
    qv = E.encode([q.get("underlying_event", c["headline"])], query=True)[0]
    cands = []
    for v in same:
        if not v["layout_eligible"]:
            continue
        ch = by_cid[v["channel_id"]]
        # word-timestamped whisper -> sentence segments for sentence-bounded passages
        # (created at most once per video, immutable)
        r, st = ts.acquire(v["video_id"], channel=ch, allow_whisper=True, prefer_words=True)
        if not r or r["transcript_method"] != "whisper_words":
            continue
        spans = [s for x in v["supporting_chunk_ids"] for s in [ts.parse_chunk_id(x)[1:]]]
        region = (max(0, min(a for a, _ in spans) - 60), max(b for _, b in spans) + 60)
        for lo, hi, kind in ((HOOK_MIN_S, HOOK_MAX_S, "hook"), (CLIP_MIN_S, CLIP_MAX_S, "clip")):
            for w in _sentence_windows(r["segments"], lo, hi, region):
                if w["text"].rstrip().endswith("?"):
                    continue
                cands.append({**w, "kind": kind, "video_id": v["video_id"], "channel": ch["display_name"],
                              "channel_id": ch["channel_id"], "handle": ch.get("yt_handle", ""),
                              "tier": ch.get("tier", 9), "title": v["title"], "published_at": v["published_at"],
                              "canonical_url": v["canonical_url"], "transcript_sha256": r["transcript_sha256"],
                              "transcript_method": r["transcript_method"],
                              "source_chunk_id": ts.chunk_id(v["video_id"], w["start"], w["end"])})
    if not cands:
        return {"producible": False, "reason": "no sentence-bounded passages in layout-eligible evidence",
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
    for b in range(0, len(shortlist), 8):
        ratings = sm.rate_passages(L, q, shortlist[b:b + 8])
        for p in shortlist[b:b + 8]:
            s, why = ratings.get(p["pid"], (0.0, "unrated"))
            p["clip_score"], p["clip_reason"] = s, why
    hooks = sorted([p for p in shortlist if p["kind"] == "hook" and p["clip_score"] >= HOOK_MIN_SCORE],
                   key=lambda p: (-p["clip_score"], -p["relevance"]))
    clips = sorted([p for p in shortlist if p["kind"] == "clip" and p["clip_score"] >= CLIP_MIN_SCORE],
                   key=lambda p: (-p["clip_score"], -p["relevance"]))
    if not hooks:
        return {"producible": False, "reason": f"no hook passage scored >= {HOOK_MIN_SCORE}",
                "candidates": shortlist, "chosen": [], "mean_chosen_score": 0}
    hook = hooks[0]
    chosen = [hook]

    def overlaps(p):
        return any(x["video_id"] == p["video_id"] and not (p["end"] <= x["start"] or p["start"] >= x["end"])
                   for x in chosen)
    for p in clips:
        if len(chosen) >= 1 + N_CLIPS:
            break
        if overlaps(p) or sum(1 for x in chosen[1:] if x["channel"] == p["channel"]) >= 2:
            continue
        chosen.append(p)
    chans = {p["channel"] for p in chosen}
    if len(chosen) < 3 or len(chans) < MIN_LAYOUT_CHANNELS:
        return {"producible": False, "candidates": shortlist, "chosen": [], "mean_chosen_score": 0,
                "reason": f"clip quality: {len(chosen) - 1} usable clips across {len(chans)} channel(s)"}
    out = []
    for p in chosen:   # select_passages input contract (full-video seconds)
        out.append({"video_id": p["video_id"], "channel": p["channel"], "handle": p["handle"],
                    "title": p["title"], "tier": p["tier"], "start": round(p["start"], 2),
                    "end": round(p["end"], 2), "text": p["text"], "duration": p["duration"],
                    "score": round(p["clip_score"] * 20 + p["relevance"], 2),
                    "clip_score": p["clip_score"], "relevance": p["relevance"],
                    "published_at": p["published_at"], "canonical_url": p["canonical_url"],
                    "transcript_sha256": p["transcript_sha256"], "source_chunk_id": p["source_chunk_id"]})
    return {"producible": True, "reason": "ok", "candidates": shortlist, "chosen": out,
            "mean_chosen_score": round(sum(p["clip_score"] for p in chosen) / len(chosen), 2),
            "channels": sorted(chans)}


def _write(run_dir, name, obj):
    p = os.path.join(run_dir, name)
    with open(p + ".tmp", "w") as f:
        json.dump(obj, f, indent=1, default=str, ensure_ascii=False)
    os.replace(p + ".tmp", p)
