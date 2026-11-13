# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0816
# Branch: pp-selectid
# Generated: 2026-11-13 08:16 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0816/C1_STEP.diff (184 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 5b7a168..cc901e5 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -711,6 +711,81 @@ def trim_variant(m, sources):
   6 |      return v
   7 |  
   8 |  
   9 | +REPOST_ALIGN_MIN = 0.80          # ruling 53: the share of the shorter moment's words that align in order
  10 | +
  11 | +
  12 | +def reposted_once(ms):
  13 | +    """RULING 53 (08:06 Nov 13): the same speech re-posted by a SECOND channel is ONE moment. Two moments on different
  14 | +    channels are the same speech when their canonical tokens (canon.canon_tokens, the one normal form) are equal, or
  15 | +    when an in-order alignment (difflib's matching blocks) covers at least REPOST_ALIGN_MIN of the shorter one's words.
  16 | +    Of each such group the ORIGINAL publisher's moment is kept: the earliest published_at (a moment with no readable
  17 | +    time is never preferred; a tie goes to the lower moment id). Its channel is the one credited, since only it plays.
  18 | +    -> (the moments kept, in their order, {copy's moment id: why})."""
  19 | +    import collections
  20 | +    import difflib
  21 | +    from datetime import datetime, timezone
  22 | +    import canon
  23 | +    toks = {m["moment_id"]: canon.canon_tokens(m.get("text") or "") for m in ms}
  24 | +
  25 | +    def at(m):                                    # the earliest readable publish time first; none is never first
  26 | +        try:
  27 | +            t = datetime.fromisoformat(str(m.get("published_at") or "").replace("Z", "+00:00"))
  28 | +        except ValueError:
  29 | +            t = None
  30 | +        if t is None or t.tzinfo is None:
  31 | +            return (1, 0.0, m["moment_id"])
  32 | +        return (0, t.astimezone(timezone.utc).timestamp(), m["moment_id"])
  33 | +
  34 | +    def same(a, b):
  35 | +        ta, tb = toks[a["moment_id"]], toks[b["moment_id"]]
  36 | +        if not ta or not tb:
  37 | +            return None
  38 | +        if ta == tb:
  39 | +            return "equal text after normalisation"
  40 | +        short = min(len(ta), len(tb))
  41 | +        if sum((collections.Counter(ta) & collections.Counter(tb)).values()) < REPOST_ALIGN_MIN * short:
  42 | +            return None                           # the shared words bound the aligned ones: 80 % is out of reach
  43 | +        hit = sum(x.size for x in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_matching_blocks())
  44 | +        return f"{hit} of the shorter's {short} words align in order" if hit >= REPOST_ALIGN_MIN * short else None
  45 | +    parent = {m["moment_id"]: m["moment_id"] for m in ms}
  46 | +
  47 | +    def root_of(x):
  48 | +        while parent[x] != x:
  49 | +            parent[x] = parent[parent[x]]
  50 | +            x = parent[x]
  51 | +        return x
  52 | +    how = {}
  53 | +    for i, a in enumerate(ms):
  54 | +        for b in ms[i + 1:]:
  55 | +            if a["channel_id"] == b["channel_id"]:
  56 | +                continue                                  # the rule is about a SECOND channel
  57 | +            w = same(a, b)
  58 | +            if w:
  59 | +                ra, rb = root_of(a["moment_id"]), root_of(b["moment_id"])
  60 | +                if ra != rb:
  61 | +                    parent[rb] = ra
  62 | +                how[(a["moment_id"], b["moment_id"])] = how[(b["moment_id"], a["moment_id"])] = w
  63 | +    groups = {}
  64 | +    for m in ms:
  65 | +        groups.setdefault(root_of(m["moment_id"]), []).append(m)
  66 | +    out, dup = [], {}
  67 | +    keep = {min(g, key=at)["moment_id"] for g in groups.values()}
  68 | +    by = {m["moment_id"]: m for m in ms}
  69 | +    for m in ms:
  70 | +        mid = m["moment_id"]
  71 | +        if mid in keep:
  72 | +            out.append(m)
  73 | +            continue
  74 | +        k = next(x for x in keep if root_of(x) == root_of(mid))
  75 | +        o = by[k]
  76 | +        dup[mid] = (f"the same speech as {k} ({o.get('channel_name') or o['channel_id']}, published "
  77 | +                    f"{o.get('published_at')}), re-posted by a second channel "
  78 | +                    f"({m.get('channel_name') or m['channel_id']}, published {m.get('published_at')}): "
  79 | +                    f"{how.get((k, mid)) or 'aligned through another copy'} (ruling 53: the original publisher's is kept "
  80 | +                    f"and credited)")
  81 | +    return out, dup
  82 | +
  83 | +
  84 |  def no_topic(m):
  85 |      """Why a moment can take NO place under the render's topic rule with the pin's screen (ruling 34), else None: it
  86 |      fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that
  87 | @@ -1269,6 +1344,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  88 |      usd0 = _spent(spend)
  89 |      ms, why = usable(moments, ctx, delivered, optout)
  90 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
  91 | +    ms, reposted = reposted_once(ms)                   # ruling 53: a speech re-posted by a second channel is ONE
  92 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
  93 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
  94 |      trims = {m["moment_id"]: v for m in ms if m["moment_id"] in no_role for v in [trim_variant(m, sources)] if v}
  95 | @@ -1281,10 +1357,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  96 |      levels = current_levels(sources.values(), ctx)
  97 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
  98 |             "no_role": no_role, "ad_read": ad_read, "trimmed": {k: v["moment_id"] for k, v in trims.items()},
  99 | +           "reposted": reposted,
 100 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 101 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 102 |             "package": None}
 103 | -    log(f"  {n_usable} usable, {len(no_role)} of them left out by the render's STAND_ALONE (an opener the clip scorer "
 104 | +    log(f"  {n_usable} usable, {len(reposted)} of them the same speech re-posted by a second channel (ruling 53: "
 105 | +        f"the original publisher's kept), {len(no_role)} left out by the render's STAND_ALONE (an opener the clip scorer "
 106 |          f"would have to affirm, or no place under the topic rule with the pin's screen; {len(trims)} of them back as "
 107 |          f"variants with ONE leading word trimmed, ruling 33 part 2), {len(ad_read)} on an ad-read "
 108 |          f"marker (the exclusion screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
 109 | diff --git a/tests/moments/test_moments.py b/tests/moments/test_moments.py
 110 | index 7a41a3a..c8814db 100644
 111 | --- a/tests/moments/test_moments.py
 112 | +++ b/tests/moments/test_moments.py
 113 | @@ -93,7 +93,7 @@ def pm(mid, channel, dur, rank=10.0, hook=True, clip=True, risk=(), topics=("pri
 114 |              "duration_s": dur, "rank_score": rank, "scores": dict(SCORES), "risk": list(risk), "topics": list(topics),
 115 |              "eligibility": {"hook": {"ok": hook}, "clip": {"ok": clip}}, "on_screen_ok": True, "excluded": [],
 116 |              "published_at": (NOW - timedelta(hours=6)).isoformat(), "speaker": {"turn_change_inside": None},
 117 | -            "text": "Bitcoin x.", "sentences": [0, 0], "words": [0, 1], "start": 0.0, "end": dur,
 118 | +            "text": f"Bitcoin {mid} x.", "sentences": [0, 0], "words": [0, 1], "start": 0.0, "end": dur,
 119 |              "transcript_sha256": "s"}
 120 |  
 121 |  
 122 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 123 | index 062acfe..243c19c 100644
 124 | --- a/tests/package/test_medley.py
 125 | +++ b/tests/package/test_medley.py
 126 | @@ -14,6 +14,7 @@ import json
 127 |  import os
 128 |  import sys
 129 |  import unittest
 130 | +from datetime import timedelta
 131 |  
 132 |  HERE = os.path.dirname(os.path.abspath(__file__))
 133 |  REPO = os.path.dirname(os.path.dirname(HERE))
 134 | @@ -1059,6 +1060,49 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 135 |          self.assertTrue(fail["z"][0].startswith("STEP_A_SAME_VENDOR"))
 136 |  
 137 |  
 138 | +class TestRuling53Reposted(unittest.TestCase):
 139 | +    """RULING 53 (08:06): the same speech re-posted by a second channel is ONE moment, the original publisher's kept and
 140 | +    credited; equal text after normalisation, or 80 % of the words aligned in order. The 07:14 build's pair: CNBC
 141 | +    Television (published 20:55 UTC Nov 12) and Strategy (MicroStrategy) (02:57 UTC Nov 13), the same 13.9 s."""
 142 | +    SPEECH = "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin is about markets."
 143 | +
 144 | +    def m(self, mid, ch, text, hours_ago):
 145 | +        return dict(pm(mid, ch, 13.0), text=text, published_at=(NOW - timedelta(hours=hours_ago)).isoformat())
 146 | +
 147 | +    def test_the_original_publishers_moment_is_kept_and_the_copy_recorded(self):
 148 | +        orig, copy = self.m("o", "CNBC", self.SPEECH, 10), self.m("c", "STRATEGY", self.SPEECH.upper(), 4)
 149 | +        kept, dup = PK.reposted_once([copy, orig, pm("z", "Z", 9.0)])
 150 | +        self.assertEqual([m["moment_id"] for m in kept], ["o", "z"])        # the earliest published, order kept
 151 | +        self.assertIn("the same speech as o (CNBC", dup["c"])
 152 | +        self.assertIn("equal text after normalisation", dup["c"])
 153 | +
 154 | +    def test_eighty_percent_of_the_words_aligned_in_order(self):
 155 | +        words = self.SPEECH.split()
 156 | +        near = " ".join(words[:12] + ["really", "truly"] + words[12:])           # 2 extra words: all 15 align
 157 | +        far = " ".join(words[:7] + ["something", "else", "entirely", "said", "here"])   # 7 of 12 words: 58 %
 158 | +        kept, dup = PK.reposted_once([self.m("o", "A", self.SPEECH, 9), self.m("n", "B", near, 3)])
 159 | +        self.assertEqual((list(dup), [m["moment_id"] for m in kept]), (["n"], ["o"]))
 160 | +        self.assertIn("align in order", dup["n"])
 161 | +        kept, dup = PK.reposted_once([self.m("o", "A", self.SPEECH, 9), self.m("f", "B", far, 3)])
 162 | +        self.assertEqual(dup, {})
 163 | +
 164 | +    def test_only_a_second_channel_and_a_readable_time_first(self):
 165 | +        kept, dup = PK.reposted_once([self.m("a", "A", self.SPEECH, 9), self.m("b", "A", self.SPEECH, 3)])
 166 | +        self.assertEqual(dup, {})                                          # one channel twice: not this rule
 167 | +        nodate = dict(self.m("u", "B", self.SPEECH, 0), published_at=None)
 168 | +        kept, dup = PK.reposted_once([nodate, self.m("d", "A", self.SPEECH, 2)])
 169 | +        self.assertEqual(list(dup), ["u"])                                 # no readable time is never preferred
 170 | +
 171 | +    def test_the_build_never_offers_the_copy_and_records_it(self):
 172 | +        ms = [pm("h", "A", 12.0), self.m("x", "B", self.SPEECH, 10), pm("y", "C", 13.0), pm("z", "D", 13.0),
 173 | +              self.m("w", "E", self.SPEECH, 2)]
 174 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
 175 | +        out = rig.run()
 176 | +        self.assertEqual(list(out["reposted"]), ["w"])
 177 | +        self.assertNotIn("id=w ", next(p for r, p in rig.prompts if r == "angle_write"))
 178 | +        self.assertEqual(out["usable"], 5)                                 # usable keeps its meaning
 179 | +
 180 | +
 181 |  class TestRuling41Search(unittest.TestCase):
 182 |      """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
 183 |      place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
 184 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips
