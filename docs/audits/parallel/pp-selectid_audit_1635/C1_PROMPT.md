# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1635
# Branch: pp-selectid
# Generated: 2026-11-13 16:30 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1635/C1_STEP.diff (141 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index ce8c6e4..dc2f3fc 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -2065,7 +2065,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
   6 |      usd0 = _spent(spend)
   7 |      import visual_pin as VP                            # ruling 70
   8 |      vcache = VP.load_cache(visual_cache) if visual_cache else {}
   9 | -    out_visual = {"calls": 0, "cached": 0, "usd": 0.0, "unmeasured": 0, "flags": 0}
  10 | +    out_visual = {"calls": 0, "cached": 0, "usd_reported": 0.0, "usd_estimate": 0.0, "estimated_calls": 0,
  11 | +                  "unmeasured": 0, "flags": 0}   # ruling 70: the vendor's figure and the estimate never mixed
  12 |  
  13 |      def see(ms_):                                      # RULING 70: the clips' sheets, judged (cached per moment)
  14 |          todo = [m for m in ms_ if not (m.get("visual") or {}).get("measured")]
  15 | @@ -2075,7 +2076,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  16 |              for m, rec in zip(todo, recs):
  17 |                  m["visual"] = rec
  18 |                  out_visual["cached" if rec.get("cached") else "calls"] += 1     # audit 1541 C1: every attempt
  19 | -                out_visual["usd"] = round(out_visual["usd"] + float(rec.get("usd") or 0.0), 6)
  20 | +                if rec.get("usd_basis") == "reported":
  21 | +                    out_visual["usd_reported"] = round(out_visual["usd_reported"] + float(rec.get("usd") or 0.0), 6)
  22 | +                elif rec.get("usd_basis") == "estimate":
  23 | +                    out_visual["usd_estimate"] = round(out_visual["usd_estimate"] + float(rec.get("usd") or 0.0), 6)
  24 | +                    out_visual["estimated_calls"] += 1
  25 |                  out_visual["unmeasured"] += 0 if rec.get("measured") else 1
  26 |                  out_visual["flags"] += len(rec.get("flags") or [])
  27 |              VP.save_cache(visual_cache, vcache)
  28 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
  29 | index 6cb6417..4cecca8 100644
  30 | --- a/pipeline/visual_pin.py
  31 | +++ b/pipeline/visual_pin.py
  32 | @@ -228,6 +228,19 @@ def sealed(rec):
  33 |      return out
  34 |  
  35 |  
  36 | +def cost(r):
  37 | +    """A reply's cost as RULING 70 reports it: {"usd": the vendor-reported figure where the reply carries one (xAI
  38 | +    cost_in_usd_ticks, Heimdall usage.cost: Reply.usage["usd_reported"]), "usd_basis": "reported"}; else the price-table
  39 | +    estimate (Reply.usd, an upper bound) with "usd_basis": "estimate"; a reply served from its recording costs nothing
  40 | +    ("cached")."""
  41 | +    if getattr(r, "cached", False):
  42 | +        return {"usd": 0.0, "usd_basis": "cached"}
  43 | +    rep = (getattr(r, "usage", None) or {}).get("usd_reported")
  44 | +    if isinstance(rep, (int, float)) and not isinstance(rep, bool):
  45 | +        return {"usd": round(float(rep), 6), "usd_basis": "reported"}
  46 | +    return {"usd": round(float(getattr(r, "usd", 0.0) or 0.0), 6), "usd_basis": "estimate"}
  47 | +
  48 | +
  49 |  def visual_for(router, m, work_dir, cache, seed=7, log=print):
  50 |      """The clip's visual record (cached per moment and span). Not measured on any failure: never a pass (law L-m).
  51 |      -> {"version", "measured", "flags", "third_person", "on_screen_text", "lower_third", "sheet" {"name", "sha256",
  52 | @@ -238,12 +251,12 @@ def visual_for(router, m, work_dir, cache, seed=7, log=print):
  53 |      if hit is not None:                              # the judged sheet, still on disk with the judged bytes
  54 |          p = os.path.join(work_dir, "visual", (hit.get("sheet") or {}).get("name") or "-")
  55 |          if _sha_of(p) == (hit.get("sheet") or {}).get("sha256"):
  56 | -            return dict(hit, cached=True, usd=0.0, sheet=dict(hit["sheet"], path=p))
  57 | +            return dict(hit, cached=True, usd=0.0, usd_basis="cached", sheet=dict(hit["sheet"], path=p))
  58 |      try:
  59 |          video = fetch(m["video_id"], float(m["start"]), float(m["end"]), work_dir)
  60 |          path, sha, ts = sheet(video, float(m["start"]), float(m["end"]), work_dir)
  61 |          if hit is not None and sha == hit["sheet"]["sha256"]:        # rebuilt, the same bytes: the same verdict
  62 | -            return dict(hit, cached=True, usd=0.0, sheet=dict(hit["sheet"], path=path))
  63 | +            return dict(hit, cached=True, usd=0.0, usd_basis="cached", sheet=dict(hit["sheet"], path=path))
  64 |          with open(path, "rb") as f:
  65 |              b64 = base64.b64encode(f.read()).decode()
  66 |      except Exception as e:                       # noqa: BLE001  no sheet: not measured (law L-m), never a crash
  67 | @@ -258,10 +271,10 @@ def visual_for(router, m, work_dir, cache, seed=7, log=print):
  68 |              rec = {"version": VERSION, "measured": True, **v, "flags": flags(v),
  69 |                     "sheet": {"name": os.path.basename(path), "sha256": sha, "times": ts, "path": path},
  70 |                     "backend": r.backend, "replayed": bool(getattr(r, "replayed", False)),
  71 | -                   "usd": 0.0 if getattr(r, "cached", False) else float(getattr(r, "usd", 0.0) or 0.0),
  72 | +                   **cost(r),
  73 |                     "usage": getattr(r, "usage", None), "cached": bool(getattr(r, "cached", False))}
  74 |              if cache is not None and not rec["replayed"]:
  75 | -                cache[k] = {x: y for x, y in rec.items() if x not in ("cached", "usd")}
  76 | +                cache[k] = {x: y for x, y in rec.items() if x not in ("cached", "usd", "usd_basis")}
  77 |              return rec
  78 |          except Exception as e:                   # noqa: BLE001  fail closed; each try's reason is kept (C2)
  79 |              if r is not None and not isinstance(e, (P.ProviderError, P.SpendLimit)) and hasattr(router, "reject"):
  80 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  81 | index 6647ab8..63f93ab 100644
  82 | --- a/tests/package/proof_ledger.py
  83 | +++ b/tests/package/proof_ledger.py
  84 | @@ -245,8 +245,10 @@ def main(argv=None):
  85 |                                "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
  86 |      vis = res.get("visual") or {}
  87 |      say(f"  visual (ruling 70): {vis.get('calls', 0)} sheet(s) asked ({vis.get('unmeasured', 0)} not measured), "
  88 | -        f"{vis.get('cached', 0)} cached, {vis.get('flags', 0)} flag(s); measured cost ${vis.get('usd', 0):.4f} "
  89 | -        f"(the router's figure: vendor-reported where the reply carries it)")
  90 | +        f"{vis.get('cached', 0)} cached, {vis.get('flags', 0)} flag(s); cost ${vis.get('usd_reported', 0):.4f} "
  91 | +        f"vendor-reported" + (f" + ${vis.get('usd_estimate', 0):.4f} price-table estimate for "
  92 | +                              f"{vis.get('estimated_calls', 0)} call(s) with no vendor figure"
  93 | +                              if vis.get("estimated_calls") else ""))
  94 |      say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${PL.LY_LIMIT_USD:.2f} "
  95 |          f"vendor-reported after this build (before it: ${spent0:.2f})")
  96 |      try:                                                 # audit 1420 C2: a registry failure never loses the record;
  97 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  98 | index ee2d718..dea7ca8 100644
  99 | --- a/tests/package/test_medley.py
 100 | +++ b/tests/package/test_medley.py
 101 | @@ -624,7 +624,8 @@ class Rig:
 102 |                                   "finding": "no third person"},
 103 |                  "on_screen_text": [], "lower_third": {"name": None, "text": None},
 104 |                  "sheet": {"name": f"visual_{m['moment_id']}.jpg", "sha256": "0" * 64, "times": [0.0], "path": "/x"},
 105 | -                "backend": "xai_vision:grok-4.7", "replayed": False, "usd": 0.002, "cached": False}
 106 | +                "backend": "xai_vision:grok-4.7", "replayed": False, "usd": 0.002, "usd_basis": "reported",
 107 | +                "cached": False}
 108 |          return dict(base, **self.visuals.get(m["moment_id"], {}))
 109 |  
 110 |      def onset(self, m, *a, **k):
 111 | @@ -1623,6 +1624,7 @@ class TestRuling70Visual(unittest.TestCase):
 112 |          self.assertEqual([sg["visual"]["sheet"]["name"] for sg in pk["segments"]],
 113 |                           ["visual_h.jpg", "visual_x.jpg", "visual_y.jpg"])
 114 |          self.assertNotIn("path", pk["segments"][0]["visual"]["sheet"])  # never a scratch path in the seal
 115 | +        self.assertEqual((out["visual"]["usd_reported"], out["visual"]["usd_estimate"]), (0.006, 0.0))
 116 |          self.assertIn("visual", package_pin.MEDLEY_GATES)
 117 |          pin = package_pin.to_pin(spk(pk), "r")
 118 |          self.assertIn("visual", pin["segments"][1])
 119 | diff --git a/tests/package/test_visual_pin.py b/tests/package/test_visual_pin.py
 120 | index df3c51b..22f9647 100644
 121 | --- a/tests/package/test_visual_pin.py
 122 | +++ b/tests/package/test_visual_pin.py
 123 | @@ -63,6 +63,17 @@ class TestContract(unittest.TestCase):
 124 |          self.assertIn("not measured", VP.hook_block({"measured": False}))
 125 |          self.assertIn("not measured", VP.hook_block(None))
 126 |  
 127 | +    def test_the_cost_is_the_vendors_figure_and_an_estimate_is_labelled(self):
 128 | +        class R:
 129 | +            cached, usd = False, 0.37
 130 | +        r = R()
 131 | +        r.usage = {"in": 2760, "out": 6226, "usd_reported": 0.041144}
 132 | +        self.assertEqual(VP.cost(r), {"usd": 0.041144, "usd_basis": "reported"})
 133 | +        r.usage = {"in": 2760, "out": 6226}
 134 | +        self.assertEqual(VP.cost(r), {"usd": 0.37, "usd_basis": "estimate"})
 135 | +        r.cached = True
 136 | +        self.assertEqual(VP.cost(r), {"usd": 0.0, "usd_basis": "cached"})
 137 | +
 138 |      def test_the_seal_never_holds_a_scratch_path_or_a_cost(self):
 139 |          s = VP.sealed({"version": "v", "measured": True, "flags": [], "third_person": {}, "on_screen_text": [],
 140 |                         "lower_third": {}, "backend": "b", "replayed": False, "usd": 0.01, "cached": True,
 141 | 
```

---

You are auditing a SMALL reporting fix on branch pp-selectid (Protocol Pulse: the builder of sealed medley pins).
Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- The router (providers.Router) returns a Reply whose .usd is the PRICE-TABLE ESTIMATE (usage x the config's
  upper-bound $ per 1M). Where a vendor reports its own cost, the back-end puts it in Reply.usage["usd_reported"]:
  xAI's cost_in_usd_ticks / 1e10, Heimdall's usage.cost.
- The spend ledger keeps the two apart (usd_reported vs usd_estimate), per the project's rule: record the vendor's
  figure, label an estimate as an estimate.
- RULING 70 (orchestrator 15:29 Nov 13): "Report the measured cost on the first build."

The defect:
- visual_pin.visual_for recorded "usd" from Reply.usd (the estimate).
- The build summed that, and the driver's log line called it "measured cost ... vendor-reported where the reply
  carries it".
- On the first build it printed $0.3646 for 3 sheets. The ledger shows the vendor-reported cost was $0.0890; the
  $0.3646 is the price-table upper bound.

The fix:
1. visual_pin.cost(reply) returns the cost and its basis:
   - {"usd": usage["usd_reported"], "usd_basis": "reported"} when the vendor reported one;
   - else {"usd": Reply.usd, "usd_basis": "estimate"};
   - {"usd": 0.0, "usd_basis": "cached"} for a reply served from its recording.
   Cache hits carry usd_basis "cached". Neither usd nor usd_basis enters the cache or the seal.
2. package.build's out["visual"] keeps usd_reported and usd_estimate apart (plus estimated_calls); they are never
   summed under one label.
3. The driver's log line prints "$X vendor-reported", and, only when some call carried no vendor figure,
   "+ $Y price-table estimate for N call(s) with no vendor figure".
4. Tests: test_visual_pin covers the three bases; test_medley covers the build's split totals. test_visual_pin 11,
   test_medley 138 OK.

Check: that no path labels an estimate as reported (or the reverse), and that a bool or a missing figure never counts
as reported. Also that nothing here changes a gate, the seal or the cache key.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

