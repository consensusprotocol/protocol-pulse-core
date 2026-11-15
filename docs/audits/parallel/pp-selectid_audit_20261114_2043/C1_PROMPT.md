# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261114_2043
# Branch: pp-selectid
# Generated: 2026-11-14 20:44 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261114_2043/C1_STEP.diff (318 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index 336f0fe..0b91501 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -67,6 +67,8 @@ class ReplayMiss(Exception):
   6 |  
   7 |  
   8 |  IMAGE_TOKENS_UPPER = 6000            # ruling 70: one image's input tokens, as the spend guard's upper bound
   9 | +RATE_MIN_REPORTED = 3                # RULING 107 Q1 (orchestrator 20:40 ET Nov 14): an abandoned call is booked at
  10 | +                                     # the model's own reported rate once it has this many reported calls
  11 |  
  12 |  
  13 |  def is_vision(prompt):
  14 | @@ -901,8 +903,39 @@ class Router:
  15 |              self._save(d)
  16 |          return key
  17 |  
  18 | -    def _settle(self, key, backend=None, usage=None, usd=0.0, role=""):
  19 | -        """Release a reservation and account the call that answered (a free one too, when the ledger is readable)."""
  20 | +    def reported_rate(self, name):
  21 | +        """RULING 107 Q1 (orchestrator 20:40 ET Nov 14): the model's own recorded vendor cost per PROMPT token: its
  22 | +        vendor-reported dollars over the prompt tokens of the calls that carried a figure ("in_reported"; a ledger kept
  23 | +        before it counts every call's prompt tokens, "in"). None (list price applies) until the model has
  24 | +        RATE_MIN_REPORTED reported calls, or with no tokens, no ledger, or an unreadable one."""
  25 | +        if not self.spend_path:
  26 | +            return None
  27 | +        try:
  28 | +            with self._lock():
  29 | +                b = self._ledger()["by_backend"].get(name)
  30 | +        except SpendLimit:
  31 | +            return None
  32 | +        if not isinstance(b, dict) or not _num(b.get("usd_reported")):
  33 | +            return None
  34 | +        toks = b.get("in_reported", b.get("in"))
  35 | +        if int(b.get("reported_calls") or 0) < RATE_MIN_REPORTED or not _num(toks) or toks <= 0:
  36 | +            return None
  37 | +        return float(b["usd_reported"]) / float(toks)
  38 | +
  39 | +    def booking_usd(self, b, prompt, system=None):
  40 | +        """What a call abandoned at its deadline is booked at on the cap's basis (ruling 48's unreported estimate):
  41 | +        RULING 107 Q1, the model's own reported rate x the prompt sent (counted from above, prompt_tokens_upper: never
  42 | +        an under-count of the prompt); before RATE_MIN_REPORTED reported calls, list price (ruling 83 (a),
  43 | +        Backend.prompt_usd). -> (usd, "reported_rate" or "list")."""
  44 | +        rate = self.reported_rate(b.name)
  45 | +        if rate is None:
  46 | +            return b.prompt_usd(prompt, system), "list"
  47 | +        return round(rate * b.prompt_tokens_upper(prompt, system), 8), "reported_rate"
  48 | +
  49 | +    def _settle(self, key, backend=None, usage=None, usd=0.0, role="", unreported=None):
  50 | +        """Release a reservation and account the call that answered (a free one too, when the ledger is readable).
  51 | +        `unreported` (an abandoned call's booking, ruling 107 Q1) is what the cap's unreported estimate takes in place
  52 | +        of `usd`, which stays the list-price figure of usd_estimate."""
  53 |          if not self.spend_path or (key is None and backend is None):
  54 |              return
  55 |          with self._lock():
  56 | @@ -926,11 +959,14 @@ class Router:
  57 |                  d.update(calls=d["calls"] + 1, usd_estimate=round(d["usd_estimate"] + usd, 6))
  58 |                  if _num(usage.get("usd_reported")):    # the vendor's own figure (xAI ticks, Heimdall usage.cost)
  59 |                      rep = float(usage["usd_reported"])
  60 | -                    b.update(usd_reported=round(b.get("usd_reported", 0.0) + rep, 8),
  61 | -                             reported_calls=b.get("reported_calls", 0) + 1)
  62 | +                    n_in = int(usage.get("in", 0))     # ruling 107 Q1: the reported calls' prompt tokens (a ledger
  63 | +                    b.update(usd_reported=round(b.get("usd_reported", 0.0) + rep, 8),      # kept before it starts
  64 | +                             reported_calls=b.get("reported_calls", 0) + 1,                # from every earlier
  65 | +                             in_reported=b.get("in_reported", b["in"] - n_in) + n_in)      # call's)
  66 |                      d["usd_reported"] = round(d.get("usd_reported", 0.0) + rep, 8)
  67 |                  else:                                  # no vendor figure: the estimate stands for this call
  68 | -                    d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) + usd, 6)
  69 | +                    d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) +
  70 | +                                                         (usd if unreported is None else unreported), 6)
  71 |              self._save(d)
  72 |  
  73 |      def _late(self, ab, value, error):
  74 | @@ -939,9 +975,11 @@ class Router:
  75 |          with none, the estimate from its own token counts. No answer (an error): the booking stands. Either way one
  76 |          line goes to the deadline log (item 55). The answer's text is never used or recorded."""
  77 |          b, role, booked = ab["backend"], ab["role"], float(ab["usd"])
  78 | +        on_cap = float(ab.get("usd_unreported", booked))   # ruling 107 Q1: what the cap's basis was booked at
  79 |          rec = {"kind": "late_answer" if error is None else "late_error", "role": role, "model": b.name,
  80 |                 "vendor": b.vendor, "deadline_s": ab.get("deadline_s"),
  81 | -               "seconds": round(time.time() - ab["t0"] + float(ab.get("deadline_s") or 0), 2), "booked_usd": booked}
  82 | +               "seconds": round(time.time() - ab["t0"] + float(ab.get("deadline_s") or 0), 2), "booked_usd": on_cap,
  83 | +               "booked_basis": ab.get("basis", "list")}
  84 |          if error is None:
  85 |              try:
  86 |                  _text, usage, _secs = value
  87 | @@ -960,7 +998,7 @@ class Router:
  88 |                                    tokens=n_out, max_out=cap)
  89 |                  if self.spend_path:
  90 |                      try:
  91 | -                        self._replace_booking(b, role, booked, usage, usd, rep)
  92 | +                        self._replace_booking(b, role, booked, usage, usd, rep, on_cap)
  93 |                          rec["replaced"] = True
  94 |                      except Exception as e:             # noqa: BLE001 (audit 2048 C1: on record; the prompt-token
  95 |                          rec.update(replaced=False,     # booking stands, the ledger written whole or not at all)
  96 | @@ -969,7 +1007,7 @@ class Router:
  97 |              rec["error"] = f"{type(error).__name__}: {str(error)[:200]}"
  98 |          self._log_slow(rec)
  99 |  
 100 | -    def _replace_booking(self, b, role, booked, usage, usd, rep):
 101 | +    def _replace_booking(self, b, role, booked, usage, usd, rep, booked_unreported=None):
 102 |          """RULING 83 (a): a late answer's accounting in place of its prompt-token booking, in one ledger write: its
 103 |          own token counts, its estimate (usd) for the estimate basis, and on the reported basis the vendor's figure
 104 |          (rep) or, with none, the estimate. The call was counted when it was booked; it is not counted again."""
 105 | @@ -983,10 +1021,13 @@ class Router:
 106 |                        **{"in": bb["in"] + int(usage.get("in", 0)), "out": bb["out"] + int(usage.get("out", 0))})
 107 |              r["usd_estimate"] = round(r["usd_estimate"] + delta, 6)
 108 |              d["usd_estimate"] = round(d["usd_estimate"] + delta, 6)
 109 | -            d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) - booked, 6)
 110 | +            d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) -
 111 | +                                                 (booked if booked_unreported is None else booked_unreported), 6)
 112 |              if _num(rep):
 113 | +                n_in = int(usage.get("in", 0))         # ruling 107 Q1: as _settle counts them
 114 |                  bb.update(usd_reported=round(bb.get("usd_reported", 0.0) + float(rep), 8),
 115 | -                          reported_calls=bb.get("reported_calls", 0) + 1)
 116 | +                          reported_calls=bb.get("reported_calls", 0) + 1,
 117 | +                          in_reported=bb.get("in_reported", bb["in"] - n_in) + n_in)
 118 |                  d["usd_reported"] = round(d.get("usd_reported", 0.0) + float(rep), 8)
 119 |              else:
 120 |                  d["usd_unreported_estimate"] = round(d["usd_unreported_estimate"] + usd, 6)
 121 | @@ -1270,13 +1311,15 @@ class Router:
 122 |                              "THE LOCAL GEMMA3:27B ON GPU0 (THE INTEGRATOR'S JUDGE SERVICE): RULING 87'S LAST RESORT")
 123 |  
 124 |              def abandon(b=b, key=key, name=name, deadline_s=dl):   # RULING 83 (a): booked at its PROMPT tokens, an
 125 | -                booked = b.prompt_usd(prompt, system)  # unreported estimate, until a late answer's figure replaces it
 126 | +                listed = b.prompt_usd(prompt, system)  # unreported estimate, until a late answer's figure replaces it;
 127 | +                booked, basis = self.booking_usd(b, prompt, system)   # RULING 107 Q1: at the model's own reported rate
 128 |                  self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
 129 |                                  "deadline_s": deadline_s, "seconds": deadline_s,
 130 | -                                "prompt_chars": len(prompt_text(prompt)),
 131 | -                                "max_tokens": max_tokens, "booked_usd": booked})   # evidence first (audit 2048 C1)
 132 | -                self._settle(key, b, {"in": 0, "out": 0}, booked, role)          # an unreadable ledger raises here
 133 | -                return {"backend": b, "role": role, "usd": booked, "deadline_s": deadline_s, "t0": time.time(),
 134 | +                                "prompt_chars": len(prompt_text(prompt)), "max_tokens": max_tokens,
 135 | +                                "booked_usd": booked, "booked_basis": basis})   # evidence first (audit 2048 C1)
 136 | +                self._settle(key, b, {"in": 0, "out": 0}, listed, role, unreported=booked)   # an unreadable ledger
 137 | +                return {"backend": b, "role": role, "usd": listed, "usd_unreported": booked, "basis": basis,  # raises
 138 | +                        "deadline_s": deadline_s, "t0": time.time(),
 139 |                          "max_out": b.max_out(max_tokens)}             # ruling 99: a late runaway is measured on it
 140 |              try:
 141 |                  if dl:                                 # ruling 5 (22:40): fail over instead of waiting
 142 | @@ -1287,9 +1330,10 @@ class Router:
 143 |              except DeadlineExceeded as e:              # abandoned (the vendor may still bill it): booked and logged by
 144 |                  self._note(role, b, False)             # abandon(); ruling 87: not answered inside its deadline
 145 |                  self._breaker(role, name, "miss", deadline_s=dl, seconds=dl, max_out=b.max_out(max_tokens))
 146 | -                booked = b.prompt_usd(prompt, system)
 147 | -                tried.append((name, f"{e} (abandoned at the deadline; booked at its prompt tokens, ${booked:.4f}, "
 148 | -                                    "ruling 83 (a))"))
 149 | +                booked, basis = self.booking_usd(b, prompt, system)
 150 | +                tried.append((name, f"{e} (abandoned at the deadline; booked at its prompt tokens, ${booked:.4f} at "
 151 | +                                    f"{'its own reported rate' if basis == 'reported_rate' else 'list price'}, "
 152 | +                                    "rulings 83 (a) / 107)"))
 153 |                  continue
 154 |              except RequestRejected as e:
 155 |                  self._settle(key)
 156 | diff --git a/tests/providers/test_ruling_107.py b/tests/providers/test_ruling_107.py
 157 | new file mode 100644
 158 | index 0000000..91df191
 159 | --- /dev/null
 160 | +++ b/tests/providers/test_ruling_107.py
 161 | @@ -0,0 +1,156 @@
 162 | +#!/usr/bin/env python3
 163 | +"""RULING 107 Q1 (orchestrator 20:40 ET Nov 14): "An abandoned call is booked at the model's own reported rate (its
 164 | +recorded cost per prompt token x the prompt sent), not list price; if the model has no reported rate yet, list price
 165 | +until it has three. The $20 cap is on that basis from now." Offline: fake back-ends, a seeded ledger, the real Router."""
 166 | +import json
 167 | +import os
 168 | +import sys
 169 | +import tempfile
 170 | +import unittest
 171 | +
 172 | +HERE = os.path.dirname(os.path.abspath(__file__))
 173 | +REPO = os.path.dirname(os.path.dirname(HERE))
 174 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 175 | +sys.path.insert(0, HERE)
 176 | +import providers as P  # noqa: E402
 177 | +from test_providers import Fake, Slow, SlowFail, router, wait_for  # noqa: E402
 178 | +
 179 | +TOKENS = 201                       # prompt_tokens_upper("p"): 1 character + 200, counted from above (ruling 83 (a))
 180 | +LIST = TOKENS * 10 / 1e6           # Fake's list input price: $10 / 1M
 181 | +
 182 | +
 183 | +def seed(path, **deepseek):
 184 | +    """A ledger whose deepseek row is `deepseek` (calls / in / reported_calls / usd_reported / in_reported)."""
 185 | +    row = {"calls": 0, "in": 0, "out": 0, "usd_estimate": 0.0, "price_usd_per_1m": [10, 100]}
 186 | +    row.update(deepseek)
 187 | +    json.dump({"usd_estimate": 0.0, "calls": row["calls"], "by_backend": {"heimdall:deepseek": row}, "by_role": {},
 188 | +               "reserved": {}, "usd_reported": float(row.get("usd_reported", 0.0)),
 189 | +               "usd_unreported_estimate": 0.0}, open(path, "w"))
 190 | +
 191 | +
 192 | +def abandon_once(d, slow, **seeded):
 193 | +    """One call whose first leg (deepseek) passes its 0.2 s deadline; qwen answers with the vendor's own figure, so the
 194 | +    unreported estimate holds the abandoned call's booking alone. -> (reply, the ledger, the deadline log)."""
 195 | +    spend, log = os.path.join(d, "SPEND.json"), os.path.join(d, "DEADLINES.jsonl")
 196 | +    seed(spend, **seeded)
 197 | +    next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen",
 198 | +                 usage={"in": 1000, "out": 100, "usd_reported": 0.002})
 199 | +    r = router(d, [slow, next_], {"check": ["heimdall:deepseek", "heimdall:qwen"]}, spend_path=spend,
 200 | +               limit_usd=50.0, limit_basis="reported", deadline_log=log)
 201 | +    rep = r.call("check", "p", 100, 7, deadline_s=0.2)
 202 | +    with open(log) as f:
 203 | +        lines = [json.loads(x) for x in f]
 204 | +    return r, rep, json.load(open(spend)), lines
 205 | +
 206 | +
 207 | +class TestRuling107Booking(unittest.TestCase):
 208 | +
 209 | +    def test_an_abandoned_call_is_booked_at_the_models_own_reported_rate_once_it_has_three_reported_calls(self):
 210 | +        with tempfile.TemporaryDirectory() as d:
 211 | +            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
 212 | +            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
 213 | +                                            in_reported=3000)
 214 | +            want = 0.003 / 3000 * TOKENS                               # $1 / 1M prompt tokens, its own figure
 215 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], want, places=9)
 216 | +            self.assertLess(want, LIST / 5)                            # not list price
 217 | +            row = led["by_backend"]["heimdall:deepseek"]
 218 | +            self.assertEqual(row["calls"], 4)                          # counted once, as ruling 83 (a) counts it
 219 | +            self.assertAlmostEqual(row["usd_estimate"], LIST, places=9)    # usd_estimate stays the list-price figure
 220 | +            miss = [x for x in log if x["kind"] == "missed_deadline"]
 221 | +            self.assertEqual([(x["booked_basis"], round(x["booked_usd"], 9)) for x in miss],
 222 | +                             [("reported_rate", round(want, 9))])
 223 | +            self.assertIn("at its own reported rate", rep.tried[0][1])
 224 | +            self.assertAlmostEqual(r.spent(), 0.003 + 0.002 + want, places=9)   # the cap reads that booking
 225 | +
 226 | +    def test_list_price_until_the_model_has_three_reported_calls(self):
 227 | +        for n in (0, 1, 2):
 228 | +            with tempfile.TemporaryDirectory() as d:
 229 | +                slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
 230 | +                r, rep, led, log = abandon_once(d, slow, calls=n, **{"in": 1000 * n}, reported_calls=n,
 231 | +                                                usd_reported=0.001 * n, in_reported=1000 * n)
 232 | +                self.assertAlmostEqual(led["usd_unreported_estimate"], LIST, places=9, msg=f"{n} reported call(s)")
 233 | +                miss = [x for x in log if x["kind"] == "missed_deadline"]
 234 | +                self.assertEqual([x["booked_basis"] for x in miss], ["list"])
 235 | +                self.assertIn("at list price", rep.tried[0][1])
 236 | +
 237 | +    def test_the_rate_is_over_the_reported_calls_prompt_tokens_only(self):
 238 | +        with tempfile.TemporaryDirectory() as d:                   # 10,000 prompt tokens, 2,000 of them on calls
 239 | +            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")   # with a figure
 240 | +            r, rep, led, log = abandon_once(d, slow, calls=5, **{"in": 10000}, reported_calls=3, usd_reported=0.004,
 241 | +                                            in_reported=2000)
 242 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.004 / 2000 * TOKENS, places=9)
 243 | +
 244 | +    def test_no_prompt_tokens_on_record_is_list_price(self):
 245 | +        with tempfile.TemporaryDirectory() as d:
 246 | +            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
 247 | +            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 0}, reported_calls=3, usd_reported=0.003,
 248 | +                                            in_reported=0)
 249 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], LIST, places=9)
 250 | +
 251 | +    def test_a_ledger_kept_before_reads_every_calls_prompt_tokens_and_starts_counting_the_reported_ones(self):
 252 | +        with tempfile.TemporaryDirectory() as d:                   # no in_reported yet: "in" stands in for it
 253 | +            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
 254 | +            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.006)
 255 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.006 / 3000 * TOKENS, places=9)
 256 | +            self.assertEqual(led["by_backend"]["heimdall:qwen"]["in_reported"], 1000)   # a new row counts from 0
 257 | +        with tempfile.TemporaryDirectory() as d:                   # an answer with a figure on an older row:
 258 | +            spend = os.path.join(d, "SPEND.json")                  # in_reported starts from that row's "in"
 259 | +            seed(spend, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.006)
 260 | +            ans = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 1}', family="deepseek",
 261 | +                       usage={"in": 500, "out": 50, "usd_reported": 0.001})
 262 | +            router(d, [ans], {"check": ["heimdall:deepseek"]}, spend_path=spend, limit_usd=50.0,
 263 | +                   limit_basis="reported").call("check", "q", 100, 7)
 264 | +            row = json.load(open(spend))["by_backend"]["heimdall:deepseek"]
 265 | +            self.assertEqual((row["in"], row["in_reported"], row["reported_calls"]), (3500, 3500, 4))
 266 | +
 267 | +    def test_an_answer_without_a_figure_adds_no_reported_prompt_tokens(self):
 268 | +        with tempfile.TemporaryDirectory() as d:
 269 | +            spend = os.path.join(d, "SPEND.json")
 270 | +            seed(spend, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.006, in_reported=3000)
 271 | +            ans = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 1}', family="deepseek",
 272 | +                       usage={"in": 700, "out": 50})
 273 | +            router(d, [ans], {"check": ["heimdall:deepseek"]}, spend_path=spend, limit_usd=50.0,
 274 | +                   limit_basis="reported").call("check", "q", 100, 7)
 275 | +            row = json.load(open(spend))["by_backend"]["heimdall:deepseek"]
 276 | +            self.assertEqual((row["in"], row["in_reported"], row["reported_calls"]), (3700, 3000, 3))
 277 | +
 278 | +    def test_a_late_answer_replaces_exactly_the_booking_made_at_the_reported_rate(self):
 279 | +        with tempfile.TemporaryDirectory() as d:
 280 | +            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.6, family="deepseek",
 281 | +                        usage={"in": 1000, "out": 100, "usd_reported": 0.0123})
 282 | +            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
 283 | +                                            in_reported=3000)
 284 | +            booked = 0.003 / 3000 * TOKENS
 285 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], booked, places=9)
 286 | +            log = wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_answer")
 287 | +            late = [x for x in log if x["kind"] == "late_answer"]
 288 | +            self.assertEqual([(x["replaced"], x["booked_basis"], round(x["booked_usd"], 9)) for x in late],
 289 | +                             [(True, "reported_rate", round(booked, 9))])
 290 | +            led = json.load(open(os.path.join(d, "SPEND.json")))
 291 | +            row = led["by_backend"]["heimdall:deepseek"]
 292 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.0, places=9)   # that booking, exactly, gone
 293 | +            self.assertAlmostEqual(led["usd_reported"], 0.003 + 0.002 + 0.0123, places=9)
 294 | +            self.assertEqual((row["calls"], row["reported_calls"], row["in"], row["in_reported"]), (4, 4, 4000, 4000))
 295 | +            self.assertAlmostEqual(row["usd_estimate"], slow.usd({"in": 1000, "out": 100}), places=9)  # list figure
 296 | +
 297 | +    def test_a_late_answer_on_a_row_kept_before_starts_its_reported_prompt_tokens_from_that_rows_in(self):
 298 | +        with tempfile.TemporaryDirectory() as d:                   # no in_reported on the row: "in" stands in
 299 | +            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.6, family="deepseek",
 300 | +                        usage={"in": 1000, "out": 100, "usd_reported": 0.0123})
 301 | +            abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003)
 302 | +            wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_answer")
 303 | +            row = json.load(open(os.path.join(d, "SPEND.json")))["by_backend"]["heimdall:deepseek"]
 304 | +            self.assertEqual((row["in"], row["in_reported"], row["reported_calls"]), (4000, 4000, 4))
 305 | +
 306 | +    def test_a_late_error_leaves_the_reported_rate_booking_standing(self):
 307 | +        with tempfile.TemporaryDirectory() as d:
 308 | +            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
 309 | +            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
 310 | +                                            in_reported=3000)
 311 | +            log = wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_error")
 312 | +            led = json.load(open(os.path.join(d, "SPEND.json")))
 313 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.003 / 3000 * TOKENS, places=9)
 314 | +
 315 | +
 316 | +if __name__ == "__main__":
 317 | +    unittest.main()
 318 | 
