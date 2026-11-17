# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_2005
# Branch: pp-selectid
# Generated: 2026-11-16 20:08 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
The automated Protocol Pulse "Pulse Check" medley (pipeline/run_fresh.py) cuts hooks and clips from
partner YouTube videos, renders 16:9 and 9:16, and runs QA gates. PBX watched the 2026-11-10 cut and
found editorial errors every gate had passed: the opening word sounded clipped (D1), clips started or
ended mid-sentence (D2/D3), credit avatars were warped (D4), the vertical was letterboxed (D5) and
channel changes were abrupt (D6). This work makes the gates catch what a human caught, proves it on
yesterday's files (tests/fixtures/pulse_20261110, pipeline/test_pulse_20261110_mustfail.py), fixes the
causes, then requires three clean fresh videos in a row with no code edits between them.

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS
- SENTENCE LAW: a clip's first word is the first word of a sentence and its last word the last word of
  a sentence. Boundary = transcript punctuation at a place a listener hears as the break between the two
  words (DEC-10, 2026-11-11: no minimum pause; the 01:50 order's 80 ms is recalibrated to the approved v2f
  reference, whose edges measure 0-10 ms; pipeline/sentence_law.py states every constant with its
  measurement). An unpunctuated transcript stretch has NO boundary
  (fail closed). Punctuation is added at transcription time only from a second, prompted ASR decode of
  the same audio, onto aligned verbatim words; the words never change (pipeline/punctuation.py). No
  language model decides a boundary (the per-gap adjudicator called 19/19 gaps sentence ends; removed).
- SELECTION LOCK: the words a clip must contain are fixed at selection time (selection_lock in edl.json,
  sha256-sealed). No later stage may recompute expected first/last words from a moved cut.
- SNAP LIMIT: a cut may move only inside the heard gap between the chosen sentence and its neighbour
  (the previous word's offset .. the next word's onset, at speech - 6 dB); it may never add or drop a word.
  A short gap is cut at the envelope minimum between the two words, never rejected for its length (DEC-10 d);
  its fade sits inside the gap (L-b: 2 video frames = 83 ms when it fits, down to 10 ms).
- NEIGHBOUR (DEC-10 c-ii): NO audible part of the neighbouring word: every frame the cut keeps on the
  neighbour's side of that minimum stays below the valley threshold (local speech - 12 dB) after the fade.
  A window is rejected for its edges only if this, the 85 % edge-word rule or sentence-completeness fails.
