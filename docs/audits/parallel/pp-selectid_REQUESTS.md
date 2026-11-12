# pp-selectid — REQUESTS for the integrator (files this session does not own)

Base: c1451047 (hardening-redteam at the split). Every item names the file, the function and the exact change. R1 is
the wiring (an exact patch, `git apply --check` clean on c1451047; extract it with
`tests/select_by_id/smoke_wiring_patch.py --extract FILE`); the smoke test applies it to a temporary copy of
pipeline/ and runs the patched `editorial_select.select_story` end to end on the protected preview's frozen
transcripts with a scripted model (no GPU, no network): `python3 tests/select_by_id/smoke_wiring_patch.py`.

Status after the orchestrator's 02:30 order (law L-w 3): story-first is KEPT as a preferred package type when >= 2
channels cover one development, so R1 stays the selector of that type. The moments-first wiring (phase 2) comes in its
own section, added when phase 2 is built. Both cycle-2 audit dispositions are in
docs/audits/parallel/pp-selectid_audit/C2_DISPOSITIONS.md.

## R1 WIRING: editorial_select pools by id; SELECT = hook + >= 2 clips

- `pipeline/editorial_select.py` `_select_story`: the closures `label_clusters` and `evaluate` and the pool loop /
  winner / writes (c1451047 lines 704-976) are replaced by `select_by_id.run_pools` over the same DEC-13 pools
  (channel_clusters_48h -> channel_clusters_72h -> wire_headlines, lazily). Unchanged: universe, chunks, embeddings,
  clusters and the free Bitcoin screen (steps 1-3).
- Order: groups are offered widest first (D-f); at most `SB_MAX_STORY_CALLS` = 12 story calls per run (D-g).
- Word pass (E5, law L-e): ONE per pool, for the on-screen videos of all its accepted stories (one GPU0 swap, law
  L-r); the backtest's frozen `words_fn` instead, where only a full-video STORE record counts (audit C2: a run's
  window transcript is refused, with or without R4).
- Independent checks: `select_by_id.ModelChecks(L)` runs today's `verify_support` on EVERY story sentence with the
  claim as the event, and `verify_reaction` (D4 c) on every non-statement sentence of a range. Both use today's
  prompts and validators through `LocalLLM.chat_json`.
- Cache: model replies are cached ONLY when validated: accepted, or declined with every check passed
  (`Recorder(validated_only=True)`; DEC-13 e / law L-l). Key: (model + weights digest + context, prompt, max_tokens,
  seed), under `data/editorial/llm_cache/select_by_id`.
- TOPIC_SELECTION:
  - keeps `pools`, with `word_pass` and `stopped` per pool;
  - gains `select_by_id`: every group, rows offered, every attempt with its raw reply, verdict and checks;
  - gains `selected` = {headline: the claim sentence VERBATIM, claim, evidence in the story ledger's form,
    eligibility, pool, origin};
  - every screened cluster's ledger entry, and every wire candidate, gets its `gate` / `decision` (DEC-13 d),
    including "story accepted; line-up not asked: another group of the pool was selected first".
- HOLD: "HOLD (infrastructure)" when the GPU0 release, the word pass or every evaluated group's model call failed.
  Otherwise "HOLD: no candidate is producible".
- Output: passages.json = select_by_id.to_passages (source text and times only; `passages` = `chosen`: no
  model-written fallback pool). Returns the claim as the label.
- `pipeline/select_passages.py` `select_and_build_edl`: success needs >= 2 clip segments (was >= 1; GPT-select F08;
  eligibility N_CLIPS; edl_rules R5 would HOLD it later anyway).
- Left in place, unused after R1 (their unit tests still run; retire them with their tests in a later batch):
  `_decide_coverage`, `_same_event_groups`, `_merge_event`, `_clip_quality`, `_close_cluster_ledger`,
  `second_verified_quote`, `expanded_window`, `anchored_window`, `repair_window`, `adjacent_admissible`,
  `sentence_on_event`; story_semantics' `label_cluster`, `derive_story_query`, `adjudicate`, `rate_passages`.
- Tests that drive `select_story` end to end with the chat_json-routing fakes (`test_editorial_robust`
  Orchestration, `test_dec13_clusters`, `test_same_event_merge` end-to-end parts, `test_story_ledger` select
  parts, `test_window_review` RoutedLLM, `test_sentence_windows` orchestration parts, `test_backtest`) need a fake
  with `_post(prompt, max_tokens, seed)` answering the two id prompts (see tests/select_by_id/smoke_wiring_patch.py
  `ScriptedLLM`); their per-function tests are unaffected.

