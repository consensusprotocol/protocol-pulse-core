# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_1750
# Branch: pp-selectid
# Generated: 2026-11-16 17:50 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_1750/C1_STEP.diff (204 lines)
```
   1 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
   2 | index ec6d16f..544684c 100644
   3 | --- a/tests/package/proof_ledger.py
   4 | +++ b/tests/package/proof_ledger.py
   5 | @@ -217,11 +217,38 @@ def delivered_pins(paths):
   6 |      return spans, newest, pins
   7 |  
   8 |  
   9 | -def build_router(routing, shadow, shadow_log):
  10 | +STOP_CEILING_USD = 1.25          # ORDER 17:50 ET Nov 16: --stop-usd at most this ('ADD 25 CENTS': a day cap of $1.25)
  11 | +
  12 | +
  13 | +def read_only(path):
  14 | +    """ORDER 17:50 ET Nov 16 ("spend the fresh dollar on ONE line-up at a time, the likeliest first; do not screen the
  15 | +    whole held pool at Grok"): the --only file, {"ids": [this build's moment ids, at least one], "why": a reason}.
  16 | +    -> {"ids", "why", "file"}, or ValueError."""
  17 | +    with open(path) as f:
  18 | +        d = json.load(f)
  19 | +    ids = d.get("ids") if isinstance(d, dict) else None
  20 | +    if not (isinstance(ids, list) and ids and all(isinstance(x, str) and x for x in ids)) or \
  21 | +            not isinstance(d.get("why"), str) or not d["why"].strip():
  22 | +        raise ValueError(f"--only {path}: needs {{'ids': [moment ids], 'why': text}}")
  23 | +    return {"ids": list(dict.fromkeys(ids)), "why": d["why"].strip(), "file": path}
  24 | +
  25 | +
  26 | +def only_moments(moments, only):
  27 | +    """The --only set: the pool's moments it names, in the pool's order (a trimmed variant is made later, beside its
  28 | +    parent, as for any moment). -> (moments, record: file, why, asked, kept, missing)."""
  29 | +    want = set(only["ids"])
  30 | +    kept = [m for m in moments if m["moment_id"] in want]
  31 | +    have = {m["moment_id"] for m in kept}
  32 | +    return kept, {"file": only["file"], "why": only["why"], "asked": len(only["ids"]), "kept": len(kept),
  33 | +                  "missing": [x for x in only["ids"] if x not in have]}
  34 | +
  35 | +
  36 | +def build_router(routing, shadow, shadow_log, limit=None):
  37 |      """The build's router: ruling 48's ledger and limit, the routing's chains (frozen legs out), the evidence file
  38 |      (item 55), ruling 86's shadow, ruling 87's shared Heimdall health and Plan B chains, ruling 99's circuit breaker,
  39 |      ruling 100's deadline table (recomputed daily from the build's own recorded answers)."""
  40 | -    return P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
  41 | +    return P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND,
  42 | +                    limit_usd=PL.LY_LIMIT_USD if limit is None else limit,        # ORDER 17:50: --stop-usd
  43 |                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
  44 |                      routing=routing, shadow=shadow, shadow_log=shadow_log,
  45 |                      health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD,      # ruling 87
  46 | @@ -297,12 +324,14 @@ def with_variants(moments, sources, ctx, inputs, say, results_dir=None, directiv
  47 |      return [m for m in moments if m["moment_id"] not in replaced] + variants
  48 |  
  49 |  
  50 | -def start_refused(spent0):
  51 | +def start_refused(spent0, stop=None):
  52 |      """RULING 48, with the orchestrator's stop of 13:02 Nov 14 (the $16 stop passed with leave; at $19 stop and tell on
  53 | -    STATE line 1 in capitals): no build starts at or over PL.LY_STOP_USD. -> the refusal line, or None."""
  54 | -    if spent0 >= PL.LY_STOP_USD:
  55 | +    STATE line 1 in capitals): no build starts at or over PL.LY_STOP_USD (or this build's --stop-usd, ORDER 17:50 ET
  56 | +    Nov 16). -> the refusal line, or None."""
  57 | +    stop = PL.LY_STOP_USD if stop is None else stop
  58 | +    if spent0 >= stop:
  59 |          return (f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
  60 | -                f"vendor reports none), at or over the ${PL.LY_STOP_USD:.2f} stop: no build starts; the orchestrator "
  61 | +                f"vendor reports none), at or over the ${stop:.2f} stop: no build starts; the orchestrator "
  62 |                  f"decides (13:02 Nov 14: SAY IT ON STATE LINE 1 IN CAPITALS)")
  63 |      return None
  64 |  
  65 | @@ -354,6 +383,10 @@ def main(argv=None):
  66 |      ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
  67 |      ap.add_argument("--routing", choices=P.ROUTINGS, default=None,
  68 |                      help="RULING 85: 'today' or 'heimdall_first' (default: model_providers.json routing.mode)")
  69 | +    ap.add_argument("--only", metavar="FILE", help="ORDER 17:50 ET Nov 16: {'ids': [moment ids], 'why': text}: this "
  70 | +                    "build takes only those moments of the pool, every gate as before (one line-up at a time)")
  71 | +    ap.add_argument("--stop-usd", type=float, default=None, help="ORDER 17:50 ET Nov 16: this build's outside-dollar "
  72 | +                    f"limit (no build starts at it; the router stops outside calls at it), in (0, {STOP_CEILING_USD}]")
  73 |      ap.add_argument("--from-candidate", metavar="BUILD_DIR[:N]",
  74 |                      help="RULING 66: try ONLY the line-up that passed the clips-alone verdict in this earlier build's "
  75 |                           "record (its tried[N]; default the first that passed), as it was judged")
  76 | @@ -370,6 +403,9 @@ def main(argv=None):
  77 |          if since > now:
  78 |              raise ValueError(f"since {since.isoformat()} is after now")
  79 |          cand = None
  80 | +        only = read_only(a.only) if a.only else None     # ORDER 17:50 ET Nov 16: read before anything is written
  81 | +        if a.stop_usd is not None and not 0 < a.stop_usd <= STOP_CEILING_USD:
  82 | +            raise ValueError(f"--stop-usd {a.stop_usd} is outside (0, {STOP_CEILING_USD}]")
  83 |          if a.from_candidate:                             # RULING 66: read before anything is written
  84 |              cdir, sep, idx = a.from_candidate.rpartition(":")
  85 |              cdir, idx = (cdir, idx) if sep and idx.isdigit() else (a.from_candidate, "")
  86 | @@ -428,6 +464,10 @@ def main(argv=None):
  87 |                                                 ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"),
  88 |                                                 word_pass_refused=wp_refused)
  89 |      inputs["word_pass"] = wp_rep
  90 | +    if only is not None:                                 # ORDER 17:50 ET Nov 16: one candidate set, before variants
  91 | +        moments, inputs["only"] = only_moments(moments, only)
  92 | +        say(f"  ORDER 17:50: --only: {inputs['only']['kept']} of {inputs['only']['asked']} listed moments in this pool "
  93 | +            f"({only['why']})" + (f"; not in it: {inputs['only']['missing']}" if inputs['only']['missing'] else ""))
  94 |      try:                                                 # RULING 95: when the next qualifying episode could arrive. It
  95 |          next_try = SPOT.next_attempt(rows, wp, now, refused=wp_refused)   # reads the inputs alone, so it is computed
  96 |      except Exception as e:                               # noqa: BLE001  here, recorded with them, and is a report,
  97 | @@ -450,7 +490,9 @@ def main(argv=None):
  98 |      rt = json.load(open(P.CONFIG)).get("routing") or {}
  99 |      routing = a.routing or rt.get("mode") or "today"
 100 |      shadow = build_shadow(routing, rt, SH.clean_streak)   # RULING 86 (Grok) / RULING 115 (qwen on every hook)
 101 | -    router = build_router(routing, shadow, os.path.join(out_dir, "SHADOW86.jsonl"))
 102 | +    limit = PL.LY_LIMIT_USD if a.stop_usd is None else a.stop_usd   # ORDER 17:50 ET Nov 16: --stop-usd
 103 | +    stop = PL.LY_STOP_USD if a.stop_usd is None else a.stop_usd
 104 | +    router = build_router(routing, shadow, os.path.join(out_dir, "SHADOW86.jsonl"), limit=limit)
 105 |      say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
 106 |          + (f"; SHADOW (ruling 86 / 115): {shadow}" if shadow else ""))
 107 |      live, live_why = PK.hook_live_bar()          # RULING 115: the bar in every build line, its floors and its sha
 108 | @@ -462,13 +504,13 @@ def main(argv=None):
 109 |      say(f"  RULING 100 (deadlines follow the model, table of {(router.deadlines or {}).get('computed_at')}): "
 110 |          f"{DT.text(router.deadlines, applies=applied(router)) or 'no row applies: each gateway keeps its number'}")
 111 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 112 | -    refused = start_refused(spent0)
 113 | +    refused = start_refused(spent0, stop)
 114 |      if refused:
 115 |          say(refused)
 116 |          logf.close()
 117 |          return 3
 118 | -    say(f"  spend (ruling 48): ${spent0:.2f} of ${PL.LY_LIMIT_USD:.2f} vendor-reported before this build (no build "
 119 | -        f"starts at ${PL.LY_STOP_USD:.2f})")
 120 | +    say(f"  spend (ruling 48): ${spent0:.2f} of ${limit:.2f} vendor-reported before this build (no build "
 121 | +        f"starts at ${stop:.2f})")
 122 |      own, used = PL.meter(router), PL.reply_meter(router)
 123 |      t0 = time.time()
 124 |      spotlit = SPOT.load_spotlit(SPOTLIGHTS)              # RULING 90: free; its pool goes to the clip scorer with the
 125 | @@ -624,8 +666,9 @@ def main(argv=None):
 126 |          after = round(router.spent(), 4)         # (after the shadows: their spend is in it)
 127 |      except Exception as e:                       # noqa: BLE001
 128 |          after = f"unreadable: {type(e).__name__}: {str(e)[:120]}"
 129 | -    res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": PL.LY_LIMIT_USD,
 130 | -                              "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
 131 | +    res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": limit, "stop": stop,
 132 | +                              "basis": PL.LY_LIMIT_BASIS, **({"order_17_50_stop": a.stop_usd}
 133 | +                                                             if a.stop_usd is not None else {})}
 134 |      line101 = ruling_101_line((res.get("prescreen") or {}).get("parallel_101"))   # RULING 101: the extra spend
 135 |      if line101:
 136 |          say(line101)
 137 | @@ -635,7 +678,7 @@ def main(argv=None):
 138 |          f"vendor-reported" + (f" + ${vis.get('usd_estimate', 0):.4f} price-table estimate for "
 139 |                                f"{vis.get('estimated_calls', 0)} call(s) with no vendor figure"
 140 |                                if vis.get("estimated_calls") else ""))
 141 | -    say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${PL.LY_LIMIT_USD:.2f} "
 142 | +    say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${limit:.2f} "
 143 |          f"vendor-reported after this build (before it: ${spent0:.2f})")
 144 |      evs = router.breaker_events                  # RULING 99: the circuit breaker's count, for STATE line 1
 145 |      try:
 146 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 147 | index 8364c0a..384c887 100644
 148 | --- a/tests/package/test_ledger_build.py
 149 | +++ b/tests/package/test_ledger_build.py
 150 | @@ -977,5 +977,53 @@ class TestRuling85NoXai(unittest.TestCase):
 151 |          second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
 152 |          self.assertEqual((first, second), (X, DS))                                 # Grok's first, deepseek's off it
 153 |  
 154 | +class TestOrder1750OneLineUpAtATime(unittest.TestCase):
 155 | +    """ORDER 17:50 ET Nov 16: the 21:10 reset build spends the fresh dollar on ONE line-up at a time (--only: this build
 156 | +    takes only the moments a candidate set names) and stops outside calls at $0.80 (--stop-usd; at most $1.25)."""
 157 | +
 158 | +    def pins(self):
 159 | +        return [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 160 | +                                                                                 "MOMENTS_PIN_LY.json")]
 161 | +
 162 | +    def test_a_bad_only_file_or_stop_refuses_the_run_before_anything_is_written(self):
 163 | +        sys.path.insert(0, HERE)
 164 | +        import proof_ledger as PLG
 165 | +        proof = os.path.join(HERE, "proof")
 166 | +        before = sorted(n for n in os.listdir(proof) if n.startswith("ledger_"))
 167 | +        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()), refused_only():
 168 | +            for name, body in (("empty.json", {"ids": [], "why": "w"}), ("nowhy.json", {"ids": ["a"]}),
 169 | +                               ("notlist.json", {"ids": "a", "why": "w"}), ("blank.json", {"ids": [""], "why": "w"})):
 170 | +                with open(os.path.join(d, name), "w") as f:
 171 | +                    json.dump(body, f)
 172 | +                self.assertEqual(PLG.main(["--delivered", *self.pins(), "--only", os.path.join(d, name)]), 2, name)
 173 | +            self.assertEqual(PLG.main(["--delivered", *self.pins(), "--only", os.path.join(d, "missing.json")]), 2)
 174 | +            for bad in ("0", "-1", "1.26", "2"):
 175 | +                self.assertEqual(PLG.main(["--delivered", *self.pins(), "--stop-usd", bad]), 2, bad)
 176 | +        self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_")), before)
 177 | +
 178 | +    def test_only_keeps_the_named_moments_in_the_pools_order_and_names_the_missing(self):
 179 | +        sys.path.insert(0, HERE)
 180 | +        import proof_ledger as PLG
 181 | +        with tempfile.TemporaryDirectory() as d:
 182 | +            p = os.path.join(d, "only.json")
 183 | +            with open(p, "w") as f:
 184 | +                json.dump({"ids": ["c", "a", "gone", "a"], "why": "story S-1"}, f)
 185 | +            only = PLG.read_only(p)
 186 | +            self.assertEqual((only["ids"], only["why"]), (["c", "a", "gone"], "story S-1"))
 187 | +            kept, rec = PLG.only_moments([{"moment_id": x} for x in ("a", "b", "c")], only)
 188 | +            self.assertEqual([m["moment_id"] for m in kept], ["a", "c"])
 189 | +            self.assertEqual((rec["asked"], rec["kept"], rec["missing"]), (3, 2, ["gone"]))
 190 | +
 191 | +    def test_the_stop_holds_the_start_and_the_router(self):
 192 | +        sys.path.insert(0, HERE)
 193 | +        import proof_ledger as PLG
 194 | +        self.assertIn("$0.80 stop", PLG.start_refused(0.80, 0.80))
 195 | +        self.assertIsNone(PLG.start_refused(0.79, 0.80))
 196 | +        self.assertIsNone(PLG.start_refused(0.99))                          # the day's own stop when none is given
 197 | +        self.assertIsNotNone(PLG.start_refused(PLG.PL.LY_STOP_USD))
 198 | +        self.assertEqual(PLG.build_router("heimdall_first", {}, os.devnull, limit=0.8).limit_usd, 0.8)
 199 | +        self.assertEqual(PLG.build_router("heimdall_first", {}, os.devnull).limit_usd, PLG.PL.LY_LIMIT_USD)
 200 | +
 201 | +
 202 |  if __name__ == "__main__":
 203 |      unittest.main()
 204 | 
```

