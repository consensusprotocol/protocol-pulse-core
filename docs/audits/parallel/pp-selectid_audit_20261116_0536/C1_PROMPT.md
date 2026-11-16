# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_0536
# Branch: pp-selectid
# Generated: 2026-11-16 05:36 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_0536/C1_STEP.diff (314 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index 5e2c2cb..2e84551 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -732,7 +732,7 @@ class Router:
   6 |      def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
   7 |                   local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0,
   8 |                   routing=None, shadow=None, shadow_log=None, health=None, plan_b_chains=None, state_md=None,
   9 | -                 breakers=None, deadlines=None, reserve_wait_s=0.0):
  10 | +                 breakers=None, deadlines=None, reserve_wait_s=0.0, uncapped=()):
  11 |          with open(config) as f:
  12 |              self.config = json.load(f)
  13 |          rt = self.config.get("routing") or {}
  14 | @@ -744,6 +744,7 @@ class Router:
  15 |          if limit_basis not in ("estimate", "reported"):
  16 |              raise ValueError(f"limit_basis must be 'estimate' or 'reported', not {limit_basis!r}")
  17 |          self.limit_basis = limit_basis            # what limit_usd counts: _basis_total
  18 | +        self.uncapped = tuple(uncapped)           # RULING 118 (b): vendors recorded in the ledger but never capped
  19 |          self.reserve_wait_s = float(reserve_wait_s)   # _reserve: 0 (the default) refuses at once, as every caller had
  20 |          self.reserve_poll_s = RESERVE_POLL_S          # it; a batch build that may wait for calls in flight opts in
  21 |          import threading
  22 | @@ -878,6 +879,12 @@ class Router:
  23 |          except OSError as e:
  24 |              self.notices.append(f"the deadline log could not be written: {type(e).__name__}: {e}")
  25 |  
  26 | +    def _capped(self, name):
  27 | +        """RULING 118 (orchestrator 05:40 ET Nov 16): (a) the OUTSIDE vendors' dollars are capped; (b) Heimdall's are
  28 | +        free: a back-end of an `uncapped` vendor (the name's part before ':', as the ledger keys it) is recorded in the
  29 | +        ledger like any other, but never reserved and never counted toward limit_usd. No `uncapped`: every back-end."""
  30 | +        return name.split(":", 1)[0] not in self.uncapped
  31 | +
  32 |      def _basis_total(self, d):
  33 |          """The ledger total limit_usd is checked against. "estimate": the price-table estimate of every call (an upper
  34 |          bound). "reported" (ruling 48, orchestrator 2026-11-13 07:02): the vendors' own reported dollars, plus the
  35 | @@ -887,7 +894,14 @@ class Router:
  36 |              if d.get("calls", 0) and "usd_reported" not in d and "usd_unreported_estimate" not in d:
  37 |                  raise SpendLimit("the ledger has calls but keeps no vendor-reported figures: the reported basis "
  38 |                                   "cannot be read (fail closed; audit 0707 C1, glm P1-2)")
  39 | +            if self.uncapped:                    # RULING 118: the capped vendors' own figures; the unreported estimate
  40 | +                return sum(float(v.get("usd_reported", 0.0) or 0.0)     # keeps no vendor split, so all of it
  41 | +                           for k, v in (d.get("by_backend") or {}).items()     # counts (the stricter reading)
  42 | +                           if self._capped(k)) + float(d.get("usd_unreported_estimate", 0.0))
  43 |              return float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
  44 | +        if self.uncapped:
  45 | +            return sum(float(v.get("usd_estimate", 0.0) or 0.0)
  46 | +                       for k, v in (d.get("by_backend") or {}).items() if self._capped(k))
  47 |          return float(d["usd_estimate"])
  48 |  
  49 |      def spent(self):
  50 | @@ -911,7 +925,7 @@ class Router:
  51 |          65 moments at step A, medley and spotlight (90 holds in all), without this wait: six step-A workers, each
  52 |          reserving about $0.85, under a $4.50 limit with $0.27 spent; four fit, and the other workers were refused batch
  53 |          after batch while those four ran."""
  54 | -        if not self.spend_path or b.free():
  55 | +        if not self.spend_path or b.free() or not self._capped(b.name):     # ruling 118 (b): Heimdall is free
  56 |              return None
  57 |          t_end, waited = time.time() + max(0.0, float(self.reserve_wait_s)), False
  58 |          while True:
  59 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  60 | index 7f683f5..a5cae35 100644
  61 | --- a/tests/package/proof_ledger.py
  62 | +++ b/tests/package/proof_ledger.py
  63 | @@ -160,13 +160,16 @@ HOOK_SHADOW = {"coherence_verdict:hook": "heimdall:qwen/qwen3.8-27b"}   # RULING
  64 |  
  65 |  
  66 |  def build_shadow(routing, rt, streak):
  67 | -    """The build's shadow back-ends: RULING 86, Grok (routing.shadow) on the first heimdall_first pins, until
  68 | -    `shadow_until_clean_pins` clean pins in a row (`streak`: a callable, read only under heimdall_first); RULING 115,
  69 | -    qwen on every hook, in every build. Recorded, never deciding."""
  70 | +    """The build's shadow back-ends: RULING 86, routing.shadow on the first heimdall_first pins, until
  71 | +    `shadow_until_clean_pins` clean pins in a row (`streak`: a callable, read only under heimdall_first), but since
  72 | +    RULING 118 only its uncapped (Heimdall) entries: ruling 86's Grok shadow is dropped; RULING 115, qwen on every hook,
  73 | +    in every build. Recorded, never deciding."""
  74 |      shadow = None
  75 |      if routing == "heimdall_first" and streak() < int(rt.get("shadow_until_clean_pins") or 3):
  76 |          shadow = rt.get("shadow") or None
  77 | -    return dict(shadow or {}, **HOOK_SHADOW)
  78 | +    shadow = {k: v for k, v in (shadow or {}).items()          # RULING 118 (a): an outside vendor's dollars are kept for
  79 | +              if str(v).split(":", 1)[0] in PL.UNCAPPED}       # the seal: no outside shadow; a Heimdall one stays
  80 | +    return dict(shadow, **HOOK_SHADOW)
  81 |  
  82 |  
  83 |  def nothing_new(proof_dir, out_dir, fp):
  84 | @@ -224,7 +227,8 @@ def build_router(routing, shadow, shadow_log):
  85 |                      health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD,      # ruling 87
  86 |                      breakers=CB.STATE,                                                         # ruling 99
  87 |                      deadlines=DT.load(DT.STATE, PL.REPLIES),                                   # ruling 100
  88 | -                    reserve_wait_s=PL.RESERVE_WAIT_S)          # batch 3: a call that fits waits for calls in flight
  89 | +                    reserve_wait_s=PL.RESERVE_WAIT_S,          # batch 3: a call that fits waits for calls in flight
  90 | +                    uncapped=PL.UNCAPPED)                      # ruling 118 (b): Heimdall recorded, never capped
  91 |  
  92 |  
  93 |  def applied(router):
  94 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
  95 | index 138301d..90de567 100644
  96 | --- a/tests/package/proof_ly.py
  97 | +++ b/tests/package/proof_ly.py
  98 | @@ -32,6 +32,8 @@ import os
  99 |  import subprocess
 100 |  import sys
 101 |  import time
 102 | +from datetime import datetime, timedelta, timezone
 103 | +from zoneinfo import ZoneInfo
 104 |  
 105 |  HERE = os.path.dirname(os.path.abspath(__file__))
 106 |  REPO = os.path.dirname(os.path.dirname(HERE))
 107 | @@ -47,14 +49,31 @@ import speakers as SP  # noqa: E402
 108 |  
 109 |  REPLIES = os.path.join(HERE, "fixtures", "replies")
 110 |  OUT = os.path.join(HERE, "proof")
 111 | -SPEND = os.path.join(OUT, "SPEND_B4.json")   # BATCH 4 (orchestrator 19:40 ET Nov 15: 21:10 ET Nov 15 to 21:10 ET Nov
 112 | -#   16, batch 3's terms) keeps its own ledger, as batch 3 did (ruling 108). CLOSED: batch 3's SPEND_B3.json at 21:10 ET
 113 | -#   Nov 15; the $20 order's SPEND_LY.json at $11.47 (restated on ruling 107 Q1's basis, e7f68e11).
 114 | -LY_LIMIT_USD = 4.50                # RULING 108, batch 4 on its terms: builds + sealing's share of the $8.00 cap (audits $2.50,
 115 | -LY_LIMIT_BASIS = "reported"        # mining and checks $1.00), VENDOR-REPORTED; an abandoned call at the model's own
 116 | -LY_STOP_USD = 4.00                 # rate (ruling 107 Q1). No build starts at or over $4.00 (a build runs $0.15-0.50, so
 117 | -                                   # none ends over $4.50: each paid call still RESERVES its upper bound while in
 118 | -                                   # flight, and none passes the limit); STATE line 1 says so in capitals.
 119 | +DAY_ET = ZoneInfo("America/New_York")
 120 | +DAY_START = (21, 10)               # RULING 118: a day's dollar runs 21:10 ET to 21:10 ET (the batches' boundary; the
 121 | +FIRST_DAY = "SPEND_B4.json"        # ruling counts batch 4's $0.52 in Nov 16's dollar, so that day's ledger is batch 4's)
 122 | +
 123 | +
 124 | +def day_ledger(now=None):
 125 | +    """RULING 118 (orchestrator 05:40 ET Nov 16): the ledger of the day `now` falls in (default: this moment). A day
 126 | +    starts at DAY_START ET and is named by the date it starts on; the day that starts 21:10 ET Nov 15 is batch 4's,
 127 | +    whose ledger it keeps (FIRST_DAY). -> the ledger's path."""
 128 | +    t = (now or datetime.now(timezone.utc)).astimezone(DAY_ET)
 129 | +    start = t.replace(hour=DAY_START[0], minute=DAY_START[1], second=0, microsecond=0)
 130 | +    if t < start:
 131 | +        start -= timedelta(days=1)
 132 | +    return os.path.join(OUT, FIRST_DAY if start.strftime("%Y%m%d") == "20261115" else
 133 | +                        f"SPEND_D{start:%Y%m%d}.json")
 134 | +
 135 | +
 136 | +SPEND = day_ledger()               # RULING 118: today's ledger, read once when a build starts (a build charges the day
 137 | +#   it started in). CLOSED: batch 3's SPEND_B3.json at 21:10 ET Nov 15; the $20 order's SPEND_LY.json at $11.47.
 138 | +LY_LIMIT_USD = 1.00                # RULING 118 (a): the OUTSIDE vendors' HARD cap, $1.00 a day all-in (builds, audits,
 139 | +LY_LIMIT_BASIS = "reported"        # tests: the audits and tests are Heimdall-only, so the builds' outside dollars are
 140 | +LY_STOP_USD = 1.00                 # the day's), VENDOR-REPORTED, an abandoned call at the model's own rate (ruling 107
 141 | +#   Q1). Each paid call RESERVES its upper bound (Router._reserve), so none passes the cap. At the cap no build starts
 142 | +#   (the verdicts are outside calls until the free panel takes them; STATE line 1 says so in capitals).
 143 | +UNCAPPED = ("heimdall",)           # RULING 118 (b): Heimdall is free: recorded in the ledger, never reserved or capped
 144 |  RESERVE_WAIT_S = 600.0             # BATCH 3 (Nov 14): the ledger build's router waits up to this long for calls in
 145 |                                     # flight to settle before refusing a call that fits under the limit by itself
 146 |                                     # (Router reserve_wait_s): step A's six workers reserve about $0.85 each, so under
 147 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 148 | index 2a117a7..091079d 100644
 149 | --- a/tests/package/test_ledger_build.py
 150 | +++ b/tests/package/test_ledger_build.py
 151 | @@ -910,8 +910,12 @@ class TestRuling85NoXai(unittest.TestCase):
 152 |          X, Q = "xai:grok-4.20-0309-reasoning", "heimdall:qwen/qwen3.8-27b"
 153 |          rt = {"shadow": {"*": X}, "shadow_until_clean_pins": 3}
 154 |          hook = {"coherence_verdict:hook": Q}
 155 | -        self.assertEqual(PLG.build_shadow("heimdall_first", rt, lambda: 0), {"*": X, **hook})
 156 | +        self.assertEqual(PLG.build_shadow("heimdall_first", rt, lambda: 0), hook)   # RULING 118: no outside shadow
 157 |          self.assertEqual(PLG.build_shadow("heimdall_first", rt, lambda: 3), hook)
 158 | +        H = "heimdall:deepseek/deepseek-v4.1-flash"                     # a Heimdall shadow stays (it is free)
 159 | +        rt_h = {"shadow": {"*": X, "visual_check": "xai_vision:grok-4.7", "context_verdict": H},
 160 | +                "shadow_until_clean_pins": 3}
 161 | +        self.assertEqual(PLG.build_shadow("heimdall_first", rt_h, lambda: 0), {"context_verdict": H, **hook})
 162 |  
 163 |          def never():
 164 |              raise AssertionError("the streak is read under heimdall_first only")
 165 | @@ -919,7 +923,7 @@ class TestRuling85NoXai(unittest.TestCase):
 166 |          r = self.pl().P.Router(env_path="/nonexistent", routing="heimdall_first",
 167 |                                 shadow=PLG.build_shadow("heimdall_first", rt, lambda: 0))
 168 |          self.assertEqual((r._shadow_of("coherence_verdict", "hook"), r._shadow_of("coherence_verdict", "coherence")),
 169 | -                         (Q, X))                                       # the router reads them as ruled
 170 | +                         (Q, None))                                    # the router reads them as ruled
 171 |  
 172 |      def test_ruling_96s_lists_and_xai_answering_nothing(self):
 173 |          """RULING 96 (01:40 ET Nov 14), final until re-measured, on ruling 88's structure, as the orchestrator's 06:12
 174 | diff --git a/tests/package/test_ledger_router.py b/tests/package/test_ledger_router.py
 175 | index c7edae2..45b760c 100644
 176 | --- a/tests/package/test_ledger_router.py
 177 | +++ b/tests/package/test_ledger_router.py
 178 | @@ -25,6 +25,7 @@ import deadline_table as DT  # noqa: E402
 179 |  import heimdall_health as HH  # noqa: E402
 180 |  import proof_ledger as PLG  # noqa: E402
 181 |  import proof_ly as PL  # noqa: E402
 182 | +import providers as P  # noqa: E402
 183 |  from test_providers import Fake, SlowFail, router, wait_for  # noqa: E402
 184 |  from test_reserve_wait import U, gate, run, seed, until  # noqa: E402
 185 |  from test_ruling_107 import LIST, TOKENS, seed as seed107  # noqa: E402
 186 | @@ -71,6 +72,38 @@ class TestTheMeterNeverStandsBetweenACallAndItsBooking(unittest.TestCase):
 187 |              self.assertAlmostEqual(own["est"], LIST + QWEN_LIST, places=9)                   # est stays list price
 188 |  
 189 |  
 190 | +class TestRuling118TheBuildsRouterCapsOnlyOutsideVendors(unittest.TestCase):
 191 | +    """RULING 118 (05:40 ET Nov 16): the build's router caps the outside vendors at the day's $1.00 and records
 192 | +    Heimdall, never capping it: reaching the cap stops outside calls, not the free work."""
 193 | +
 194 | +    def test_heimdall_runs_past_the_cap_and_an_outside_call_is_refused_at_it(self):
 195 | +        with tempfile.TemporaryDirectory() as d:          # every file the build's router reads or writes is d's
 196 | +            led = os.path.join(d, "SPEND.json")
 197 | +            json.dump({"usd_estimate": 0.0, "calls": 2, "by_backend": {
 198 | +                "xai:g": {"calls": 1, "in": 0, "out": 0, "usd_estimate": 0.0, "usd_reported": 0.95},
 199 | +                "heimdall:q": {"calls": 1, "in": 0, "out": 0, "usd_estimate": 0.0, "usd_reported": 3.0}},
 200 | +                "by_role": {}, "reserved": {}, "usd_reported": 3.95, "usd_unreported_estimate": 0.0}, open(led, "w"))
 201 | +            with contextlib.ExitStack() as st:
 202 | +                for mod, name, val in ((PL, "SPEND", led), (PL, "REPLIES", os.path.join(d, "rec")),
 203 | +                                       (PL, "DEADLINE_LOG", os.path.join(d, "DL.jsonl")),
 204 | +                                       (HH, "STATE", os.path.join(d, "HEALTH.json")),
 205 | +                                       (CB, "STATE", os.path.join(d, "BREAKERS.json")),
 206 | +                                       (DT, "STATE", os.path.join(d, "DEADLINE_TABLE.json")),
 207 | +                                       (PLG, "STATE_MD", os.path.join(d, "STATE.md"))):
 208 | +                    st.enter_context(mock.patch.object(mod, name, val))
 209 | +                r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
 210 | +            h = Fake("heimdall:q", "heimdall", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.5})
 211 | +            x = Fake("xai:g", "xai", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.01})
 212 | +            r.backends, r.chains["check"], r.chains["judge"] = {"heimdall:q": h, "xai:g": x}, ["heimdall:q"], ["xai:g"]
 213 | +            self.assertAlmostEqual(r.spent(), 0.95, places=6)      # the day's outside dollars only
 214 | +            self.assertIsNone(PLG.start_refused(r.spent()))        # under the $1.00 stop: a build may start
 215 | +            self.assertEqual(r.call("check", "p" * 100_000).backend, "heimdall:q")   # its upper bound alone > $1.00
 216 | +            with self.assertRaises(P.SpendLimit):
 217 | +                r.call("judge", "p")                               # 0.95 + its upper bound > $1.00: refused at once
 218 | +            self.assertEqual((h.calls, x.calls), (1, 0))
 219 | +            self.assertAlmostEqual(json.load(open(led))["by_backend"]["heimdall:q"]["usd_reported"], 3.5, places=6)
 220 | +
 221 | +
 222 |  class TestTheLedgerBuildsRouterWaitsForCallsInFlight(unittest.TestCase):
 223 |  
 224 |      def test_a_call_kept_out_only_by_a_call_in_flight_waits_and_answers(self):
 225 | diff --git a/tests/package/test_ruling_102.py b/tests/package/test_ruling_102.py
 226 | index 0889c09..08e48db 100644
 227 | --- a/tests/package/test_ruling_102.py
 228 | +++ b/tests/package/test_ruling_102.py
 229 | @@ -305,18 +305,31 @@ class TestOnThePinAndOnState(unittest.TestCase):
 230 |          self.assertIn("THE LOCAL JUDGE (RULING 87'S LAST RESORT) GAVE 2 STEP-A VERDICT(S): ['c', 'e']", line)
 231 |  
 232 |      def test_no_build_starts_at_the_stop_and_one_starts_below(self):
 233 | -        """The orchestrator 13:02 Nov 14: at the stop no build starts, and STATE line 1 says so in capitals. RULING 108
 234 | -        (21:20 Nov 14): batch 3's builds stop at $4.00 of their $4.50 share; batch 4 (19:40 Nov 15) on the same terms."""
 235 | -        self.assertEqual((PLG.PL.LY_STOP_USD, PLG.PL.LY_LIMIT_USD), (4.00, 4.50))
 236 | +        """The orchestrator 13:02 Nov 14: at the stop no build starts, and STATE line 1 says so in capitals. RULING 118
 237 | +        (05:40 Nov 16): the outside vendors' HARD cap is $1.00 a day, Heimdall uncapped; each paid call reserves its
 238 | +        upper bound, so the cap itself is never passed (ruling 108's headroom between the stop and the limit is gone)."""
 239 | +        self.assertEqual((PLG.PL.LY_STOP_USD, PLG.PL.LY_LIMIT_USD), (1.00, 1.00))
 240 |          self.assertEqual(PLG.PL.LY_LIMIT_BASIS, "reported")               # vendor-reported (audit 2114 C1, glm)
 241 | -        self.assertGreaterEqual(PLG.PL.LY_LIMIT_USD - PLG.PL.LY_STOP_USD, 0.50)   # one build's headroom (C1, glm)
 242 | -        self.assertEqual(os.path.basename(PLG.PL.SPEND), "SPEND_B4.json")   # batch 4's own; never a closed ledger
 243 | -        self.assertNotIn(os.path.basename(PLG.PL.SPEND), ("SPEND_LY.json", "SPEND_B3.json"))
 244 | -        self.assertIsNone(PLG.start_refused(3.99))
 245 | -        why = PLG.start_refused(4.0)
 246 | -        self.assertIn("at or over the $4.00 stop: no build starts", why)
 247 | +        self.assertEqual(PLG.PL.UNCAPPED, ("heimdall",))
 248 | +        self.assertIsNone(PLG.start_refused(0.99))
 249 | +        why = PLG.start_refused(1.0)
 250 | +        self.assertIn("at or over the $1.00 stop: no build starts", why)
 251 |          self.assertIn("SAY IT ON STATE LINE 1 IN CAPITALS", why)
 252 |  
 253 | +    def test_ruling_118_each_day_keeps_its_own_ledger_from_21_10_et(self):
 254 | +        """RULING 118: $1.00 a day; a day runs 21:10 ET to 21:10 ET, and the one that starts 21:10 ET Nov 15 is batch 4's
 255 | +        (the ruling counts batch 4's $0.52 in it), so it keeps SPEND_B4.json; a build charges the day it started in."""
 256 | +        from datetime import datetime
 257 | +        from zoneinfo import ZoneInfo
 258 | +        et, dl = ZoneInfo("America/New_York"), PLG.PL.day_ledger
 259 | +        name = lambda *a: os.path.basename(dl(datetime(*a, tzinfo=et)))
 260 | +        self.assertEqual([name(2026, 11, 15, 21, 10), name(2026, 11, 16, 5, 40), name(2026, 11, 16, 21, 9)],
 261 | +                         ["SPEND_B4.json"] * 3)
 262 | +        self.assertEqual([name(2026, 11, 16, 21, 10), name(2026, 11, 17, 3, 0), name(2026, 11, 17, 21, 10)],
 263 | +                         ["SPEND_D20261116.json", "SPEND_D20261116.json", "SPEND_D20261117.json"])
 264 | +        self.assertEqual(PLG.PL.SPEND, dl())                               # the build's ledger is today's
 265 | +        self.assertNotIn(os.path.basename(PLG.PL.SPEND), ("SPEND_LY.json", "SPEND_B3.json"))   # never a closed one
 266 | +
 267 |  
 268 |  class TestTheConfirmAheadIsGrokOnly(unittest.TestCase):
 269 |      """RULING 101 beside 102: Grok's confirm-ahead never asks Gemini or the local judge (the second family's
 270 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
 271 | index d27acc2..8eef714 100644
 272 | --- a/tests/providers/test_providers.py
 273 | +++ b/tests/providers/test_providers.py
 274 | @@ -390,6 +390,39 @@ class TestRouter(unittest.TestCase):
 275 |              with self.assertRaises(P.SpendLimit):
 276 |                  r.spent()
 277 |  
 278 | +    def test_ruling_118_heimdall_is_recorded_but_never_capped(self):
 279 | +        """RULING 118 (05:40 ET Nov 16): the outside vendors' dollars are capped; Heimdall's are recorded in the same
 280 | +        ledger but never reserved and never counted toward the limit (uncapped=("heimdall",)); the unreported
 281 | +        estimate keeps no vendor split and counts whole; with no `uncapped` every back-end counts, as before."""
 282 | +        with tempfile.TemporaryDirectory() as d:
 283 | +            led = os.path.join(d, "SPEND.json")
 284 | +            json.dump({"usd_estimate": 6.0, "calls": 10, "by_backend": {
 285 | +                "heimdall:q": {"calls": 9, "in": 0, "out": 0, "usd_estimate": 5.0, "usd_reported": 4.0},
 286 | +                "xai:g": {"calls": 1, "in": 0, "out": 0, "usd_estimate": 1.0, "usd_reported": 0.9}},
 287 | +                "by_role": {}, "reserved": {}, "usd_reported": 4.9, "usd_unreported_estimate": 0.05}, open(led, "w"))
 288 | +            h = Fake("heimdall:q", "heimdall", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.5})
 289 | +            x = Fake("xai:g", "xai", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.01})
 290 | +            kw = dict(spend_path=led, limit_usd=1.0, limit_basis="reported")
 291 | +            r = router(d, [h, x], {"write": ["heimdall:q"], "judge": ["xai:g"]}, uncapped=("heimdall",), **kw)
 292 | +            self.assertAlmostEqual(r.spent(), 0.95, places=6)          # the outside figure plus the whole unreported
 293 | +            r.call("write", "p" * 400_000)                             # an upper bound over $4: neither reserved nor
 294 | +            led_ = json.load(open(led))                                # refused
 295 | +            self.assertAlmostEqual(led_["by_backend"]["heimdall:q"]["usd_reported"], 4.5, places=6)   # recorded
 296 | +            self.assertAlmostEqual(r.spent(), 0.95, places=6)                                        # never counted
 297 | +            with self.assertRaises(P.SpendLimit):
 298 | +                r.call("judge", "p")                                   # 0.95 + its upper bound ($0.20) > $1.00
 299 | +            self.assertEqual((h.calls, x.calls, json.load(open(led))["reserved"]), (1, 0, {}))
 300 | +            r.limit_usd = 1.20
 301 | +            r.call("judge", "p")                                       # it fits under a higher cap: counted
 302 | +            self.assertAlmostEqual(r.spent(), 0.96, places=6)
 303 | +            every = router(d, [h, x], {"write": ["heimdall:q"]}, **kw)          # no `uncapped`: all counted, as before
 304 | +            self.assertAlmostEqual(every.spent(), 4.9 + 0.5 + 0.01 + 0.05, places=6)
 305 | +            with self.assertRaises(P.SpendLimit):
 306 | +                every.call("write", "p")
 307 | +            est = router(d, [h, x], {"write": ["heimdall:q"]}, spend_path=led, limit_usd=1.0, uncapped=("heimdall",))
 308 | +            self.assertAlmostEqual(est.spent(), json.load(open(led))["by_backend"]["xai:g"]["usd_estimate"],
 309 | +                                   places=6)                           # the estimate basis: the capped vendors' own
 310 | +
 311 |      def test_the_spend_guard_reserves_the_upper_bound_and_never_passes_the_limit(self):
 312 |          with tempfile.TemporaryDirectory() as d:
 313 |              led = os.path.join(d, "SPEND.json")
 314 | 
```

---

pp-selectid: RULING 118 (orchestrator 05:40 ET Nov 16), THE DAY CAP: the guard before the free panel. Files:
pipeline/providers.py (Router: `uncapped`), tests/package/proof_ly.py (the $1.00 day cap, the day ledger, UNCAPPED),
tests/package/proof_ledger.py (the build's router; the shadow), and their tests.

THE ORDER, verbatim: "(a) OUTSIDE VENDORS (xAI, Gemini, any paid API): HARD CAP $1.00 A DAY all-in (builds, audits,
tests together; batch 4 has spent $0.52, so $0.48 is left today), and the target is UNDER $1.00 PER SEALED VIDEO.
Reaching the cap stops outside calls, not the work. (b) HEIMDALL AND THE TWO 4090s ARE FREE: use them for all they are
worth; capacity and politeness are the only limits." Audits from now: Heimdall seats only.

THE CHANGE:
- providers.Router(uncapped=()): a back-end whose name's vendor part (before ':', as the ledger keys it) is in
  `uncapped` is recorded in the ledger exactly as before, but _reserve takes NO reservation for it and _basis_total
  leaves its dollars OUT of the total limit_usd is checked against. Reported basis: the capped back-ends' usd_reported
  plus the WHOLE usd_unreported_estimate (it keeps no vendor split, so all of it counts: the stricter reading);
  estimate basis: the capped back-ends' usd_estimate. Default (): every back-end counts, as before, for every other
  caller of the Router.
- proof_ly: LY_LIMIT_USD = LY_STOP_USD = 1.00 (were 4.50 / 4.00); UNCAPPED = ("heimdall",); SPEND = day_ledger(): a
  day runs 21:10 ET to 21:10 ET and is named by its start date; the day that starts 21:10 ET Nov 15 keeps batch 4's
  SPEND_B4.json (the ruling counts batch 4's $0.52 in it). SPEND is read once when a build starts: a build charges the
  day it started in. Audits and tests are Heimdall-only from now, so the builds' outside dollars are the day's.
- proof_ledger.build_router passes uncapped=PL.UNCAPPED; build_shadow keeps only uncapped (Heimdall) shadow entries:
  ruling 86's Grok shadow ($0.25 of build 19's $0.46) is dropped; ruling 115's qwen hook shadow stays.

UNCHANGED GUARDS (not in the diff): _reserve's refusal, pipeline/providers.py (def _reserve): spent + reserved + this
call's upper bound > limit_usd raises SpendLimit, at once when spend alone is over; _basis_total's first lines: a ledger
with calls and no reported figures raises SpendLimit (fail closed); proof_ledger.start_refused (no build starts at or
over LY_STOP_USD); every capped paid call reserves its price-table upper bound while in flight.

TESTS: test_providers test_ruling_118_heimdall_is_recorded_but_never_capped (reported and estimate bases; a $4 Heimdall
call neither reserved nor refused, recorded; an outside call refused at the cap; no `uncapped`: all counted);
test_ledger_router TestRuling118TheBuildsRouterCapsOnlyOutsideVendors (through the build's own router, every state file
in a temp folder: a Heimdall call whose upper bound alone passes $1.00 runs, an outside call at $0.95 spent is refused);
test_ruling_102 (the $1.00 stop; the day ledger at the 21:10 boundary, today's = SPEND_B4.json); test_ledger_build
(the Grok shadow dropped, a Heimdall shadow kept). Mutations G1-G9 after a control run. All suite files pass.

PLEASE CHECK: (1) that an outside call can never pass the day's $1.00; (2) that a Heimdall call is never refused by
the cap and is still recorded; (3) that every other Router caller is unchanged; (4) the day ledger's boundary and the
first day's file; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