- ONSET/TAIL: edge words keep >= 85 % of their duration in the render (a floor for timestamp noise, never
  permission to trim: L-b below). The START OF PLAYBACK keeps the D1
  rule unchanged: a source that starts speaking at its file head, and the hook, need >= 80 ms of genuine
  sub-speech audio before the first onset or a declared room-tone lead-in pad; codec zero/padding is not
  room tone. Inside the video there is no lead / tail minimum (DEC-10: v2f's approved edges: 0 ms).
- CREDITS: round avatars of the channels actually used; the avatar is the channel's real square avatar,
  never a video thumbnail, never a generated placeholder; G12 / G15 measure the brand-red rings the renderer
  draws and G15 checks each disc is the credited channel's registered avatar (DEC-11).
- L-a SIGN-OFF NAMES ALL (PBX, 2026-11-11): the sign-off voiceover names every channel on the credits card, and the spoken set, the card set and the clips used are identical.
  Check: run_fresh.stage_voice HOLDs before render unless the script names exactly credit_rings.credit_channels(edl) (hook first, then clips); G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off and requires spoken == credited (registry names + aliases); VO stems are keyed by hash(text, voice, model). Must-fail: the 2026-11-11 preview (DataDash missing). Must-pass: v2f.
- L-b EDGE WORDS WHOLE (PBX, 2026-11-11): a fade never overlaps an edge word: the first and last word of every clip are heard whole, at full level, with their natural decay.
  Check: sentence_law.edge_fades places each machine-cut fade (2 frames, shortened down to 10 ms) inside the gap next to the cut, measured from the cut point's level; G17c (sentence_law.gate_g17_edges) requires every frame of both edge words within 1 dB of the unfaded source. Must-fail: the preview's Natalie Brunell tail ('...participated in the Monday rally.'). Must-pass: the L-b re-cut of it; v2f's edges except its two recorded legacy edges.
- L-c DISSENT IS RIGHT UNTIL DISPROVED (PBX, 2026-11-11): a check that disagrees with the others on an edge word is treated as right until an acoustic comparison against the source proves otherwise.
  Check: run_fresh.stage_gates: a dissenting G3b reading (DEC-12f) or a G3c head / tail failure on an edge stands (HOLD / FAIL) unless G16's neighbour_clear passes and G17c, MEASURED ON THE FINAL FILE OF THAT FORMAT (sentence_law.edges_on_final: the bytes being approved, their constant gain removed, every frame of the edge word compared), passes for that edge; a proof from the prepared clip is never accepted (amended by the orchestrator addendum 2026-11-11 '22:00', GPT-cut F03). Test: test_release_auth / test_word_diff TestSpanMatches; sentence_law.edge_word_fidelity refuses an alignment that leaves a word frame uncompared (GPT-cut F07).
- L-d PROTECTED PREVIEW (PBX, 2026-11-11): the PBX-approved preview of 2026-11-11 is a protected reference.
  Check: pipeline/regression.sh step 6 (pipeline/check_preview_reference.py): its selection locks, cut points and 9:16 layout must reproduce with the current code; tag ref-pulse-preview-2026-11-11; references/pulse_preview_2026-11-11 (read-only, SHA256SUMS).
- L-e PUNCTUATED BEFORE READ (2026-11-11): Every word transcript the sentence law reads, the editorial word pass included, has its sentence punctuation restored from a prompted second decode of the same audio before any sentence is read.
  Check: transcript_store.acquire(prefer_words) returns only a sentence_ready record: the verbatim decode where no stretch reads unpunctuated, else a whisper_words_punct record (marks from a large-v3 batched reference decode with punctuation.PROMPT, onto aligned words only, plus a sentence-initial capital where both decodes end a sentence right before the word, so editorial start_is_boundary reads the reference's own evidence; word keys and timings unchanged; the verbatim record kept; one Whisper model on GPU0 at a time); editorial_select's word pass treats any other record as failed. Must-fail: Altcoin Daily Ov5jg52HqIY's verbatim record (its quote read as one 35.28 s sentence). Must-pass: its restored record (the quote's sentence 161.14-170.08, "Even thinking about the seasonality, ... the midterms.", a valid 8.94 s hook window). Test: pipeline/test_punct_word_pass.py.
- L-f CHANNELS FIRST (DEC-13, orchestrator 2026-11-11 18:00): Story candidates come from the channels' own conversation first: clusters of statements by at least two independent channels, screened for Bitcoin before any model call, with the claim written from their shared statements and their quotes attached; wire headlines are evaluated only after every cluster is exhausted.
  Check: editorial_select pools channel_clusters_48h -> channel_clusters_72h -> wire_headlines (a pool runs only when every earlier one produced nothing); cluster_entry (>= 2 channels with a Bitcoin statement, 48 h tier then 72 h max, else stopped with no model call; one statement per channel); a cluster's coverage adjudicates its own statements; every cluster's ledger entry names its channels, claim, statements, counted quotes and the gate that stopped it; a validated model reply is cached by sha256(model, its Ollama digest, context, max_tokens, prompt). MIN_COVERAGE_CHANNELS 2, hook >= 4.0, stand-alone, topic and sentence laws unchanged. Must-produce: today's $74K-pullback statements (4 channels) and ETF-outflow statements (2 channels) reach the model (under the old rule they were in no cluster). Must-not: Bloomberg's Fed-hike and Natalie Brunell's ETF-outflow statements never share a cluster. Test: pipeline/test_dec13_clusters.py.
- L-g WRITTEN FORMS (2026-11-11): A check that reads speech counts a word the ASR wrote as a symbol as the spoken word ('$40 trillion' = '40 trillion dollars', '50%' = '50 percent'), and reads the expected word the same way.
  Check: segment_v1/qa_gates._g3b_words: G3b's readings, the EDL's last word and its next word are read with the same rules (symbols spelled out in spoken order, abbreviated scales too ('$40M' = '40 million dollars'), a 'dollars' the ASR also wrote never doubled; thousands separators and trailing full stops dropped, other commas split words, decimals kept; a leak is any word of the next source word heard after the last word); vote rule and thresholds unchanged; G17c still compares every edge word with the source. Must-pass: the approved v2f's 9:16 clip_02 '... above 40 trillion dollars.' (read 'above $40 trillion' twice). Must-fail unchanged: Nov 10's Natalie tail against 'week.'; a cut 250 ms into 'rally'. Test: pipeline/test_g3b_majority.py.
- L-h TEXT READ AS SPOKEN (2026-11-12): Transcript text is read as the words it stands for before any chunk, quote check or model sees it: caption HTML entities are decoded ('S&amp;P' = 'S&P') and a Whisper word split into tokens is read whole ('$81 ,000' = '$81,000'); the stored record is never rewritten.
  Check: transcript_store.read_text builds every chunk's text; story_semantics._norm decodes entities and joins split tokens for quote checks; the embedding cache is versioned (t2) so vectors match the read text. Must-fail / must-pass: Altcoin Daily's 'S&P 500' quote and Natalie Brunell's '$81,000' quote against their real excerpts (pipeline/test_caption_entities.py).
- L-i THE CLAIM IS THE EVENT (DEC-13 a) (2026-11-12): A channel cluster's claim is the event its coverage is judged against: its query is derived from the claim alone and the model never re-reads it as another event.
  Check: story_semantics.derive_story_query: a transcript_cluster item is derived from the claim with CLUSTER_NOTE (no label summary) and its underlying_event is the claim verbatim (the model's reading kept as underlying_event_derived); wire items byte-identical. Test: test_caption_entities TestClusterClaimIsTheEvent; real model (DoD 20:13): Natalie Brunell and Coin Bureau then both count for the election sell-off / ETF-outflow claim.
- L-j RELEASE IS AUTHORISED ON THESE BYTES (red-team order 2026-11-11 '21:55', A): 'all release gates passed' means every REQUIRED gate ran, on samples, unwaived, on exactly the bytes that are sent.
  Check: pipeline/release_auth.py is the one authorisation every send path uses: exact gate inventory v1 (REQUIRED rows exactly 'PASS' with evidence executed and samples >= 1; MONITORING rows present with an exact verdict, reported, not deciding: addendum '22:15' item 4; any other or missing row = blocker); run_fresh writes ATTESTATION.json last (holds anywhere = HOLD; executed code at the launch revision; the finals and manifests must be the bytes the gates measured); authorise() re-hashes both finals, EDL, manifests, gate report, verification pack and sheets before the first send; telegram.deliver_run checks each file's digest again before its send, checkpoints every message, never resends an unknown outcome; the legacy send_telegram_preview is removed; replays are never deliverable. Tests: test_release_auth.py (the fail-closed mutation family), test_telegram_delivery.py, test_failure_blocks.py.
- L-k ONE CANONICAL FORM (orchestrator 2026-11-11 '21:10'): every text comparison in the pipeline uses pipeline/canon.py; two strings a listener hears as the same words compare equal, and a different number, unit, sign, name, negation or dropped word never does.
  Check: canon.canon_tokens / canon_aligned / same (entities, unicode, split tokens, numbers as values, currency and percent spoken order, signs, apostrophes kept); routed into quote verification, selection anchors, edge words, G3 / G3b, G18 (word_diff keeps units and signs; a repeat-only difference is decided by the audio, sentence_law.span_matches: GPT-cut F04 / F05), G20, G1 / G13 (token runs, never substrings), PIN approved text. Tests: test_canon.py (200 real sentences x mutations equal; real differences unequal; TestSites fails any ad-hoc normaliser outside canon.py).
- L-l A MODEL REPLY COUNTS ONLY WHOLE (red-team order 2026-11-11 '21:55', B): a local-model reply feeds a decision only when every field that decision reads is present, of its exact type, inside its enumerated values and ranges; anything else is a failed call (INCONCLUSIVE / unrated / not producible), never a pass, an agreement or a default.
  Check: pipeline/story_semantics._field / _str_list and the validators _v_derive, _v_adj, _v_sup, _v_react, _v_label, _v_rate run inside LocalLLM.chat_json (bounded retries, then LLMParseError; a cached reply is re-validated on read and asked again when it fails); verify_support counts SUPPORTS only when same_actor_action_object is exactly True and presented_as is exactly 'current' ('unclear' = INCONCLUSIVE; GPT-select F01); every passage is rated exactly once with a 1-5 number and a known fault, never clamped (GPT-select F12); a positive adjudication carries its chunk ids and quote; harmless variations the prompt allows are accepted (an integral float as an int, enum case / whitespace, an absent optional reason, null aliases). Tests: test_editorial_robust.py (one defect per deciding field = a failed call; through the real call = INCONCLUSIVE, never counted; harmless variations accepted), test_dec13_clusters TestLLMCache.
- LAW 20 / M2: gate thresholds are constants; a failed gate is a hard stop; never change what a check
  accepts to make a render pass; never reclassify a failing gate as a false positive.
- M12 FAIL CLOSED: missing data, model failure or an exception rejects; it never produces a pass.
- LAW 22: the frozen v2f reference (references/v2f_2026-11-06) must keep re-rendering byte-identically.
- Smallest diff; no new renderer, compositor or selector (M1); GPU0 only; no publishing.



---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_2005/C1_STEP.diff (200 lines)
```
   1 | diff --git a/pipeline/context_integrity.py b/pipeline/context_integrity.py
   2 | index 3f32a94..ec86be7 100644
   3 | --- a/pipeline/context_integrity.py
   4 | +++ b/pipeline/context_integrity.py
   5 | @@ -298,6 +298,16 @@ def source_for(x, sources):
   6 |      return sources[x.get("source_key") or x["video_id"]]
   7 |  
   8 |  
   9 | +def show_date(now):
  10 | +    """RULING 126 (1) (orchestrator 20:00 ET Nov 16): the show date step A and the context check carry is the ET calendar
  11 | +    date (PBX's audience and his day), never the UTC date (from 19:00 ET the UTC date is already tomorrow's).
  12 | +    -> 'YYYY-MM-DD', or None without a clock."""
  13 | +    if now is None:
  14 | +        return None
  15 | +    from zoneinfo import ZoneInfo
  16 | +    return now.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
  17 | +
  18 | +
  19 |  def contexts_from_sources(package, sources, now=None):
  20 |      """{label: {"text": the window with <selected> marks, "title", "channel", "published", "show_date", "window"}}."""
  21 |      out = {}
  22 | @@ -309,7 +319,7 @@ def contexts_from_sources(package, sources, now=None):
  23 |              continue                                # judged as unavailable (require_all)
  24 |          out[seg["label"]] = {"text": text, "title": src.title or "", "channel": seg["channel"], "window": win,
  25 |                               "published": str(src.published_at or "")[:16],
  26 | -                             "show_date": now.strftime("%Y-%m-%d") if now else None}
  27 | +                             "show_date": show_date(now)}                 # ruling 126 (1): the ET date
  28 |      return out
  29 |  
  30 |  
  31 | diff --git a/pipeline/package.py b/pipeline/package.py
  32 | index 038c3c9..4e971be 100644
  33 | --- a/pipeline/package.py
  34 | +++ b/pipeline/package.py
  35 | @@ -509,6 +509,25 @@ def _load_cache(path):
  36 |          return {}
  37 |  
  38 |  
  39 | +def step_a_key(m, context):
  40 | +    """RULING 58 / RULING 126 (1): a step-A verdict's cache key: the moment id, the sha256 of its text, the sha256 of the
  41 | +    exact context step A reads, and the prompt's version. The show date enters the context's sha ONLY for a moment that
  42 | +    holds time words (time_sensitive: the miner's flag, a recency word or a current price in its own words); a moment
  43 | +    with none is judged the same on any date and is never paid for again because a clock rolled over."""
  44 | +    kc = context if time_sensitive(m) else {k: v for k, v in context.items() if k != "show_date"}
  45 | +    return f"{m['moment_id']}:{text_sha(m['text'])}:{text_sha(json.dumps(kc, sort_keys=True))}:{STEP_A_VERSION}"
  46 | +
  47 | +
  48 | +def step_a_old_keys(m, context, now):
  49 | +    """RULING 126 (1), for a moment with no time words: the keys its verdict was cached under before the date left the
  50 | +    key (the context with the UTC show date in it, today's and yesterday's: all a moment inside the 12-hour window can
  51 | +    hold) -> [key]. Read once; the verdict found is written again under step_a_key."""
  52 | +    from datetime import timedelta
  53 | +    return [f"{m['moment_id']}:{text_sha(m['text'])}:"
  54 | +            f"{text_sha(json.dumps(dict(context, show_date=(now - timedelta(days=k)).strftime('%Y-%m-%d')), sort_keys=True))}"
  55 | +            f":{STEP_A_VERSION}" for k in (0, 1)]
  56 | +
  57 | +
  58 |  def _cache_put(path, new):
  59 |      """Merge {key: {back-end: verdict}} into the cache file (read again under the lock, .tmp then rename)."""
  60 |      if not path or not new:
  61 | @@ -554,6 +573,9 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  62 |      db, cdb = _load_store(store), _load_cache(cache)
  63 |      wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
  64 |      off = lambda name: (lambda b: b is not None and b.vendor not in wv and b.family not in wf)(router.backends.get(name))
  65 | +    pick = lambda key: next((x for name, x in sorted((cdb.get(key) or {}).items())        # a cached verdict off the
  66 | +                             if isinstance(x, dict) and off(name) and x.get("backend") == name), None)   # writers'
  67 | +    moved = {}                                          # ruling 126 (1): old-key verdicts, written under the new key
  68 |      a_by, fails, vendors, families, todo, contexts, keys = {}, {}, set(), set(), [], {}, {}
  69 |      for m in order:
  70 |          mid = m["moment_id"]
  71 | @@ -563,12 +585,15 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  72 |              continue                # moment is not cleared; it never poisons its batch's call
  73 |          contexts[mid] = {"text": text, "title": src_of(m, sources).title or "", "channel": _name(m, ctx),
  74 |                           "window": win, "published": str(m.get("published_at") or "")[:16],
  75 | -                         "show_date": ctx.now.strftime("%Y-%m-%d")}
  76 | -        keys[mid] = f"{mid}:{text_sha(m['text'])}:{text_sha(json.dumps(contexts[mid], sort_keys=True))}:{STEP_A_VERSION}"
  77 | +                         "show_date": CI.show_date(ctx.now)}       # RULING 126 (1): the ET date
  78 | +        keys[mid] = step_a_key(m, contexts[mid])                          # ruling 126 (1): the date only with time words
  79 |          rec = db.get(f"{mid}:{STEP_A_VERSION}")
  80 |          if not (isinstance(rec, dict) and off(rec.get("backend"))):
  81 | -            rec = next((x for name, x in sorted((cdb.get(keys[mid]) or {}).items())
  82 | -                        if isinstance(x, dict) and off(name) and x.get("backend") == name), None)
  83 | +            rec = pick(keys[mid])
  84 | +            if rec is None and not time_sensitive(m):    # RULING 126 (1): a verdict cached before the date left the key
  85 | +                rec = next((r for r in map(pick, step_a_old_keys(m, contexts[mid], ctx.now)) if r is not None), None)
  86 | +                if rec is not None:
  87 | +                    moved.setdefault(keys[mid], {})[rec["backend"]] = rec
  88 |          if rec is not None:
  89 |              b = router.backends[rec["backend"]]
  90 |              a_by[mid], fails[mid] = rec, CI.a_failures(rec)
  91 | @@ -611,7 +636,7 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  92 |          with open(store + ".tmp", "w") as f:
  93 |              json.dump(db, f, indent=1)
  94 |          os.replace(store + ".tmp", store)
  95 | -    _cache_put(cache, new)
  96 | +    _cache_put(cache, dict(moved, **new))              # ruling 126 (1): the moved verdicts under their new keys
  97 |      return a_by, fails, vendors, families
  98 |  
  99 |  
 100 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 101 | index c7d52b5..5996416 100644
 102 | --- a/tests/package/test_medley.py
 103 | +++ b/tests/package/test_medley.py
 104 | @@ -1256,12 +1256,14 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
 105 |          B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 106 |          return type("R", (), {"backends": {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall", "deepseek")}})()
 107 |  
 108 | -    def fake(self, calls, fail=frozenset()):
 109 | +    def fake(self, calls, fail=frozenset(), seen=None):
 110 |          import context_integrity as CI
 111 |          from test_gates import a_item
 112 |  
 113 |          def step_a(router_, contexts, wv, seed=7, writer_family=None, deadline_s=None, failover=False, kind=None):
 114 |              calls.append((sorted(contexts), seed))
 115 | +            if seen is not None:
 116 | +                seen.update(contexts)                    # ruling 126 (1): the exact contexts step A was given
 117 |              if set(contexts) & set(fail):
 118 |                  raise RuntimeError("the batch reply was out of contract")
 119 |              b = "heimdall:deepseek" if "xai" in (wv or set()) else "xai:grok"
 120 | @@ -1310,12 +1312,78 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
 121 |              calls.clear()
 122 |              later = E.Context(NOW + timedelta(days=1), REG)
 123 |              PK.prescreen(self.router(), ms[:3], srcs, later, {"heimdall"}, {"deepseek"}, cache=cache)
 124 | -            self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01", "m02"])   # a new show date
 125 | +            self.assertEqual(calls, [])                  # RULING 126 (1): no time words: a new show date asks nothing
 126 | +            ts = [dict(m, risk=["time_sensitive"]) for m in ms[:2]]          # the miner's flag: time words
 127 | +            PK.prescreen(self.router(), ts, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 128 | +            calls.clear()
 129 | +            PK.prescreen(self.router(), ts, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 130 | +            self.assertEqual(calls, [])                  # the same show date: paid for once
 131 | +            PK.prescreen(self.router(), ts, srcs, later, {"heimdall"}, {"deepseek"}, cache=cache)
 132 | +            self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01"])   # time words: a new show date
 133 |              calls.clear()
 134 |              a_by, _, _, _ = PK.prescreen(self.router(), ms[:3], srcs, ctx(), {"xai"}, {"grok"}, cache=cache)
 135 |              self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01", "m02"])   # never the writer's
 136 |              self.assertEqual({a["backend"] for a in a_by.values()}, {"heimdall:deepseek"})     # vendor's verdict
 137 |  
 138 | +    def test_ruling_126_the_show_date_is_the_et_date(self):
 139 | +        """RULING 126 (1): the show date step A and the context check carry is the ET date, not the UTC date (19:30 ET
 140 | +        Nov 10 is 00:30 UTC Nov 11)."""
 141 | +        import context_integrity as CI
 142 | +        import tempfile
 143 | +        from datetime import datetime, timezone
 144 | +        evening = datetime(2026, 11, 11, 0, 30, tzinfo=timezone.utc)
 145 | +        self.assertEqual(CI.show_date(evening), "2026-11-10")
 146 | +        self.assertEqual(CI.show_date(datetime(2026, 11, 11, 5, 0, tzinfo=timezone.utc)), "2026-11-11")
 147 | +        self.assertIsNone(CI.show_date(None))
 148 | +        ms, srcs = self.pool(2)
 149 | +        calls, seen = [], {}
 150 | +        self.fake(calls, seen=seen)
 151 | +        with tempfile.TemporaryDirectory() as d:
 152 | +            PK.prescreen(self.router(), ms, srcs, E.Context(evening, REG), {"heimdall"}, {"deepseek"},
 153 | +                         cache=os.path.join(d, "c.json"))
 154 | +        self.assertEqual({c["show_date"] for c in seen.values()}, {"2026-11-10"})
 155 | +        seg = {"label": "clip_01", "video_id": ms[0]["video_id"], "k0": 1, "k1": 1, "words": ms[0]["words"],
 156 | +               "channel": "C00"}
 157 | +        self.assertEqual(CI.contexts_from_sources({"segments": [seg]}, srcs, evening)["clip_01"]["show_date"],
 158 | +                         "2026-11-10")
 159 | +
 160 | +    def test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved(self):
 161 | +        """RULING 126 (1): a moment with no time words finds its verdict under the key it was cached under before (the
 162 | +        UTC show date in it, today's or yesterday's UTC date) and pays nothing; the verdict is written under its new key;
 163 | +        a time-sensitive moment never takes an old key's verdict; older than yesterday is not looked for."""
 164 | +        import tempfile
 165 | +        ms, srcs = self.pool(4)
 166 | +        ms[3] = dict(ms[3], risk=["time_sensitive"])
 167 | +        calls, seen = [], {}
 168 | +        self.fake(calls, seen=seen)
 169 | +        asked = lambda: sorted(sum((c[0] for c in calls), []))
 170 | +        with tempfile.TemporaryDirectory() as d:
 171 | +            c1 = os.path.join(d, "c1.json")
 172 | +            PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=c1)
 173 | +            with open(c1) as f:
 174 | +                now_keys = json.load(f)
 175 | +            old = {}
 176 | +            for m in ms:                                 # the same verdicts under the keys used before ruling 126 (1)
 177 | +                c = dict(seen[m["moment_id"]], show_date=NOW.strftime("%Y-%m-%d"))
 178 | +                old[f"{m['moment_id']}:{PK.text_sha(m['text'])}:{PK.text_sha(json.dumps(c, sort_keys=True))}:"
 179 | +                    f"{PK.STEP_A_VERSION}"] = now_keys[PK.step_a_key(m, seen[m["moment_id"]])]
 180 | +            for days, want in ((20 / 24, ["m03"]), (1 + 20 / 24, ["m00", "m01", "m02", "m03"])):
 181 | +                c2 = os.path.join(d, f"c2_{days:.2f}.json")
 182 | +                with open(c2, "w") as f:
 183 | +                    json.dump(old, f)
 184 | +                calls.clear()
 185 | +                later = E.Context(NOW + timedelta(days=days), REG)
 186 | +                a_by, fails, _, _ = PK.prescreen(self.router(), ms, srcs, later, {"heimdall"}, {"deepseek"}, cache=c2)
 187 | +                self.assertEqual((asked(), len(a_by)), (want, 4), days)
 188 | +                if days < 1:
 189 | +                    with open(c2) as f:
 190 | +                        moved = json.load(f)
 191 | +                    for m in ms[:3]:                     # written under the new key: found there next time
 192 | +                        self.assertIn(PK.step_a_key(m, seen[m["moment_id"]]), moved)
 193 | +                    calls.clear()
 194 | +                    PK.prescreen(self.router(), ms, srcs, later, {"heimdall"}, {"deepseek"}, cache=c2)
 195 | +                    self.assertEqual(calls, [])
 196 | +
 197 |      def test_ruling_101_plan_only_lists_what_the_screen_would_ask_and_asks_nothing(self):
 198 |          import tempfile
 199 |          ms, srcs = self.pool(10)
 200 | 
```

---

pp-selectid: RULING 126 (1) (orchestrator 20:00 ET Nov 16), verbatim: "THE SHOW DATE: it is meant to be the ET date (PBX's
audience and his day), not UTC, and a verdict should carry the date in its cache key ONLY when the moment holds time words
(the free time-word screen already knows which do); a moment with no time words is judged the same on any date and must
never be re-paid because a clock rolled over. Build both, audit-first on Heimdall, and LAND THEM AFTER TONIGHT'S BUILDS".
Files: pipeline/context_integrity.py, pipeline/package.py, tests/package/test_medley.py.

THE CHANGE:
(1) context_integrity.show_date(now): the ET calendar date of the clock (zoneinfo America/New_York), None without one.
    Used by contexts_from_sources (the context check's excerpts; its callers, UNCHANGED, pass the build's clock:
    package.py:2467, 2516, 2561, 2691; spotlight.py:1125, 1143) and by package.prescreen's step-A contexts. Before, both
    used now.strftime on the run clock, which is UTC (eligibility.py:167: "Context.now must be an aware datetime (the
    run clock, UTC)"), so from 19:00 ET the show date was tomorrow's.
(2) package.step_a_key(m, context): the step-A cache key (moment id, sha256 of its text, sha256 of the context step A
    reads, the prompt's version, as before) hashes the context WITHOUT its show_date when the moment is not
    time-sensitive. The time-word screen is UNCHANGED package.time_sensitive (package.py:210): the miner's
    "time_sensitive" risk flag, OR a recency word in the clip's own words (vo_fidelity.time_words, vo_fidelity.py:411),
    OR a current-kind price. The prompt itself still carries the (ET) show date; only the cache key leaves it out.
(3) package.step_a_old_keys(m, context, now) + prescreen: for a moment that is NOT time-sensitive and has no verdict
    under its new key, the keys the code used before (the context hashed WITH the UTC show date, today's and
    yesterday's UTC dates: a moment inside the 12-hour publish window cannot hold an older one) are read, with the same
    "off the writers" filter (pick, as before); a verdict found there is used (no call) and written under the new key
    (moved, merged into the one cache write; _cache_put UNCHANGED, package.py:512). A time-sensitive moment never takes
    an old key's verdict. Without this, landing (2) would re-pay every cached moment once.

NOT CHANGED: the context check (CI.check_contexts) has no per-moment cache: its replies are replayed by the exact prompt,
which now carries the ET date (a line-up re-asked on a new ET date is asked again; it was so before, on the UTC date).

TESTS (test_medley TestRuling58StepAEveryCandidate): the cross-build test now asks: a new show date asks NOTHING for
moments with no time words, and asks again for time-sensitive ones (the miner's flag); new: the ET date at 00:30 UTC
(19:30 ET) in step A's contexts and in contexts_from_sources; new: an old-key verdict is read once (no call) for a
moment without time words, written under its new key (no call the next time), never taken by a time-sensitive moment,
and not looked for past yesterday's UTC date. Mutations R1-R9 after a control run.

PLEASE CHECK: (a) that a time-sensitive moment's verdict can never be reused across show dates; (b) the old-key read
(the exact old key format, the date window, the writers' filter, the write under the new key); (c) the ET date at the
DST edges (zoneinfo); (d) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