<!-- PATCH BEGIN -->
```diff
--- a/pipeline/editorial_select.py
+++ b/pipeline/editorial_select.py
@@ -41,6 +41,7 @@
 UNIVERSE_HOURS = 72
 TOPUP_MAX_WHISPER_HOURS = 8.0      # in-run acquisition for uploads the background ingest missed
 MAX_CANDIDATES = 24
+SB_MAX_STORY_CALLS = 12          # pp-selectid: story calls per run (widest clusters first; a budget the integrator tunes with measured gemma3 latency, law L-p)
 BTC_RELEVANCE_MIN = 3
 RETRIEVAL_MIN_SIM = 0.55
 MAX_ADJUDICATE_PER_STORY = 14
@@ -701,269 +702,144 @@
         + ", ".join(f"{sum(e['screen'] == t for e in emergent)} {t}" for t in TIERS)
         + f", {sum(e['screen'] not in TIERS for e in emergent)} stopped (no model call)")
 
-    def label_clusters(tier):
-        """DEC-13 a: the candidates of one recency tier; model calls start here (label + verified quote)."""
-        out = []
-        for gi, (g, entry) in enumerate(zip(groups, emergent)):
-            if entry["screen"] != tier:
-                continue
-            lab = sm.label_cluster(L, chunks, vecs, g, today)
-            ages = [chunks[i]["age_h"] for i in g["chunk_idx"]]
-            entry.update(label=lab, claim=lab.get("headline"))
-            if not lab.get("current_ok"):
-                entry["rejected"] = ("no verified current-development evidence"
-                                     if lab.get("is_specific_event") else
-                                     lab.get("error") or "not a specific current event")
-                entry["gate"] = f"label: {entry['rejected']}"
-            else:
-                cdq = lab.get("current_development_chunk_id")
-                entry["current_development_evidence"] = {
-                    "chunk_id": cdq, "quote": lab.get("current_development_quote"),
-                    "channel": by_chunk.get(cdq, {}).get("channel_name"),
-                    "canonical_url": by_chunk.get(cdq, {}).get("canonical_url")}
-                out.append({"origin": "transcript_cluster", "headline": lab["headline"],
-                            "summary": lab.get("summary", ""), "source_domain": "transcript cluster",
-                            "cluster_channels": g["channels"], "cluster_chunk_ids": lab.get("excerpt_chunk_ids"),
-                            "cluster_index": gi, "cluster_tier": tier,
-                            "cluster_member_chunk_ids": entry["member_chunk_ids"],
-                            "current_development_evidence": entry["current_development_evidence"],
-                            "age_h": min(ages) if ages else None,
-                            # D1: upload time of the video holding the verified current-development quote
-                            "source_published": by_chunk.get(cdq, {}).get("published_at")})
-                cands.append(out[-1])                    # in the record at once (forensic checkpoints)
-            ck("emergent", tier=tier, cluster=gi)
-        log(f"  {tier} clusters: {sum(e['screen'] == tier for e in emergent)} labelled, {len(out)} candidate(s)")
-        return out
-
-    def evaluate(pname, pool):
-        """Steps 4-7 on one pool of candidates; returns the pool's evaluation order (merged candidates included)."""
-        # 4. STORY IMPORTANCE (+ E1 currentness gate)
-        for ci, c in enumerate(pool):
-            try:
-                q = sm.derive_story_query(L, c, today)
-            except sm.LLMParseError as e:
-                c["importance_gate"] = ["inconclusive: story-query derivation failed (LLM output unparseable)"]
-                c["llm_error"] = {"error": str(e), "llm_attempts": e.attempts}
-                ck("derive", pool=pname, candidate=ci, of=len(pool))
-                continue
-            c["query"] = q
-            imp = {"llm_importance": q.get("importance"), "llm_bitcoin_relevance": q.get("bitcoin_relevance"),
-                   "is_specific_event": q.get("is_specific_event"), "model_event_date": q.get("event_date"),
-                   "model_event_recency": q.get("event_recency"), "recency": _recency(c.get("age_h")),
-                   "engine_score": c.get("engine_score"),
-                   "engine_score_note": rec["story_engine"]["llm_legs"] if c["origin"] == "story_engine" else None}
-            try:
-                imp["importance_score"] = round(0.45 * float(q.get("importance", 0)) / 5 +
-                                                0.35 * float(q.get("bitcoin_relevance", 0)) / 5 +
-                                                0.20 * imp["recency"], 3)
-            except Exception:
-                imp["importance_score"] = 0.0
-            c["importance"] = imp
-            gate = []
-            if (q.get("bitcoin_relevance") or 0) < BTC_RELEVANCE_MIN:
-                gate.append(f"bitcoin_relevance {q.get('bitcoin_relevance')} < {BTC_RELEVANCE_MIN}")
-            if not q.get("is_specific_event", True):
-                gate.append("not a specific event")
-            # D1: publish metadata dates the event; the model date is a tiebreaker only without it
-            g = sm.grounded_event_date(q, _parse_ts(c.get("source_published")), now, UNIVERSE_HOURS)
-            c["event_date_grounding"] = g
-            if g["model_date_discarded"]:
-                log(f"  D1/E9 model date discarded ({g['model_date']['status']}): {c['headline'][:70]}")
-            if g["stale"]:
-                gate.append(g["stale_reason"])
-            c["importance_gate"] = gate
-            ck("derive", pool=pname, candidate=ci, of=len(pool))
-        live = [c for c in pool if "query" in c and not c["importance_gate"]]
-        if live:
-            ev = E.encode([c["query"].get("underlying_event", c["headline"]) for c in live])
-            for i, c in enumerate(live):
-                for j in range(i):
-                    if not live[j].get("merged_into") and float(ev[i] @ ev[j]) >= DEDUPE_SIM:
-                        keep, drop = (live[j], c) if live[j]["importance"]["importance_score"] >= \
-                            c["importance"]["importance_score"] else (c, live[j])
-                        drop["merged_into"] = keep["headline"]
-        order = sorted([c for c in live if not c.get("merged_into")],
-                       key=lambda c: -c["importance"]["importance_score"])
-        rec.setdefault("evaluation_order", []).extend(c["headline"] for c in order)
-        ck("importance")
-
-        # 5. CROSS-SOURCE COVERAGE (all candidates first)
-        for oi, c in enumerate(order):
-            q = c["query"]
-            qv = E.encode(sm.query_texts(q), query=True)
-            sims = (vecs @ qv.T).max(axis=1) if len(chunks) else np.zeros(0)
-            pats = sm.alias_patterns(q)
-            members = set(c.get("cluster_member_chunk_ids") or ())   # DEC-13 a: a cluster's evidence = its statements
-            per_vid = {}
-            for i, ch in enumerate(chunks):
-                if members and ch["chunk_id"] not in members:
-                    continue
-                hits = sum(1 for p in pats if p.search(ch["text"]))
-                if members or sims[i] >= RETRIEVAL_MIN_SIM or hits >= 2:
-                    per_vid.setdefault(ch["video_id"], []).append((float(sims[i]) + 0.03 * min(hits, 3), i))
-            ranked_v = sorted(per_vid.items(), key=lambda kv: -max(s for s, _ in kv[1]))
-            picked, seen_ch = [], set()
-            for vid, lst in ranked_v:                       # channel diversity first
-                ch0 = chunks[lst[0][1]]["channel_id"]
-                if ch0 not in seen_ch:
-                    picked.append((vid, lst))
-                    seen_ch.add(ch0)
-            for vid, lst in ranked_v:
-                if len(picked) >= MAX_ADJUDICATE_PER_STORY:
-                    break
-                if (vid, lst) not in picked:
-                    picked.append((vid, lst))
-            picked = picked[:MAX_ADJUDICATE_PER_STORY]
-            verdicts = []
-            c["coverage"] = {"videos_evaluated": 0, "verdicts": verdicts, "status": "in_progress"}
-            for vi, (vid, lst) in enumerate(picked):
-                idx = [i for _, i in sorted(lst, reverse=True)[:4]]
-                ex = [chunks[i] for i in sorted(idx, key=lambda i: chunks[i]["start"])]
-                u = next(x for x in uni if x["video_id"] == vid)
-                v = sm.adjudicate(L, q, {"title": u["title"], "channel": u["channel"],
-                                         "published_at": u["published_at"]}, ex, today=today)
-                v.update(video_id=vid, canonical_url=u["canonical_url"], channel=u["channel"],
-                         channel_id=u["channel_id"], title=u["title"], published_at=u["published_at"],
-                         layout_eligible=u["layout_eligible"], transcript_sha256=u["transcript_sha256"],
-                         transcript_method=u["transcript_method"],
-                         excerpts=[{"chunk_id": x["chunk_id"], "start": x["start"], "end": x["end"],
-                                    "text": x["text"]} for x in ex],
-                         retrieval_score=round(max(s for s, _ in lst), 3))
-                verdicts.append(v)
-                c["coverage"]["videos_evaluated"] = len(verdicts)
-                ck("adjudicate", candidate=oi, of=len(order), video=vi, of_videos=len(picked))
-            _decide_coverage(c, verdicts, by_cid, log)
-            ck("coverage", candidate=oi, of=len(order))
-
-        # 5b. SAME-EVENT MERGE (mission 4b): candidates resting on the same counted passage are one event
-        for group in _same_event_groups(order):
-            merged = _merge_event([order[i] for i in group], L, uni, by_cid, today, log)
-            cands.append(merged)
-            order.append(merged)
-            ck("merge", members=len(group), decision=merged["decision"])
-
-        # 5c. DEC-9: an event already delivered to the approval chat is never selected again (same identity)
-        import story_ledger
-        ledger = story_ledger.entries()
-        excluded = []
-        for c in order:
-            hit = story_ledger.delivered_match(c, ledger) if c.get("decision") == "coverage_qualified" else None
-            if hit:
-                c["decision"] = f"already delivered (story ledger: {hit['run']}, '{hit['headline'][:60]}')"
-                excluded.append({"headline": c["headline"], "ledger_run": hit["run"]})
-        rec.setdefault("story_ledger", {"entries": len(ledger), "excluded": []})["excluded"] += excluded
-
-        # 6. E5: one GPU0 swap -> word-level transcripts for every coverage-qualified candidate
-        qualified = [c for c in order if c.get("decision") == "coverage_qualified"]
-        need = {}
-        for c in qualified:
-            for v in c["coverage"]["verdicts"]:
-                if v["counted_as_same_event"] and v["layout_eligible"]:
-                    need[v["video_id"]] = v["channel_id"]
-        words, arb = {}, {"videos": sorted(need)}
-        rec.setdefault("gpu_arbitration", {})[pname] = arb
-        todo = [] if words_fn else [vid for vid in need if not ts.sentence_ready(ts.canonical_transcript(vid))]
-        for vid in need:
-            if words_fn:
-                words[vid] = words_fn(vid)                  # backtest: existing word records only
-            elif vid not in todo:
-                words[vid] = (ts.canonical_transcript(vid), "cached")
+    # DEC-13 a + constrained selection (addendum '22:15' item 3; pp-selectid): pools channel_clusters_48h ->
+    # channel_clusters_72h -> wire_headlines, a pool only when every earlier one produced nothing. Inside a pool the
+    # model chooses SENTENCE IDS (pipeline/select_by_id.py): the claim and every segment are source sentences
+    # verbatim, nothing the model writes is matched back to a transcript (E-FAIL-036 / 037 / 038); one predicate
+    # (pipeline/eligibility.py) judges every story and line-up (Bitcoin screen, freshness, partner channel, layout,
+    # stand-alone, whole sentences, the hook's lead, the story ledger, law L-o's 60-70 s runtime); today's model
+    # judgements stay as independent checks on the verbatim text (select_by_id.ModelChecks: verify_support on EVERY
+    # story sentence against the claim, so two-channel coverage rests on an independent verdict per sentence;
+    # verify_reaction on every non-statement sentence of a range). One word pass per pool (law L-r: GPU0 swaps are
+    # counted, never one per story); SB_MAX_STORY_CALLS story calls per run, widest clusters first (decision D-f).
+    import eligibility as EL
+    import select_by_id as SB
+    import story_ledger
+    ctx = EL.Context(now, registry, ledger=tuple(story_ledger.entries()))
+    sources = SB.sources_from_universe(uni)
+    by_vid = {u["video_id"]: u for u in uni}
+    chunks_by_video = {}
+    for c in chunks:
+        chunks_by_video.setdefault(c["video_id"], []).append(c)
+    wire = [c for c in cands if c["origin"] == "story_engine"][:MAX_CANDIDATES]
+    arb = rec.setdefault("gpu_arbitration", {})
+
+    def word_source(vid, r):
+        u = by_vid[vid]
+        timing, toks = SB.tokens_from_record(r)
+        return EL.Source(vid, u["channel_id"], u["channel"], u["published_at"], r.get("transcript_sha256"),
+                         r.get("transcript_method"), toks, timing=timing, title=u.get("title") or "",
+                         file_head=True, vod=True)        # a full-video store record of a universe upload
+
+    def story_words(vids):
+        """E5 / law L-e: sentence-ready word records for the on-screen videos of a pool's accepted stories (one GPU0
+        swap per pool); the backtest passes its frozen word records instead (words_fn): only a full-video STORE record
+        counts there (status 'store ...'); a run's window transcript has window-offset times (E-FAIL-PS1) and is
+        refused here whether or not R4 is applied (audit C2)."""
+        got = {}
+        if words_fn:
+            for vid in vids:
+                r, why = words_fn(vid)
+                full = bool(r) and str(why).startswith("store ") and ts.sentence_ready(r)
+                got[vid] = word_source(vid, r) if full else None
+            arb.setdefault("results", {}).update(
+                {v: "sentence-ready (backtest store record)" if got[v] else "backtest: no full-video store word record"
+                 for v in vids})
+            return got
+        todo = [v for v in vids if not ts.sentence_ready(ts.canonical_transcript(v))]
+        acquired = {}
         if todo:
             try:
-                arb["release"] = sm.release_gpu0_for_whisper(L, log=log)
+                arb.setdefault("release", []).append(sm.release_gpu0_for_whisper(L, log=log))
             except RuntimeError as e:
-                arb["release_error"] = str(e)
-                for vid in todo:
-                    words[vid] = (None, f"infra: {e}")
+                arb.setdefault("release_error", []).append(str(e))
             else:
                 for vid in todo:
-                    r, st = ts.acquire(vid, channel=by_cid[need[vid]], allow_whisper=True, prefer_words=True)
-                    err = ts.LAST_ERROR.get(vid, "")
-                    if r is None or not ts.sentence_ready(r):
-                        words[vid] = (None, f"infra: {err}" if _infra_error(err) else f"failed: {st} {err}")
-                    else:
-                        words[vid] = (r, st)
+                    acquired[vid], _ = ts.acquire(vid, channel=by_cid[by_vid[vid]["channel_id"]], allow_whisper=True,
+                                                  prefer_words=True)
                     ck("word_transcripts", video=vid)
                 ts.release_whisper()
-                arb["after_whisper"] = sm.gpu0_memory()
-        arb["results"] = {vid: st for vid, (r, st) in words.items()}
-        ck("word_transcripts_done")
-
-        # 7. CLIP QUALITY
-        for oi, c in enumerate(qualified):
-            cq = _clip_quality(c, [v for v in c["coverage"]["verdicts"] if v["counted_as_same_event"]],
-                               E, L, by_cid, words, log, today=today)
-            c["clip_quality"] = cq
-            c["decision"] = "producible" if cq["producible"] else (
-                ("INFRA_HOLD: " if cq.get("infra") else "rejected: ") + cq["reason"])
-            ck("clip_quality", candidate=oi, of=len(qualified))
-
-        return order
-
-    # DEC-13 a: candidates come from the channels' own conversation first; wire / story-engine headlines are
-    # evaluated only after every channel cluster is exhausted (none producible)
-    pools = [(f"channel_clusters_{t}", lambda t=t: label_clusters(t)) for t in TIERS] + [
-        ("wire_headlines", lambda: [c for c in cands if c["origin"] == "story_engine"][:MAX_CANDIDATES])]
-    rec["pools"], order = [], []
-    for pname, make in pools:
-        done = next((p["pool"] for p in rec["pools"] if p.get("producible")), None)
-        if done:
-            why = f"not evaluated: the {done} pool produced a story (DEC-13 a)"
-            for e in emergent:
-                if pname.endswith(e["screen"]):
-                    e["gate"] = why
-            for c in (cands if pname == "wire_headlines" else []):
-                if c["origin"] == "story_engine":
-                    c["decision"] = why
-            rec["pools"].append({"pool": pname, "evaluated": False})
-            continue
-        pool = make()
-        got = evaluate(pname, pool)
-        order += got
-        rec["pools"].append({"pool": pname, "candidates": len(pool), "evaluated": True,
-                             "producible": any(c.get("decision") == "producible" for c in got)})
-    _close_cluster_ledger(emergent, cands)
-    rec["llm"].update(calls=getattr(L, "calls", None), cache_hits=getattr(L, "cache_hits", None),
-                      digest=getattr(L, "digest", None))
-    producible = [c for c in order if c.get("decision") == "producible"]
-    infra = [c for c in order if str(c.get("decision", "")).startswith("INFRA_HOLD")]
-    L.stop()
-    if embedder is None:
-        E.close()
+                arb.setdefault("after_whisper", []).append(sm.gpu0_memory())
+        for vid in vids:
+            r = acquired.get(vid) if vid in acquired else ts.canonical_transcript(vid)
+            got[vid] = word_source(vid, r) if ts.sentence_ready(r) else None
+        arb.setdefault("results", {}).update(
+            {v: "sentence-ready" if got[v] else (ts.LAST_ERROR.get(v) or "not sentence-ready") for v in vids})
+        return got
+
+    pools = [(f"channel_clusters_{t}", lambda t=t: SB.cluster_groups(emergent, sources, t)) for t in TIERS] + [
+        ("wire_headlines", lambda: SB.wire_groups(wire, chunks, vecs, lambda tx, q: E.encode(tx, query=q), sources))]
+    model = SB.OllamaModel(L)
+    if getattr(L, "digest", None):                 # DEC-13 e: VALIDATED replies kept by (model + digest + ctx, prompt, seed)
+        model = SB.Recorder(model, os.path.join(sm.LLM_CACHE_DIR, "select_by_id"), validated_only=True)
+    try:
+        res = SB.run_pools(model, ctx, pools, story_words, log=log, checks=SB.ModelChecks(L),
+                           max_story_calls=SB_MAX_STORY_CALLS)
+    finally:
+        rec["llm"].update(calls=getattr(L, "calls", None), digest=getattr(L, "digest", None))
+        L.stop()
+        if embedder is None:
+            E.close()
+    rec["pools"], rec["select_by_id"] = res["pools"], res["groups"]
+
+    def gate(g):                                   # the gate a group's own record names (DEC-13 d)
+        st, lo = g.get("story") or {}, g.get("lineup") or {}
+        if lo.get("status") == "accepted":
+            return "producible"
+        if lo:
+            return f"line-up {lo.get('status')}: {lo.get('why') or ''}".strip()
+        if st.get("status") == "accepted":
+            return "story accepted; line-up not asked: another group of the pool was selected first (DEC-13 a)"
+        return f"story {st.get('status')}: {st.get('why') or ''}".strip()
+    visited = {}
+    for g in res["groups"]:                        # DEC-13 d: every screened cluster names the gate that stopped it
+        if g["group"].startswith("cluster "):
+            visited[int(g["group"].split()[1])] = (gate(g), ((g.get("story") or {}).get("claim") or {}).get("text"))
+    done = (res["selected"] or {}).get("pool")
+    for i, e in enumerate(emergent):
+        if e.get("screen") not in TIERS:
+            continue                                   # stopped by the free screen (its gate is already written)
+        if i in visited:
+            e["gate"], e["claim"] = visited[i]
+        else:
+            e["gate"] = (f"not evaluated: the {done} pool produced a story (DEC-13 a)" if done else
+                         "not evaluated: the pool's story-call budget or an earlier stop")
+    wire_out = {int(g["group"].split()[1]): g for g in res["groups"] if g["group"].startswith("wire ")}
+    for j, c in enumerate(wire):                   # DEC-13 d for the wire pool too: every candidate names its gate
+        g = wire_out.get(j)
+        if g is not None:
+            c["decision"] = gate(g)
+        elif any(p.get("pool") == "wire_headlines" and p.get("evaluated") for p in res["pools"]):
+            c["decision"] = "not evaluated: the pool's story-call budget or no retrieval hit"
+        else:
+            c["decision"] = f"not evaluated: the {done} pool produced a story (DEC-13 a)" if done else "not evaluated"
     rec["seconds"] = round(time.time() - t0)
-    if not producible:
-        rec["decision"] = ("HOLD (infrastructure): no producible candidate and "
-                           f"{len(infra)} candidate(s) blocked by GPU/transcription infrastructure"
-                           if infra else "HOLD: no candidate is producible (see candidates[].decision)")
+    if res["selected"] is None:
+        infra = arb.get("release_error") or [v for v, st in (arb.get("results") or {}).items() if _infra_error(st)]
+        asked = [g for g in res["groups"] if (g.get("story") or {}).get("attempts")]
+        down = [g["group"] for g in asked if "model_error" in ((g.get("lineup") or {}).get("status"),
+                                                               (g.get("story") or {}).get("status"))]
+        if not infra and asked and len(down) == len(asked):    # every model call failed: an outage, not a selection
+            infra = [f"every evaluated group ended in a model error ({len(down)})"]
+        rec["decision"] = ("HOLD (infrastructure): no producible candidate and GPU0 release / word pass / model "
+                           f"failures {infra}" if infra else "HOLD: no candidate is producible (see select_by_id[])")
         ck("done")
         raise NoProducibleStory(rec["decision"])
-    win = max(producible, key=lambda c: (c["importance"]["importance_score"],
-                                         c["coverage"]["independent_channels"],
-                                         c["clip_quality"]["mean_chosen_score"]))
-    rec["selected"] = {"headline": win["headline"], "origin": win["origin"],
-                       "short_label": win["query"].get("short_label"),
-                       "underlying_event": win["query"].get("underlying_event"),
-                       "currentness": win["currentness"],
-                       "event_date_grounding": win.get("event_date_grounding"),
-                       "flags": win.get("flags", []),
-                       "importance": win["importance"],
-                       "coverage": {k: v for k, v in win["coverage"].items() if k != "verdicts"},
-                       "clip_quality": {k: v for k, v in win["clip_quality"].items() if k != "candidates"},
-                       "why": ("highest story importance among producible candidates; ties broken by "
-                               "coverage then clip quality"),
-                       "evidence": [{"video_id": v["video_id"], "chunk_ids": v.get("supporting_chunk_ids") or [],
-                                     "quote": v.get("evidence_quote"),
-                                     "quote_tokens": sm._norm(v.get("evidence_quote")).split()}
-                                    for v in win["coverage"]["verdicts"] if v.get("counted_as_same_event")],
-                       "other_producible": [c["headline"] for c in producible if c is not win],
-                       "infra_held": [c["headline"] for c in infra]}
+    st, lo = res["selected"]["story"], res["selected"]["lineup"]
+    meta = {vid: {"channel": by_cid[u["channel_id"]]["display_name"], "handle": by_cid[u["channel_id"]].get("yt_handle", ""),
+                  "tier": by_cid[u["channel_id"]].get("tier", 9)} for vid, u in by_vid.items() if u["channel_id"] in by_cid}
+    passages = SB.to_passages(st, lo, meta)
+    rec["selected"] = {"headline": st.claim.text, "selected_by": "select_by_id", "pool": res["selected"]["pool"],
+                       "group": res["selected"]["group"],
+                       "origin": "transcript_cluster" if res["selected"]["pool"].startswith("channel") else "story_engine",
+                       "claim": {"video_id": st.claim.source.video_id, "text": st.claim.text},
+                       "story_tier": st.eligibility.facts.get("tier"),
+                       "evidence": SB.evidence_record(st.story, chunks_by_video),
+                       "eligibility": lo.eligibility.to_dict()}
     rec["decision"] = "SELECTED"
-    chosen = win["clip_quality"]["chosen"]
-    _write(run_dir, "passages.json", {"story": win["query"], "passages": win["clip_quality"]["candidates"],
-                                      "chosen": chosen,
-                                      "channels": sorted({p["channel"] for p in chosen})})
+    _write(run_dir, "passages.json", passages)
     srcs, seen = [], set()
-    for p in chosen:
+    for p in passages["chosen"]:
         if p["video_id"] in seen:
             continue
         seen.add(p["video_id"])
@@ -973,7 +849,7 @@
                      "transcript_sha256": p["transcript_sha256"]})
     _write(run_dir, "sources.json", srcs)
     ck("done")
-    return win["query"].get("short_label") or win["headline"], rec
+    return st.claim.text, rec
 
 
 def cluster_entry(chunks, vecs, g):
--- a/pipeline/select_passages.py
+++ b/pipeline/select_passages.py
@@ -357,8 +357,8 @@
     if hook_seg is None:
         print("  Cannot build hook segment (sentence law) — STOP")
         return False
-    if len(clip_segs) < 1:
-        print("  No valid clip segments (sentence law) — STOP")
+    if len(clip_segs) < 2:     # SELECT = hook + >= 2 clips (eligibility N_CLIPS; edl_rules R5; GPT-select F08)
+        print(f"  {len(clip_segs)} valid clip segment(s) < 2 (sentence law) — STOP")
         return False
 
     # Generate VO script (M20 rules)
```
<!-- PATCH END -->

