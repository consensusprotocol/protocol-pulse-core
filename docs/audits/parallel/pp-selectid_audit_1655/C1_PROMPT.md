# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1655
# Branch: pp-selectid
# Generated: 2026-11-13 16:49 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1655/C1_STEP.diff (254 lines)
```
   1 | diff --git a/pipeline/candidates.py b/pipeline/candidates.py
   2 | index d89ed67..ea38cca 100644
   3 | --- a/pipeline/candidates.py
   4 | +++ b/pipeline/candidates.py
   5 | @@ -88,6 +88,22 @@ def seed(reg, record, source):
   6 |      return added
   7 |  
   8 |  
   9 | +def registered(reg):
  10 | +    """The line-ups the registry holds, whatever their state, for the search to leave alone (the 16:30 Nov 13 build's
  11 | +    search re-formed the resting candidate and re-wrote it: free from its recordings, but a try inside its 6 h all the
  12 | +    same). The registry tries a candidate: open first; resting, once after its 6 h with fresh writes; closed, never.
  13 | +    -> {tuple(line-up): {"key", "state", "until", "source", "index"}}. Raises ValueError on a malformed line-up (the
  14 | +    driver reads it before it writes anything)."""
  15 | +    out = {}
  16 | +    for k, e in reg["candidates"].items():
  17 | +        lu = e.get("lineup")
  18 | +        if not isinstance(lu, list) or not lu or not all(isinstance(x, str) and x for x in lu) or key(lu) != k:
  19 | +            raise ValueError(f"the candidate {k!r} holds no line-up of moment ids matching its key ({lu!r})")
  20 | +        out[tuple(lu)] = {"key": k, "state": e["state"], "until": e.get("until"), "source": e["source"],
  21 | +                          "index": e["index"]}
  22 | +    return out
  23 | +
  24 | +
  25 |  def due(reg, now):
  26 |      """The candidates to try now, newest first (by the time their line-up passed): every open one (its recorded
  27 |      verdicts and writes, free), and every resting one whose 6 h are over (fresh writes). -> [(key, entry, fresh)]."""
  28 | diff --git a/pipeline/package.py b/pipeline/package.py
  29 | index dc2f3fc..24992fa 100644
  30 | --- a/pipeline/package.py
  31 | +++ b/pipeline/package.py
  32 | @@ -2033,7 +2033,7 @@ def candidate_lineup(router, candidate, cleared, now):
  33 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
  34 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
  35 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
  36 | -          visual_cache=None):
  37 | +          visual_cache=None, registered=None):
  38 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  39 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
  40 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
  41 | @@ -2060,6 +2060,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  42 |      out["candidate"]["class"]: "package", "clip" (closed for good), "line" (its clips passed, a line failed) or
  43 |      "budget". candidate["write_seed"] (ruling 66 at 14:02: a candidate's one more try "with fresh writes") is added to
  44 |      every write's seed, so no recorded write is served again; 0 (the default) keeps the recorded ones.
  45 | +    registered (candidates.registered): every line-up the registry holds, by its moment ids in order. The search never
  46 | +    re-forms one: the registry tries it (open first; resting once after its 6 h, with fresh writes; closed never). A
  47 | +    line-up the search forms that is registered is recorded ("registered") and neither judged nor written, and the angle
  48 | +    ends there, as it ends after a passing line-up whose line fails. A build from a candidate ignores it.
  49 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
  50 |      t0 = time.time()
  51 |      usd0 = _spent(spend)
  52 | @@ -2473,6 +2477,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  53 |                  if segs is None:
  54 |                      rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
  55 |                      break
  56 | +                held = (registered or {}).get(tuple(m["moment_id"] for m in segs)) if candidate is None else None
  57 | +                if held is not None:                      # RULING 66 (14:02): the registry's line-up, never the search's
  58 | +                    rec["registered"] = dict(held)
  59 | +                    rec["why"] = (f"ruling 66: a registered candidate ({held.get('state')}" +
  60 | +                                  (f" until {held['until']}" if held.get("until") else "") +
  61 | +                                  f"; {held.get('source')} tried[{held.get('index')}]): the registry tries it, the "
  62 | +                                  f"search never re-forms it; not judged, nothing written: next angle")
  63 | +                    log(f"  angle {ai + 1}: {rec['why']} ({time.time() - t0:.0f} s)")
  64 | +                    break
  65 |                  n_lineup += 1
  66 |                  spins += 1
  67 |                  if spins > 4 * lineups:                   # a guard: free (cached) line-ups never turn forever
  68 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  69 | index 63f93ab..02585be 100644
  70 | --- a/tests/package/proof_ledger.py
  71 | +++ b/tests/package/proof_ledger.py
  72 | @@ -125,6 +125,7 @@ def main(argv=None):
  73 |              with open(p) as f:
  74 |                  CA.seed(reg, json.load(f), os.path.relpath(os.path.dirname(p), REPO))
  75 |          CA.due(reg, now)                                 # every stored time reads (audit 1420 C1), or exit 2
  76 | +        CA.registered(reg)                               # and every line-up (the search leaves them alone), or exit 2
  77 |      except (OSError, ValueError, KeyError, TypeError) as e:
  78 |          print(f"REFUSED: the delivered pins, 'since', the candidate or the candidate registry cannot be read "
  79 |                f"({type(e).__name__}: {e})", file=sys.stderr)
  80 | @@ -207,8 +208,8 @@ def main(argv=None):
  81 |          say(f"  RULING 66: {len(tries)} candidate(s) tried: " + "; ".join(
  82 |              f"{t['source']}[{t['index']}] {t['class']} -> {t['state']}" for t in tries) if tries else
  83 |              "  RULING 66: no candidate is due")
  84 | -        if res is None and left > 0:
  85 | -            res = PK.build(router, moments, sources, ctx, lineups=left, **kw)
  86 | +        if res is None and left > 0:                     # the search never re-forms a registered line-up
  87 | +            res = PK.build(router, moments, sources, ctx, lineups=left, registered=CA.registered(reg), **kw)
  88 |          elif res is None:                                # every judged line-up went to candidates: no angle asked
  89 |              res = dict(last.get("out") or {"usable": None, "prescreen": {}, "tried": []}, package=None, packages=[],
  90 |                         why_none="ruling 66: the 8 judged line-ups were spent on candidates; no angle asked")
  91 | diff --git a/tests/package/test_candidates.py b/tests/package/test_candidates.py
  92 | index 14bcc8b..7c06985 100644
  93 | --- a/tests/package/test_candidates.py
  94 | +++ b/tests/package/test_candidates.py
  95 | @@ -100,6 +100,23 @@ class TestRegistry(unittest.TestCase):
  96 |          with self.assertRaises(ValueError):
  97 |              CA.due(reg, T0)
  98 |  
  99 | +    def test_registered_is_every_line_up_whatever_its_state(self):
 100 | +        """The search leaves every registered line-up to the registry (the 16:30 Nov 13 gap)."""
 101 | +        reg = CA.new_registry()
 102 | +        CA.seed(reg, record(T0, [t(["a", "b", "c"]), t(["d", "e", "f"]), t(["g", "h", "i"])]), "r")
 103 | +        CA.outcome(reg["candidates"]["d+e+f"], "line", T0.isoformat(), "b")
 104 | +        CA.outcome(reg["candidates"]["g+h+i"], "clip", T0.isoformat(), "b")
 105 | +        got = CA.registered(reg)
 106 | +        self.assertEqual({k: v["state"] for k, v in got.items()},
 107 | +                         {("a", "b", "c"): "open", ("d", "e", "f"): "resting", ("g", "h", "i"): "closed"})
 108 | +        self.assertEqual((got[("d", "e", "f")]["until"], got[("d", "e", "f")]["key"], got[("d", "e", "f")]["index"]),
 109 | +                         ((T0 + timedelta(hours=6)).isoformat(), "d+e+f", 1))
 110 | +        self.assertEqual(CA.registered(CA.new_registry()), {})
 111 | +        for bad in (["a", "b"], None, "abc", ["a", "", "c"], ["a", 2, "c"]):          # not a line-up matching its key
 112 | +            reg["candidates"]["a+b+c"]["lineup"] = bad
 113 | +            with self.assertRaises(ValueError):
 114 | +                CA.registered(reg)
 115 | +
 116 |      def test_run_due_stops_at_a_package_inside_the_judged_line_ups(self):
 117 |          reg = CA.new_registry()
 118 |          for h, lu in enumerate((["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"])):
 119 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 120 | index 076c82d..74817cb 100644
 121 | --- a/tests/package/test_ledger_build.py
 122 | +++ b/tests/package/test_ledger_build.py
 123 | @@ -4,6 +4,7 @@
 124 |  - reading the store's word record (its sha checked, sentence-ready only);
 125 |  - turning rows into the packager's moments (counted drops, no duplicate spans);
 126 |  - the adapter's failures are raised, never read as an empty ledger."""
 127 | +import contextlib
 128 |  import hashlib
 129 |  import io
 130 |  import json
 131 | @@ -27,6 +28,16 @@ SENTS = ["Bitcoin is a global free market.", "Nobody can stop Bitcoin from settl
 132 |           "In 2009 Bitcoin started as a quiet experiment."]
 133 |  
 134 |  
 135 | +@contextlib.contextmanager
 136 | +def refused_only():
 137 | +    """A refusal test's guard: a driver run that gets past its refusal block fails here, before it can write a proof
 138 | +    dir or reach the network (16:45 Nov 13: a mutation check of a refusal test ran the driver on, in a scratch copy;
 139 | +    it spent nothing, but only because that copy lacked a directory)."""
 140 | +    with mock.patch("urllib.request.urlopen", side_effect=AssertionError("a refused run reached the network")), \
 141 | +            mock.patch("os.makedirs", side_effect=AssertionError("a refused run went on to write a proof dir")):
 142 | +        yield
 143 | +
 144 | +
 145 |  def row(text, start=None, end=None, mid="L1", vid="vidA"):
 146 |      return {"moment_id": mid, "video_id": vid, "channel_id": "UCdd", "channel_name": "DataDash", "text": text,
 147 |              "start": start, "end": end, "published_at": NOW.isoformat(), "title": "t",
 148 | @@ -691,7 +702,7 @@ class TestDriverRefuses(unittest.TestCase):
 149 |          self.assertEqual(len(spans), sum(i["clips"] for i in info))
 150 |          proof = os.path.join(HERE, "proof")
 151 |          before = sorted(n for n in os.listdir(proof) if n.startswith("ledger_"))
 152 | -        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()):
 153 | +        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()), refused_only():
 154 |              with open(pins[1]) as f:
 155 |                  pin = json.load(f)
 156 |              for name, bad in (("naive.json", dict(pin, approved_at="2026-11-13T03:01:09")),
 157 | @@ -723,7 +734,7 @@ class TestDriverRefuses(unittest.TestCase):
 158 |                                                                                   "MOMENTS_PIN_LY.json")]
 159 |          proof = os.path.join(HERE, "proof")
 160 |          before = sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json")
 161 | -        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()) as err:
 162 | +        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()) as err, refused_only():
 163 |              reg = os.path.join(d, "CANDIDATES.json")
 164 |              with open(reg, "w") as f:
 165 |                  json.dump({"records": [], "candidates": {"x+y+z": {
 166 | @@ -736,6 +747,18 @@ class TestDriverRefuses(unittest.TestCase):
 167 |              self.assertIn("registry", err.getvalue())
 168 |              with open(reg) as f:
 169 |                  self.assertEqual(f.read(), was)                                     # never rewritten
 170 | +            for bad in (None, ["x", "y"]):                      # a line-up the search could not leave alone
 171 | +                with open(reg, "w") as f:
 172 | +                    json.dump({"records": [], "candidates": {"x+y+z": {
 173 | +                        "lineup": bad, "source": "r", "index": 0, "found_at": "2026-11-13T19:00:00+00:00",
 174 | +                        "state": "open", "until": None, "fresh_used": False, "history": []}}}, f)
 175 | +                with open(reg) as f:
 176 | +                    was = f.read()
 177 | +                with mock.patch.object(PLG, "REGISTRY", reg):
 178 | +                    self.assertEqual(PLG.main(["--delivered", *pins]), 2, bad)
 179 | +                self.assertIn("matching its key", err.getvalue())
 180 | +                with open(reg) as f:
 181 | +                    self.assertEqual(f.read(), was)
 182 |          self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json"),
 183 |                           before)
 184 |  
 185 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 186 | index dea7ca8..7eb3ed2 100644
 187 | --- a/tests/package/test_medley.py
 188 | +++ b/tests/package/test_medley.py
 189 | @@ -523,7 +523,7 @@ class Rig:
 190 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 191 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 192 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 193 | -                 cached=False, candidate=None, visuals=None):
 194 | +                 cached=False, candidate=None, visuals=None, registered=None):
 195 |          import providers as P
 196 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 197 |          self.takeaways, self.spend = list(takeaways or []), spend
 198 | @@ -533,6 +533,7 @@ class Rig:
 199 |          self.hooks, self.hook_err, self.hook_calls = dict(hooks or {}), hook_err, []   # ruling 59 (a): {id: (s, a, u)}
 200 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 201 |          self.candidate, self.seeds = candidate, []          # ruling 66: build from a candidate; the seeds asked with
 202 | +        self.registered = registered                        # ruling 66: the registry's line-ups (candidates.registered)
 203 |          self.visuals, self.visual_calls = dict(visuals or {}), []   # ruling 70: {moment id: record} (default: clean)
 204 |          self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 205 |          self.screens, self.events, self.a_seen = [], [], []
 206 | @@ -663,6 +664,8 @@ class Rig:
 207 |                                                               "replayed": False}),
 208 |          }
 209 |          kw, path = ({"candidate": self.candidate} if self.candidate is not None else {}), None
 210 | +        if self.registered is not None:
 211 | +            kw["registered"] = self.registered
 212 |          if self.verdicts is not None:                      # ruling 56: the integrator's file, read by the real reader
 213 |              import tempfile
 214 |              fd, path = tempfile.mkstemp(suffix=".json")
 215 | @@ -1773,6 +1776,38 @@ class TestRuling66Candidate(unittest.TestCase):
 216 |          self.assertEqual(rig.seeds, [("medley", 8), ("write", 1108), ("write", 1109)])   # fresh writes, the verdict
 217 |                                                                                            # still its recorded seed
 218 |  
 219 | +    def test_the_search_never_re_forms_a_registered_line_up(self):
 220 | +        """RULING 66 (14:02; the 16:30 Nov 13 build's search re-formed the resting candidate and re-wrote it from its
 221 | +        recordings): a line-up the registry holds is neither judged nor written by the search, first formed or swapped
 222 | +        in, and the angle ends there; a build from the candidate itself still tries it."""
 223 | +        two = [["h", "x", "y", "z"], ["x", "h", "y", "z"]]
 224 | +        held = lambda lu, st, until=None: {tuple(lu): {"key": "+".join(lu), "state": st, "until": until,
 225 | +                                                       "source": "proof/ledger_x", "index": 0}}
 226 | +        rig = Rig(self.MS, two, [(True, [], None, Rig.LINE)], [None],
 227 | +                  registered=held(["h", "x", "y"], "resting", "2026-11-14T03:29:49+00:00"))
 228 | +        out = rig.run()
 229 | +        self.assertIsNotNone(out["package"])
 230 | +        self.assertEqual(out["tried"][0]["lineup"], ["h", "x", "y"])           # formed, then left alone
 231 | +        self.assertEqual(out["tried"][0]["registered"]["state"], "resting")
 232 | +        self.assertTrue(out["tried"][0]["why"].startswith("ruling 66: a registered candidate (resting until "
 233 | +                                                          "2026-11-14T03:29:49+00:00; proof/ledger_x tried[0])"))
 234 | +        self.assertNotIn("medley_ok", out["tried"][0])                          # never a new candidate (CA.seed)
 235 | +        self.assertEqual([c[0] for c in rig.medley_calls], ["x"])                # only angle 2's line-up is judged
 236 | +        self.assertEqual([w[0][0] for w in rig.write_calls], ["x"])              # and written
 237 | +        self.assertEqual(out["search"]["lineups"], 1)                           # the skip is no judged line-up
 238 | +        rig = Rig(self.MS, two, [(False, [], {"clip_02": 2}, Rig.LINE), (True, [], None, Rig.LINE)], [None],
 239 | +                  registered=held(["h", "x", "z"], "closed"))
 240 | +        out = rig.run()                                                          # a swap that forms it: the same
 241 | +        self.assertEqual(rig.medley_calls[0], ["h", "x", "y"])
 242 | +        self.assertEqual((out["tried"][1]["lineup"], out["tried"][1]["registered"]["state"]),
 243 | +                         (["h", "x", "z"], "closed"))
 244 | +        self.assertEqual([c[0] for c in rig.medley_calls[1:]], ["x"])
 245 | +        self.assertIsNotNone(out["package"])
 246 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 247 | +                  candidate=PK.load_candidate(self.record()), registered=held(["h", "x", "y"], "resting"))
 248 | +        out = rig.run()                                                          # its own try: never skipped
 249 | +        self.assertEqual((rig.medley_calls, out["candidate"]["class"]), ([["h", "x", "y"]], "package"))
 250 | +
 251 |      def test_exactly_its_clips_never_a_subset(self):
 252 |          ms = [pm("h", "A", 13.0), pm("x", "B", 13.0), pm("y", "C", 13.0), pm("z", "D", 11.0)]
 253 |          rec = self.record(tried=[{"angle": 1, "text": self.TEXT, "lineup": ["h", "x", "y", "z"],
 254 | 
```