```

---

pp-selectid, RULING 107 Q1 (the orchestrator, 20:40 ET Nov 14): "An abandoned call is booked at the model's own
reported rate (its recorded cost per prompt token x the prompt sent), not list price; if the model has no reported
rate yet, list price until it has three. The $20 cap is on that basis from now."

THE CHANGE (pipeline/providers.py; tests/providers/test_ruling_107.py is new):
- Router.reported_rate(name): the model's vendor-reported dollars over "in_reported", the prompt tokens of the calls
  that carried a vendor figure. A ledger row kept before this change has no in_reported and uses "in". The result is
  None (list price applies) until the model has RATE_MIN_REPORTED (3) reported calls, and also with no tokens, no
  ledger, or an unreadable ledger.
- Router.booking_usd(b, prompt, system): that rate x prompt_tokens_upper (the prompt counted from above, as ruling
  83 (a) already counts it), or list price (Backend.prompt_usd) when there is no rate. -> (usd, basis).
- The abandon closure in Router.call (ruling 83 (a)): the cap's unreported estimate takes the reported-rate booking.
  usd_estimate (the list-price figure, read by the estimate basis) keeps the list booking. The deadline-log line
  records booked_usd and booked_basis.
- _settle(..., unreported=None): an abandoned call's booking enters usd_unreported_estimate in place of usd. An answer
  that carries a vendor figure adds its prompt tokens to in_reported; an older row's count starts from its "in"
  (b["in"] - n_in, since "in" was updated a line above).
- _late / _replace_booking(..., booked_unreported=None): a late answer removes exactly the booking made on the cap's
  basis, and counts its prompt tokens in in_reported the same way.

UNCHANGED GUARDS (you see only the diff):
- _within (providers.py, "def _within(seconds, fn, on_abandon=None, on_late=None)") calls on_abandon in the CALLER's
  thread before it raises DeadlineExceeded. The late answer arrives later in the worker thread, through on_late.
- _lock is fcntl.flock on SPEND.json.lock, released when the returned file object closes (the "with" block).
- _ledger raises SpendLimit on an unreadable ledger.
- The "reported" spend basis is usd_reported + usd_unreported_estimate (_basis_total): this is the $20 cap's basis.

PLEASE CHECK:
(1) Is the rate exactly "recorded cost per prompt token", and used only from 3 reported calls on?
(2) Can the cap be under-booked by it? The rate is all-in (the reported dollars include output). The prompt is
    counted from above (characters + 200), never under.
(3) Locks and threads: reported_rate takes the ledger lock inside the abandon callback, and _settle takes it again
    right after. Is there any nesting or deadlock? Any race with the late-answer thread's _replace_booking?
(4) The in_reported carry-over on older rows: is b["in"] - n_in the right starting count, in both places?
(5) Do the other callers of _settle and _replace_booking still behave the same with the new optional parameters?
(6) The tests: 9 new, plus the 75 existing provider tests, all pass. 12 of 12 mutations are killed: the rate never
    used; 2 reported calls enough; the rate over every call's tokens; the cap taking the list booking; a late answer
    removing the list booking; the in_reported carry-over from 0 (in each of the two places); the prompt's size
    ignored; the late answer handed the list booking; the log recording the list booking; a zero-token row dividing;
    an answer without a figure counted as reported tokens.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