## R2 ONE HOME FOR THE LAW CONSTANTS (follow-up, not needed for R1)

`pipeline/eligibility.py` defines every selection law constant once, citing where it lives today;
`tests/eligibility/test_eligibility.py` TestPinned fails if `editorial_select` / `stand_alone` / `sentence_law` change
one without it. To make eligibility the only home: in `pipeline/editorial_select.py` replace the definitions of
UNIVERSE_HOURS, MIN_COVERAGE_CHANNELS, MIN_LAYOUT_CHANNELS, HOOK_MIN_S / HOOK_MAX_S, CLIP_MIN_S / CLIP_MAX_S,
MAX_WINDOW_SENTENCES, MAX_VERIFIED_QUOTES_PER_VIDEO, CLUSTER_HOURS, BITCOIN_TERMS, V2F_VIDEO_IDS, ADJ_MAX_START_S,
ADJ_MAX_PER_DIRECTION, INTERJECTIONS, BACKREF_WORDS, BACKREF_PHRASES, _NOT_ENTITY, SAME_STATEMENT_RUN with imports
from eligibility (eligibility imports canon, sentence_law, stand_alone, transcript_store, story_semantics, never
editorial_select: no cycle), and `layout_eligible(channel)` with `eligibility.layout_ok(channel)`.