---

You are auditing a SMALL search fix on branch pp-selectid (Protocol Pulse: the builder of sealed medley pins).
Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- package.build searches for a medley: per angle, a line-up (a hook + 2-4 clips, by moment id, in order) is judged
  on the clips alone (one model verdict); only a line-up that passes gets writes (the takeaway / title / caption),
  then paid gates. Line-ups judged in a build are capped at 8 (a recorded verdict is free and not counted).
- When a passing line-up's writes fail (its LINE fails) and no clip was dropped, the angle ends:
  `if out["packages"] or not relined: break` (next angle).
- RULING 66 (orchestrator 13:18 + 14:02 Nov 13): a line-up that passed the clips-alone verdict is a CANDIDATE, kept in
  a registry (pipeline/candidates.py; the driver tests/package/proof_ledger.py reads and writes it). Every build
  first tries the due candidates (run_due): open ones with their recorded calls; a candidate whose clips pass but whose
  LINE fails again is "CLOSED for 6 hours, then may be tried once more with fresh writes"; it is closed for good when
  a clip is delivered, ages out or fails a gate (or its fresh try fails too). States: open / resting / closed.

The defect (found in the 16:30 ET build's record, ledger_20261113_212949):
- The registry tried the candidate H+A+B; its line failed again, so it became "resting" until 22:29 ET.
- The normal search that followed in the same build re-formed H+A+B (angle 1, its 6th line-up, through the same
  swaps as before) and wrote it again. Every call was served from its recordings (free), but it was a try inside the
  6 h all the same, and with other seeds it could have been a paid verdict and paid writes.

The fix:
1. candidates.registered(reg) -> {tuple(line-up): {key, state, until, source, index}} for EVERY registered line-up,
   whatever its state. It raises ValueError on an entry whose line-up is not a non-empty list of non-empty strings
   matching its key.
2. package.build(registered=...): after a line-up is formed (first formed, swapped, reordered or pool-filled: all pass
   through the same point at the top of the loop) and before any verdict, a registered line-up is recorded in
   out["tried"] (rec["registered"], rec["why"] "ruling 66: a registered candidate (...): ... next angle"), neither
   judged nor written, and the angle ends (break), as it ends after a passing line-up whose line fails. It is not a
   judged line-up. A build FROM a candidate (candidate is not None) ignores registered.
3. The driver: CA.registered(reg) is evaluated in the refusal block (a malformed entry: exit 2, nothing written), and
   the normal search after run_due gets registered=CA.registered(reg) (the states after this build's candidate tries).
4. Decided, not an oversight (challenge it if you disagree): the key is the clips AND their order, as ruling 66 defines
   a candidate ("clips, order, verdict, ..."); the same clips in another order are another line-up and may be judged.
   Every registered line-up is skipped, open ones included: in practice an open one reaches the search only when its
   own try ended on a budget, and the registry tries it again next build.
5. Tests: test_candidates (registered: every state; malformed entries raise), test_medley (the search skips a
   registered line-up first formed and one formed by a swap; a candidate build still tries its own), test_ledger_build
   (malformed entries refuse the run). Hardening: both driver refusal tests now run under refused_only(), which makes
   urllib.request.urlopen and os.makedirs raise, so a run that slips past the refusal block fails the test before it
   can write a proof dir or reach the network. (A mutation check of the refusal test, with the new check removed, had
   run the driver on in a scratch copy; replayed with the network blocked, it made 0 HTTP calls, but only because
   that copy lacked a directory.)

Check, against the diff only:
- that a registered line-up can never be judged or written by the search, on any path that forms a line-up;
- that the skip never counts as a judged line-up and cannot loop;
- that nothing here changes what any gate, verdict or the seal accepts (law: never change what a check accepts to
  make something pass);
- that the candidate's own try is never skipped;
- that the refusal guard cannot leak into other tests (os.makedirs / urlopen patched only inside its with-block).

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