---

pp-selectid: ORDER 17:50 ET Nov 16 (the 21:10 ET reset build), two options of the build DRIVER (tests/package/proof_ledger.py;
pipeline/package.py is not touched): --only FILE and --stop-usd X. Files: tests/package/proof_ledger.py,
tests/package/test_ledger_build.py.

THE ORDER, verbatim (3): "SPEND TONIGHT: spend the fresh dollar on ONE line-up at a time, the likeliest first; do not
screen the whole held pool (94 moments) at Grok: that alone would eat the dollar. Stop outside calls at $0.80 unless a
package is one call from its seal." (5): "If PBX answers before 21:10 I will send 'ADD 25 CENTS': then start at once with
the same plan and a day cap of $1.25." Ruling 122 (1)'s order of work inside the build (Grok only for the chosen line-up's
moments) is NOT built; these options give its effect from outside the build: each run takes one candidate set.

THE CHANGE:
- --only FILE: {"ids": [this build's moment ids, at least one, non-empty strings], "why": non-empty text}; read in the
  driver's refusal block (a bad or missing file: exit 2, nothing written); after the ledger build's inputs and BEFORE
  the trimmed variants (with_variants), the pool keeps only the named moments, in its own order; the record's
  inputs.only says file, why, asked, kept, missing, and the log says it. Every stage and gate of the build is unchanged:
  it simply sees a smaller pool (eligibility, step A, the second screen, the hook bar, the visual check, story-first,
  the writer, every verdict).
- --stop-usd X, 0 < X <= 1.25 (else exit 2 in the refusal block): this build's router limit (Router limit_usd: no paid
  call reserved past it) and its start stop (start_refused: no build starts at or over it); the record's
  spend_ruling_48 names cap, stop and order_17_50_stop. Without it: ruling 118's $1.00 as before.

TESTS (TestOrder1750OneLineUpAtATime): a bad or missing --only file, and --stop-usd 0, -1, 1.26, 2: exit 2 and no proof dir;
read_only (dedupe, why) and only_moments (pool order, missing named); start_refused with and without the stop;
build_router's limit with and without it. Mutations O1-O6 after a control run: the two pieces of main()'s wiring
(applying --only; giving the stop to the start check) are not reachable without a full driver run: the live build's log
line and record show them (said, not hidden).

PLEASE CHECK: (1) that --only cannot add a moment or skip a gate; (2) the stop's ceiling and its wiring; (3) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