## R3 DECISIONS (evidence in docs/audits/SELECT_BY_ID_DESIGN.md sections 4-5 and the proof)

- D-a RESOLVED (audit M1 / C2). Independent model checks run on the chosen verbatim text:
  - `verify_support` on every story sentence against the claim;
  - `verify_reaction` on every non-statement sentence of a range.
  `rate_passages` floors are not run: law L-o makes score floors targets that rank. Cost: one local call per story
  sentence and per added sentence.
- D-b The caption headline is now the claim sentence verbatim; `telegram.headline_numbers_said` still requires its
  numbers in the final. A claim from an evidence-only channel (has_chyron) may not be on screen: require the claim to
  lie inside the line-up, or keep the check as the gate (fail closed: the drop stops)?
- D-c CONSTITUTION section 9's 48 h Freshness Law (video_pipeline_v3) vs DEC-13's 72 h max for Pulse Check: eligibility
  follows DEC-13 (72 h) and reports the 48 h / 72 h tier.
- D-d NOTE-PS5 (whole-record L-e refuses a record for one far stretch) and NOTE-PS6 (D4 a vs the approved Natalie
  clip): pp-selectid_BIBLE_ADDITIONS.md.
- D-e The wire pool now retrieves by the headline's own embedding (no derived query, no alias hits): recall of wire
  items changes; DEC-13 runs it only after every cluster tier.