from several YouTube channels). Your role: a strict reviewer of a de-duplication rule.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- build() takes the usable moments (each with moment_id, channel_id, channel_name, video_id, text, published_at),
  screens them (step A, L-v 2, CUTTABLE, ...), and offers the survivors to an angle writer, which proposes line-ups.
  The sign-off credits the channel of every clip that plays.
- The 07:14 build: Strategy (MicroStrategy) re-posted CNBC Television's interview six hours later. The same 13.9 s
  speech appeared as two moments, and the angle writer built every angle on both copies.

The order this diff implements (ORCHESTRATOR RULING 53, 08:06 ET Nov 13, verbatim): "PROPOSAL 2: YES. The same speech
re-posted by a second channel is ONE moment before the angle step; keep the ORIGINAL publisher's (earliest
published_at), credit the original, and record the copy as a duplicate with its reason. Equal text after
normalisation, or time-aligned overlap of 80 % of the words."

The change:
1. pipeline/package.py:
   - reposted_once(ms) -> (kept, {copy id: why}). Two moments on DIFFERENT channels are the same speech when:
     - their canonical tokens (canon.canon_tokens, the pipeline's one normal form) are equal; or
     - an in-order alignment (difflib.SequenceMatcher matching blocks, autojunk off) covers at least 80 %
       (REPOST_ALIGN_MIN) of the SHORTER moment's words.
     A multiset-overlap pre-check skips a pair whose shared words cannot reach 80 %. It is an upper bound, so no
     match is lost.
   - Groups are merged transitively (union-find). Per group the kept moment is the earliest READABLE published_at;
     a moment with no readable time is never preferred; a tie goes to the lower moment id.
   - Each copy's reason names the original (id, channel, time), the copy's channel and time, and the match.
   - build() applies it right after usable(), before the STAND_ALONE screens, the trimmed variants and step A.
     out["reposted"] records the copies; out["usable"] keeps its count from before (its meaning since audit 0310);
     the log line counts the copies.
   - "Credit the original": only the kept moment plays, so the sign-off credits the original's channel.
2. tests/moments/test_moments.py: the shared test helper pm() gave EVERY test moment the same text "Bitcoin x.". Under
   this rule those would all be one speech on many channels, so the default text is now distinct per moment
   ("Bitcoin <id> x.").
3. tests/package/test_medley.py (+ `from datetime import timedelta`):
   - the original is kept and the copy is recorded, with the order kept;
   - 2 extra words still align (a duplicate); 7 of 12 words do not;
   - one channel twice is not this rule;
   - a moment with no readable time is never preferred;
   - the build never offers the copy, records it, and keeps usable's count.
- Measured on the 07:14 build's real 308 moments: 2 copies found, both Strategy re-posts of CNBC Television, one with
  equal text and one with 38 of 38 words aligned. 2.3 s.
- test_medley 86 OK; every other suite OK.

Stated readings (say so if you read the ruling differently):
- K1: "time-aligned overlap of 80 % of the words" is read as an in-order alignment of the two word sequences covering
  80 % of the shorter moment's words. Two re-posts have different clocks, so the alignment is by the words.
- K2: the rule runs on the usable moments, before step A, not only on the cleared pool just before the angle. That
  keeps the original even when a copy would survive a later gate the original fails, as "keep the ORIGINAL
  publisher's, credit the original" asks, and it saves the copy's step-A and L-v 2 calls.
- K3: only DIFFERENT channels ("a second channel"). The same speech twice from one channel is out of this rule; the
  package's duplicate check still covers it.

Check in particular: the match never merges two different speeches that merely share words (the 80 % bound, the
pre-check); the original is chosen by publish time and not by order; no copy can reach the angle step; the recorded
reason; and anything that could be slow on 300 moments.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

