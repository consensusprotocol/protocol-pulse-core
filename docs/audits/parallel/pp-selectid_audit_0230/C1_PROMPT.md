# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0230
# Branch: pp-selectid
# Generated: 2026-11-14 02:30 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0230/C1_STEP.diff (77 lines)
```
   1 | diff --git a/pipeline/heimdall_health.py b/pipeline/heimdall_health.py
   2 | index 510725f..c0b25a2 100644
   3 | --- a/pipeline/heimdall_health.py
   4 | +++ b/pipeline/heimdall_health.py
   5 | @@ -184,15 +184,23 @@ def mode(path=STATE, now=None, evidence=None, state_md=None, who=""):
   6 |          return s["mode"]
   7 |  
   8 |  
   9 | -def probe_due(path=STATE, now=None):
  10 | -    """True when a probe is due: calls are failing (or the mode is plan_b) and the last probe is PROBE_EVERY_S old."""
  11 | +def probe_due(path=STATE, now=None, who=""):
  12 | +    """True when a probe is due: calls are failing (or the mode is plan_b) and the last probe is PROBE_EVERY_S old.
  13 | +    A True CLAIMS the slot (last_probe_utc and last_probe_by stamped under the lock), so with several probers (this
  14 | +    builder's router, pp-ingest's watcher) there is ONE probe per PROBE_EVERY_S slot, and "BACK_AFTER answers in a
  15 | +    row" means that many slots (pp-ingest REQUESTS R12, 02:3x ET Nov 14). A claimer that never reports leaves the slot
  16 | +    spent: the next probe is due PROBE_EVERY_S later."""
  17 |      now = _now(now)
  18 |      with _Locked(path):
  19 |          s = _load(path)
  20 |          if s["mode"] != "plan_b" and not s.get("failing_since_utc"):
  21 |              return False
  22 |          lp = _t(s.get("last_probe_utc"))
  23 | -        return lp is None or (now - lp).total_seconds() >= PROBE_EVERY_S
  24 | +        if lp is not None and (now - lp).total_seconds() < PROBE_EVERY_S:
  25 | +            return False
  26 | +        s["last_probe_utc"], s["last_probe_by"] = _iso(now), who
  27 | +        _save(path, s)
  28 | +        return True
  29 |  
  30 |  
  31 |  def probe_result(answered, path=STATE, now=None, evidence=None, state_md=None, who=""):
  32 | diff --git a/pipeline/providers.py b/pipeline/providers.py
  33 | index aa5474b..1161323 100644
  34 | --- a/pipeline/providers.py
  35 | +++ b/pipeline/providers.py
  36 | @@ -1036,7 +1036,7 @@ class Router:
  37 |          def loop():
  38 |              while True:
  39 |                  try:
  40 | -                    if HH.probe_due(self.health):
  41 | +                    if HH.probe_due(self.health, who="pp-selectid probe"):     # claims the slot (one prober each)
  42 |                          HH.probe_result(self.probe_once(fams), self.health, evidence=self.deadline_log,
  43 |                                          state_md=self.state_md, who="pp-selectid probe")
  44 |                  except Exception:                      # noqa: BLE001 (the probe never stops a build)
  45 | diff --git a/tests/providers/test_heimdall_health.py b/tests/providers/test_heimdall_health.py
  46 | index e47a60c..8cfeff4 100644
  47 | --- a/tests/providers/test_heimdall_health.py
  48 | +++ b/tests/providers/test_heimdall_health.py
  49 | @@ -73,6 +73,27 @@ class TestHealth(unittest.TestCase):
  50 |          self.assertIn("BACK TO HEIMDALL-FIRST (THE PROBE ANSWERED 3 TIMES IN A ROW)",
  51 |                        open(self.md).read().split("\n")[0])
  52 |  
  53 | +    def test_two_probers_share_one_probe_per_slot(self):
  54 | +        """pp-ingest REQUESTS R12 (02:3x ET Nov 14): this router's probe and pp-ingest's watcher probe the same state;
  55 | +        a due probe is CLAIMED, so one slot gives one probe and 3 in a row is 3 slots."""
  56 | +        k = lambda m: self.kw(T0 + timedelta(minutes=m))
  57 | +        HH.note(False, **k(0))
  58 | +        HH.note(False, **k(15))                                          # down: plan_b
  59 | +        at = lambda m: T0 + timedelta(minutes=m)
  60 | +        self.assertEqual([HH.probe_due(self.state, at(16), who=w) for w in ("pp-selectid", "pp-ingest")],
  61 | +                         [True, False])                                  # the second prober finds the slot taken
  62 | +        self.assertEqual(json.load(open(self.state))["last_probe_by"], "pp-selectid")
  63 | +        HH.probe_result(True, **k(16))
  64 | +        self.assertEqual([HH.probe_due(self.state, at(17), who=w) for w in ("pp-selectid", "pp-ingest")],
  65 | +                         [False, False])
  66 | +        rounds = 1
  67 | +        for m in (18, 20):
  68 | +            claims = [HH.probe_due(self.state, at(m), who=w) for w in ("pp-ingest", "pp-selectid")]
  69 | +            self.assertEqual(claims, [True, False])
  70 | +            rounds += 1
  71 | +            mode = HH.probe_result(True, **k(m))
  72 | +        self.assertEqual((rounds, mode), (3, "heimdall_first"))         # three slots, three answers
  73 | +
  74 |      def test_a_drill_is_recorded_never_counted_and_answers_write_once_per_heartbeat(self):
  75 |          HH._SEEN.clear()
  76 |          for m in range(0, 40, 5):                                        # 40 minutes of drill failures
  77 | 
```

---

You are auditing a SMALL change on branch pp-selectid (Protocol Pulse). Only state what you can verify from the diff;
if uncertain, say so; do not guess. Be specific: file:line and a concrete input that breaks it.

Background (static): RULING 87 (Plan B): Heimdall is "down" after 15 minutes with no Heimdall family answering;
while calls fail or the mode is plan_b, a cheap health probe runs every 2 minutes (PROBE_EVERY_S); "Return to
Heimdall-first when its probe has answered 3 times in a row" (BACK_AFTER). pipeline/heimdall_health.py keeps the
state in one JSON file under an flock; TWO processes now probe it: this builder's Router probe thread and pp-ingest's
watcher (another repo, loading this module by path).

The defect (pp-ingest's REQUESTS R12): probe_due() only READ the slot, so both probers could probe in one 2-minute
slot. Then "3 in a row" could come from fewer than 3 slots, and one prober's failure reset the other's streak.

The change: probe_due(path, now, who="") CLAIMS the slot when it returns True: under the same lock, last_probe_utc =
now and last_probe_by = who are saved, so a second prober in the same slot gets False. probe_result (unchanged) still
stamps last_probe_utc when the probe ends. The router's probe thread passes who="pp-selectid probe". A test has two
probers share one slot and needs three slots for three answers in a row.

Check: that one slot yields exactly one True across callers (the read and the stamp are under one lock); that the
existing 15-minute rule and the 3-in-a-row return are unchanged; that a claimer that never reports cannot block
probing for more than one slot; that nothing else in the state changes. Answer with findings tagged <critical>,
<high>, <medium> (file:line, a concrete scenario), then "SHIP: yes / no / yes with conditions".