- D-f Order inside a pool: the widest cluster first (most channels), ties in clustering order; the first accepted
  line-up wins. Today ranked producible candidates by story importance, which read model-written scores of
  model-written text. Change it here if PBX wants another order.
- D-g Story-call budget: `SB_MAX_STORY_CALLS` = 12 per run. Each call is up to 3 attempts plus one verify_support per
  story sentence. This is a budget to set from measured gemma3:27b latency against law L-p's cycle time (the proof
  used 8).

## R4 BACKTEST: a run's window transcript is not full-video word timing (E-FAIL-PS1)

Since audit C2, R1 no longer depends on R4 for correctness: its backtest path refuses any record whose status is not
'store ...'. R4 is still asked so that the backtest does not report a run transcript as a word record.

`pipeline/backtest.py` `offline_words`: drop the `_run_transcript` fallback (or add that run's EDL
`source_window_offset_s` to every word time and refuse a transcript whose EDL offset is unknown). The exact change
(`git apply --check` clean on c1451047). It changes what `pipeline/test_backtest.py`
`test_store_then_run_transcript_then_the_gate` asserts: its first block (a run transcript returned as a word record)
must become "a run transcript is never returned" (r is None, st contains "no full-video word record"); its store
block is unchanged. `_run_transcript` is then unused.

```diff
--- a/pipeline/backtest.py
+++ b/pipeline/backtest.py
@@ -86,16 +86,14 @@
 
 
 def offline_words(runs_dir=RUNS_DIR):
-    """words_fn: a sentence-ready store word record, else a run's large-v3 transcript, else none (a live run
-    would transcribe: recorded as the gate)."""
+    """words_fn: a sentence-ready store word record (full-video timestamps), else none (a live run would transcribe:
+    recorded as the gate). A run's transcripts/<video>.json is select_passages' transcript of a DOWNLOADED WINDOW
+    (offset = that run's EDL source_window_offset_s, e.g. 23.38 s), never full-video timing (pp-selectid E-FAIL-PS1)."""
     def fn(video_id):
         r = ts.canonical_transcript(video_id)
         if ts.sentence_ready(r):
             return r, f"store {r['transcript_method']}"
-        r = _run_transcript(video_id, runs_dir)
-        if r:
-            return r, f"run transcript {r['source_path']}"
-        return None, "backtest: no word record (a live run would transcribe it)"
+        return None, "backtest: no full-video word record (a live run would transcribe it)"
     return fn
 
 
```

## R6 BEFORE R1 IS ENABLED (audit C2; laws L-o, L-r, L-u, L-s)

1. gemma3:27b shadow run (opus B P0; this session uses no GPU).
   - Run R1's `run_pools` over the saved universes and the preview with production max_tokens and seeds.
   - Report per attempt: parse validity, rejection reasons, the ModelChecks verdict distribution, and the latency
     per story call. The latency sets D-g.
   - If fenced or prose replies dominate, fix it in the adapter (JSON mode is already on). Never add repair.
2. L-o downstream: three sites still apply the windows as hard filters, so a line-up chosen under L-o can HOLD at
   validate:
   - `edl_rules.py` R5 (8-25 s, :229-232);
   - `stand_alone.check_edl` (hook / clip opener at validate, run_fresh.py:342-370);
   - `select_passages.py:333` (duration).
   L-o's WIRING clause names exactly these. Align them, with must-fail tests proving every INTEGRITY rule still
   rejects.
3. Runtime: measure 60-70 s on the FINAL (gates), not only the pre-render estimate. Refit `eligibility.TAIL_S` once
   three-segment finals exist; today it is one calibration from a four-segment final.
4. L-r: the line-up call reloads gemma on GPU0 after the word pass. Route that reload through gpu0's `swap_to`.
   `LocalLLM.placement_checked` stays True after a reload today.
5. L-u (orchestrator 02:30): one clip per channel per video and <= 20 s per source video, for every package type.
   Phase 2 (pp-selectid) applies it in the packager to every type. When the law is written, eligibility gains the L-u
   constants (MAX_CLIPS_PER_CHANNEL 1, a per-source-video seconds cap) and TestPinned pins them.
6. L-s (orchestrator 02:30): the context-integrity gate (built in phase 2) also covers the story-first type.
7. L-x (orchestrator 02:45: no single model, Ultron first). R1 builds `select_by_id.OllamaModel(L)` and
   `ModelChecks(L)` directly. Under L-x, both take their back-end chain for the roles "story selection" and "check
   verdict" from phase 2's provider config:
   - local gemma first, then the configured fallbacks;
   - the check verdict always on a different model than the selection;
   - no model name in the code.
   The `select_by_id.Model` interface is the seam, and no change to select_by_id's contract is needed.

## R7 MOMENTS-FIRST WIRING (phase 2; laws L-q, L-s..L-x): the package rendered by the SAME factory

The route is the existing PINNED entry point. A moments-first package becomes the pinned decision, and every
downstream stage stays shared and unchanged: validate (edl_rules, editorial gate, stand-alone, layout), cut, sentence
law, voice, prepare, layout, render 16:9 and 9:16, gates, verify, release authorisation.

1. **`pipeline/pinned.py` (exact patch below, `git apply --check` clean on c1451047; tests/package/smoke_r7.py: SMOKE
   R7 PASS on a temporary patched copy).**
   - `build_edl` takes the VO from the pin's `moments_package` (written by pipeline/package_pin.py): the package's
     intro, and one bridge after each clip but the last (`after_clip`, the renderer's placement, render_vertical.py
     :821-872). There is none between the hook and the first clip.
   - The EDL also carries the ONE title and caption (law L-t) and the package's sha256 and gate verdicts.
   - It refuses (PinError) a bridge the renderer cannot place, or a package whose VO-fidelity and context-integrity
     gates did not BOTH pass.
   - A pin without a package is unchanged: no body VO, Editorial Law 2's default.
2. **TONIGHT** (orchestrator: "the integrator renders it"): apply item 1, then run run_fresh.py with
   `--pinned` and the MOMENTS_PIN.json named at the top of pp-selectid_STATE.md.
   - The pin's segments carry `approved_text` = the moments' exact words, and `machine_cuts: true`, so the sentence law
     locates them BY TEXT in the acquired transcript, as for a machine PIN today.
   - Its `approved_by` names the machine and REVIEW ONLY. No human approved it (law L-q: the first moments-first
     delivery is REVIEW ONLY, with its duration deviations listed per L-o).
   - stage_review (local gemma) still writes its own independent review of the VO jobs. The editorial gate's Law 2
     then needs each body-VO line affirmed: intro = "context", each bridge = "connection".
3. **Moments mode in `pipeline/run_fresh.py` (the integrator's code; every step is a function here).**
   - A stage "moments":
     - `moments.mine(providers.Router(local_llm=<the LocalLLM started under the gpu0 lease>), <the cycle's word
       Sources>, ctx, trend_brief.TOPICS, since=<the last cycle's start>)`;
     - `package.build(router, mined["moments"], sources, ctx, delivered=<moment ids delivered in 24 h>,
       optout=moments.optout_ids())`;
     - `package_pin.write_pin(pk, run_name, run.dir)`.
   - Then `stage_pinned(run, pin_path)`. "No package" is a HOLD naming `why_none` / `tried`.
   - The cycle's word Sources are pipeline_pp_ingest's: the moment ledger plus the store's sentence-ready records,
     law L-e.
4. **Gates for moments-first runs ONLY** (law L-q CHECK, '01:58').
   - The same-event / topic gates are replaced by the package's recorded verdicts: VO fidelity (deterministic and the
     blind verdict) and context integrity (L-s). The release authorisation must require both, from
     `edl["moments_checks"]`.
   - stand_alone's topic check stays: its subject for a Bitcoin package is Bitcoin, and every segment names it by rule.
   - Every other integrity gate is unchanged.
   - L-t: the title and caption are bound into the release authorisation (release_auth's attested set, with both
     finals). Any change after the gates re-runs them.
5. **The windows still applied downstream** (R6 item 2: edl_rules R5 8-25 s, select_passages:333, stand_alone at
   validate) must follow law L-o.
   - The packager keeps every segment at <= 20 s (L-u). A hook under 8 s HOLDs at R5 until R6 item 2 lands.
6. **L-x.** Every role resolves through pipeline/model_providers.json, so no model name lives in code.
   - The integrator runs the local legs of tests/providers/ab_roles.py under the GPU0 lease (`--local`), and re-orders
     a role's chain only on that measurement.
   - The Heimdall 90 % tripwire notifies, never halts (providers.Router.heimdall_tripwire).

<!-- PATCH R7 BEGIN -->
```diff
--- a/pipeline/pinned.py
+++ b/pipeline/pinned.py
@@ -311,20 +311,45 @@
     for i, c in enumerate(clips, 1):
         c["index"] = i
     channels = sorted({x["channel"] for x in segs})
+    mp = pin.get("moments_package")            # pp-selectid R7: a moments-first package (law L-q) as the decision
+    vo = _generate_vo_script(pin["label"], hook["text"], clips, channels)
+    if isinstance(mp, dict):
+        vo = moments_vo(mp, clips)
     edl = {
         "topic": pin["label"],
         "angle": f"Pinned: {pin.get('headline') or pin['label']}",
         "hook": hook,
         "clips": clips,
-        "vo": _generate_vo_script(pin["label"], hook["text"], clips, channels),
+        "vo": vo,
         "total_clip_duration": round(hook["duration"] + sum(c["duration"] for c in clips), 2),
         "mode": "pinned",
         "pinned_story_id": pin["story_id"],
     }
+    if isinstance(mp, dict):                   # law L-t: the ONE title and caption travel with the EDL to release
+        edl.update(title=mp["title"], caption=mp["caption"], moments_package_sha256=mp["package_sha256"],
+                   moments_checks=mp.get("checks"))
     overrides = build_vertical_overrides(hook, clips, registry)
     return edl, overrides, report
 
 
+def moments_vo(mp, clips):
+    """The package's VO, checked by its VO-fidelity and context-integrity gates (pipeline/package.py): the intro and
+    one bridge after each clip but the last, in the EDL's shape ({"text", "after_clip"}). Fail closed on any shape
+    the renderer cannot place (a bridge after the hook, after the last clip, or after a missing clip)."""
+    v = mp.get("edl_vo") or {}
+    intro = v.get("intro")
+    bridges = v.get("bridges") or []
+    idx = {c["index"] for c in clips}
+    for b in bridges:
+        if not isinstance(b, dict) or not str(b.get("text") or "").strip() or b.get("after_clip") not in idx or                 b["after_clip"] == max(idx):
+            raise PinError(f"moments_package bridge {b!r}: needs text and after_clip in 1..{max(idx) - 1}")
+    if intro is not None and not str(intro).strip():
+        raise PinError("moments_package intro is empty")
+    if not mp.get("checks", {}).get("vo_fidelity_ok") or not mp.get("checks", {}).get("context_integrity_ok"):
+        raise PinError("moments_package: the VO-fidelity and context-integrity gates did not both pass")
+    return {"intro": intro, "bridges": [{"text": b["text"], "after_clip": b["after_clip"]} for b in bridges]}
+
+
 def prepare(pin_path, run_dir, log=print):
     """Validate + acquire + build. Writes edl.json, vertical_overrides.json, PINNED_DECISION.json.
     Returns the PINNED_DECISION record. Raises PinError."""
```
<!-- PATCH R7 END -->

## R8 FOR pipeline_pp_tests (the exam): cases this session found (orchestrator 03:40: "send the case to pipeline_pp_tests")

1. **title_misleads_about_now** (vo_fidelity corpus, a new fail class; laws L-v 3 / L-t). REAL case, fresh_20261112_050611:
   - The candidate title, caption and VO intro were "Bitcoin ran from 16K to 126K" (Simply Bitcoin, Noq6txZU91c
     399.15-405.25, verbatim).
   - The universe's own current level that night was about $73,000: Bitcoin falling and testing its 200-day average.
   - Every word is in a clip, and the line is still misleading as a headline.
   - Must FAIL: a headline line (title / caption / intro) stating a price level or move that is neither marked as
     history ("from the 2022 low ...") nor within tolerance of a level the universe states as current.
   - Must PASS: the same numbers marked as history; today's level stated as today's.
   - This session's gate: vo_fidelity PRICE_NOW with package.current_levels.
2. **clip_repeats_the_line_before_it** (a package-structure fail class). Same night: the intro and the title repeated
   clip_03's words, which then played as a 6.1 s clip that added nothing.
   - Must FAIL: a VO line right before a clip, or the title, carrying a run of >= 5 canonical tokens of that clip.
   - This session's gate: package.duplicates.
3. **cleft_it / generic_we** (context_integrity must-PASS near misses, NOTE-PS12): "It's not Bitcoin that's getting
   hacked. It's other intermediaries." (What Bitcoin Did) and "we are going to have a new internet" (Natalie Brunell).
   A referent rule that rejects these is a false reject.

## R9 FOR pipeline_pp_tests: MUST-PASS context-integrity cases ruled by the orchestrator (06:00 ruling 3, 06:22 rulings 5-6)

All four come from tonight's universe (fresh_20261112_050611); the orchestrator ruled each a FALSE REJECT of an earlier
encoding of the gate.

1. **ellipsis_completed_inside** (context_integrity, must PASS; ruling 3, REFERENT_OUTSIDE). What Bitcoin Did,
   c1JGheQBPH4 2480.28-2491.52: "It's not Bitcoin that's getting hacked. It's other intermediaries. So in some ways, it
   kind of shines a light on the secure nature and the unique nature of Bitcoin."
   - The orchestrator's text: "that is ellipsis completed by the sentence immediately before it INSIDE the clip
     ('It's not Bitcoin that's getting hacked. It's other intermediaries [that are getting hacked].'). Same family as
     the cleft-'it' false reject. Rule: a referent is OUTSIDE only if no antecedent or completing predicate exists in
     the selected sentences AND resolving it differently would change what the speaker asserts. A presupposed general
     topic (that hacks have happened) is not an outside referent."
2. **own_hedge_heard_verbatim** (must PASS; ruling 3, STRONGER). The same clip: "the speaker's own hedge ('in some
   ways, it kind of shines a light') is verbatim in the clip the viewer hears. A STRONGER failure must cite the exact
   VO/title words that raise the certainty, or an attribution verb stronger than the clip's hedge. A bare
   A-says-likely / B-says-certain disagreement between two models with no cited words is recorded as a NOTE, not a
   failure."
3. **scope_of_presupposed_occasion** (must PASS; ruling 5, NOT_ENTAILED). The same clip.
   - "The viewer hears the speaker's exact words, including the present progressive 'that's getting hacked' and the
     speaker's OWN generalisation ... RULE: entailment is judged between the speaker's in-context assertion and the
     CLIP'S OWN WORDS as heard, not between two model paraphrases."
   - "A difference of scope fails only when the context LIMITS the claim in a way the selected words drop (e.g. 'in
     this one case', 'for small holders only', 'back in 2021') and the limit changes what a reasonable viewer
     concludes. A presupposed topic or occasion is not such a limit."
4. **elaboration_consistent_with_inside_condition** (must PASS; ruling 6, RETRACTION). A guest on Natalie Brunell's
   channel, wdk5JZ9hPzs 529.05-539.34: "Bitcoin is a new system of measure that's measuring the first free market
   that's ever existed. And all it has to do, is stay decentralized and secure." Later in the window: "if people
   measure Bitcoin through the debt-based system it could become centralized and a different control system."
   - "RETRACTION means the speaker later withdraws, reverses, corrects or materially limits the selected assertion
     ('actually I misspoke', 'that said, I don't believe that', 'but that only holds if...'). Here the clip itself
     carries the condition ('all it has to do, is stay decentralized and secure'), and the later passage elaborates
     how that condition could be lost. A later elaboration or warning that is CONSISTENT with a condition stated
     inside the clip is not a retraction. It would be one if the selected words had dropped the condition."
   - The MUST-FAIL twin: the same later passage, with the selection cut to "Bitcoin is a new system of measure that's
     measuring the first free market that's ever existed." (the condition dropped).
- This session's gate after the rulings: the corpus's 41 context-integrity must-fail cases, 41/41 rejected
  (tests/package/exam/ci_mustfail_20261112T062725.json).
- One intermediate encoding let 2 title_adds_thesis cases pass. Worth a must-fail case each in the other direction:
  (a) a title "X: <a thesis X did not assert>" over a clip the viewer reads at the same certainty alone; (b) host
  commentary attributed to nobody, which must NOT be read as the speaker's assertion (must PASS).

## R5 BIBLE

Fold docs/audits/parallel/pp-selectid_BIBLE_ADDITIONS.md (E-FAIL-PS1..PS4, NOTE-PS5, NOTE-PS6) into
docs/QWEN_CONTEXT_BIBLE.md with your numbering.
