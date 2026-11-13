# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0338
# Branch: pp-selectid
# Generated: 2026-11-13 03:26 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0338/C1_STEP.diff (223 lines)
```
   1 | diff --git a/pipeline/transcript_truth.py b/pipeline/transcript_truth.py
   2 | index bfc8f44f..e002ec4b 100644
   3 | --- a/pipeline/transcript_truth.py
   4 | +++ b/pipeline/transcript_truth.py
   5 | @@ -22,14 +22,18 @@ NEGATIONS = frozenset({"not", "no", "never", "none", "nobody", "nothing", "neith
   6 |                         "won't", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "shouldn't",
   7 |                         "wouldn't", "couldn't", "hasn't", "haven't", "hadn't"})
   8 |  _NUM = re.compile(r"^-?\d+(\.\d+)?$")
   9 | -PAD_S = 1.5
  10 | +PAD_S = 1.5                  # the audio fetched after the clip
  11 | +PAD_BEFORE_S = 4.0           # ruling 38 (03:12 ET Nov 13): the audio before the clip, so the recogniser hears the
  12 | +                             # sentence before it (1.5 s ended inside measured pauses: "the window starts at the clip")
  13 | +PAUSE_MIN_S = 0.700          # ruling 38: a measured pause this long with no recognised word also opens a clip
  14 | +CANON_RUN = 6                # recogniser words read together at an edge, so a spoken number is one canonical token
  15 |  
  16 |  
  17 | -def audio_window(video_id, start, end, out_dir, pad=PAD_S):
  18 | -    """WAV (16 kHz mono) of [start - pad, end + pad] (clamped at the video head), fetched with yt-dlp's download
  19 | -    sections -> (path, the window's real start in video seconds)."""
  20 | +def audio_window(video_id, start, end, out_dir, pad=PAD_S, pad_before=PAD_BEFORE_S):
  21 | +    """WAV (16 kHz mono) of [start - pad_before, end + pad] (clamped at the video head), fetched with yt-dlp's
  22 | +    download sections -> (path, the window's real start in video seconds)."""
  23 |      os.makedirs(out_dir, exist_ok=True)
  24 | -    a, b = max(0.0, start - pad), end + pad
  25 | +    a, b = max(0.0, start - pad_before), end + pad
  26 |      stem = f"{video_id}_{int(a * 1000)}_{int(b * 1000)}"
  27 |      base = os.path.join(out_dir, stem)
  28 |      wav = base + ".wav"
  29 | @@ -140,33 +144,63 @@ def self_repair(words, i, first):
  30 |              and fw.startswith(stem) and r.get("speaker") is not None and r.get("speaker") == f.get("speaker"))
  31 |  
  32 |  
  33 | +def _canon_from(ws, i):
  34 | +    """The first canonical token of the recogniser's words from i on (a spoken number read as one token, the L-v 2
  35 | +    canonicaliser: 'Twenty-five percent' -> '25')."""
  36 | +    c = canon.canon_tokens(" ".join(w.get("text") or "" for w in ws[i:i + CANON_RUN]))
  37 | +    return c[0] if c else None
  38 | +
  39 | +
  40 | +def _canon_to(ws, i):
  41 | +    """The last canonical token of the recogniser's words up to i ('to sixty-eight thousand.' -> '68000')."""
  42 | +    c = canon.canon_tokens(" ".join(w.get("text") or "" for w in ws[max(0, i - CANON_RUN + 1):i + 1]))
  43 | +    return c[-1] if c else None
  44 | +
  45 | +
  46 |  def edges(second, wav_start, start, end, text):
  47 |      """CUTTABLE (orchestrator 06:45 ruling C, ruling 7 (1)): the INDEPENDENT recogniser's own sentence boundaries at
  48 | -    the segment's edges, from its word timing on the SOURCE audio. IN: the recogniser's word at the clip's first word
  49 | -    (same word, within 0.6 s) follows a word ending in terminal punctuation. OUT: the recogniser's word at the clip's last
  50 | -    word (within 0.8 s) ends in terminal punctuation, and the recogniser heard a next word (it did not stop at the
  51 | -    window's edge). Store or caption punctuation is never evidence. -> {"cuttable", "in", "out"}."""
  52 | +    the segment's edges, from its word timing on the SOURCE audio. The clip's first / last word is found by its first
  53 | +    four letters OR by the L-v 2 canonicaliser on a short run of the recogniser's words (ruling 39: 'sixty-eight
  54 | +    thousand.' is the clip's '68,000.'). IN: the recogniser's word at the clip's first word (within 0.6 s) follows a
  55 | +    word ending in terminal punctuation; or (ruling 38) the recogniser heard no word for at least PAUSE_MIN_S before the
  56 | +    clip's opening word (a measured pause), or the window reaches the FILE HEAD and holds no word before the clip (the
  57 | +    clip opens on the file's first spoken word). OUT: the recogniser's word at the clip's last word (within 0.8 s) ends
  58 | +    in terminal punctuation, and the recogniser heard a next word (it did not stop at the window's edge). Store or
  59 | +    caption punctuation is never evidence. -> {"cuttable", "in", "out"}."""
  60 |      ws = [w for w in second.get("words") or [] if w.get("start") is not None]
  61 |      toks = re.findall(r"[\w'’$%.,-]+", re.sub(r"\s+\.(?=\w)", ".", text or ""))     # 'U .S.' is one word 'U.S.' 
  62 |      first, last = _w(toks[0]) if toks else "", _w(toks[-1]) if toks else ""
  63 | +    ct = canon.canon_tokens(text or "")
  64 | +    c_first, c_last = (ct[0], ct[-1]) if ct else (None, None)
  65 |      out = {"in": {"ok": False, "why": "no word timing from the recogniser"},
  66 |             "out": {"ok": False, "why": "no word timing from the recogniser"}}
  67 |      if not ws or not first:
  68 |          return dict(out, cuttable=False)
  69 |      t_in, t_out = start - wav_start, end - wav_start
  70 | -    ci = [i for i, w in enumerate(ws) if abs(float(w["start"]) - t_in) <= 0.6 and _w(w["text"]).startswith(first[:4])]
  71 | -    co = [i for i, w in enumerate(ws) if abs(float(w.get("end") or w["start"]) - t_out) <= 0.8
  72 | -          and _w(w["text"]).rstrip(".")[:4] == last.rstrip(".")[:4]]
  73 | +    ci = [i for i, w in enumerate(ws) if abs(float(w["start"]) - t_in) <= 0.6 and
  74 | +          (_w(w["text"]).startswith(first[:4]) or (c_first is not None and _canon_from(ws, i) == c_first))]
  75 | +    co = [i for i, w in enumerate(ws) if abs(float(w.get("end") or w["start"]) - t_out) <= 0.8 and
  76 | +          (_w(w["text"]).rstrip(".")[:4] == last.rstrip(".")[:4] or (c_last is not None and _canon_to(ws, i) == c_last))]
  77 |      if ci:
  78 |          i = ci[0]
  79 |          j, repair = i - 1, None
  80 |          if self_repair(ws, j, first):           # ruling 8: the speaker's false start opens the sentence
  81 |              repair, j = ws[j]["text"], j - 1
  82 |          prev = ws[j]["text"] if j >= 0 else None
  83 | -        out["in"] = {"ok": prev is not None and prev.rstrip().endswith(TERMINAL), "word": ws[i]["text"],
  84 | -                     "before": prev, "why": "a sentence ends before the clip" if prev and prev.rstrip().endswith(TERMINAL)
  85 | -                     else ("the window starts at the clip: no word before it" if prev is None else
  86 | -                           f"the recogniser runs on into the clip ('{prev}')")}
  87 | +        t_open = float(ws[j + 1]["start"])      # the clip's opening word (its self-repair, when there is one)
  88 | +        gap = t_open - (float(ws[j].get("end") or ws[j]["start"]) if j >= 0 else 0.0)   # no word before: from the
  89 | +        ends = prev is not None and prev.rstrip().endswith(TERMINAL)                     # window's start
  90 | +        head = prev is None and wav_start <= 0.0
  91 | +        pause = gap >= PAUSE_MIN_S - 1e-9
  92 | +        out["in"] = {"ok": ends or pause or head, "word": ws[i]["text"], "before": prev,
  93 | +                     "pause_ms": int(round(gap * 1000)),
  94 | +                     "why": "a sentence ends before the clip" if ends else
  95 | +                     ("the clip opens on the file's first spoken word (the window reaches the file head and holds no "
  96 | +                      "word before it, ruling 38)" if head else
  97 | +                      (f"a measured pause of {gap * 1000:.0f} ms with no recognised word before the clip "
  98 | +                       f"(>= {PAUSE_MIN_S * 1000:.0f} ms, ruling 38)" if pause else
  99 | +                       ("the window starts at the clip: no word before it" if prev is None else
 100 | +                        f"the recogniser runs on into the clip ('{prev}', {gap * 1000:.0f} ms before it)")))}
 101 |          if repair:
 102 |              out["in"].update(self_repair=repair, why=out["in"]["why"] + f"; the speaker's false start '{repair}' "
 103 |                               "opens the sentence (ruling 8: a self-repair, part of the sentence)")
 104 | @@ -191,7 +225,7 @@ def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_s
 105 |      if wav is None:
 106 |          wav, wav_start = audio_window(video_id, start, end, work_dir)
 107 |      sec, rep = second_pass(router, wav)
 108 | -    off = start - (wav_start if wav_start is not None else max(0.0, start - PAD_S))
 109 | +    off = start - (wav_start if wav_start is not None else max(0.0, start - PAD_BEFORE_S))
 110 |      span = span_text(sec, off, off + (end - start)) or sec["text"]
 111 |      sw = [w for w in sec.get("words") or [] if _inside(w, off, off + (end - start))]
 112 |      toks = re.findall(r"[\w'’$%.,-]+", text or "")
 113 | @@ -203,5 +237,6 @@ def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_s
 114 |      return {"video_id": video_id, "start": start, "end": end, "model": rep.backend, "replayed": rep.replayed,
 115 |              "second_pass_text": span, "self_repair": repair, "transcript_ok": cmp_["ok"], "disagree": cmp_["disagree"],
 116 |              "critical": cmp_["critical"], "speakers": turns, "audio": os.path.basename(wav),
 117 | -            "edges": edges(sec, wav_start if wav_start is not None else max(0.0, start - PAD_S), start, end, text),
 118 | +            "edges": edges(sec, wav_start if wav_start is not None else max(0.0, start - PAD_BEFORE_S), start, end,
 119 | +                           text),
 120 |              "ok": cmp_["ok"] and turns["turn_change_inside"] is False}
 121 | diff --git a/tests/package/test_angles.py b/tests/package/test_angles.py
 122 | index 60a9f85a..3c5b64b4 100644
 123 | --- a/tests/package/test_angles.py
 124 | +++ b/tests/package/test_angles.py
 125 | @@ -330,6 +330,97 @@ class TestInventory(unittest.TestCase):
 126 |          self.assertFalse(t["ok"])
 127 |  
 128 |  
 129 | +class TestEdgesRulings38And39(unittest.TestCase):
 130 | +    """Rulings 38 and 39 (03:12 ET Nov 13). The L-v 2 window reaches PAD_BEFORE_S = 4 s before the clip. The IN edge
 131 | +    opens on a recognised sentence end, OR a measured pause of >= 700 ms with no recognised word before the clip's
 132 | +    opening word, OR the file's first spoken word (the window reaches the file head and holds no word before it). The
 133 | +    edge matcher reads a short run of recogniser words with the L-v 2 canonicaliser, so a spoken number matches the
 134 | +    clip's digits."""
 135 | +
 136 | +    TEXT = "Bitcoin is money for everyone."
 137 | +
 138 | +    def ws(self, before, first_at, text=None, after="Next.", step=0.3):
 139 | +        out = [dict(w, speaker="s0") for w in before]
 140 | +        words = (text or self.TEXT).split()
 141 | +        out += [{"text": t, "start": first_at + step * k, "end": first_at + step * k + 0.22, "speaker": "s0"}
 142 | +                for k, t in enumerate(words)]
 143 | +        end = first_at + step * (len(words) - 1) + 0.22
 144 | +        return out + [{"text": after, "start": end + 0.5, "end": end + 0.8, "speaker": "s0"}], end
 145 | +
 146 | +    def edges(self, before, first_at, wav_start=2.0, text=None, after="Next."):
 147 | +        ws, end = self.ws(before, first_at, text, after)
 148 | +        return TT.edges({"words": ws}, wav_start, wav_start + first_at, wav_start + end, text or self.TEXT)
 149 | +
 150 | +    def test_a_measured_pause_of_700_ms_opens_the_clip_and_less_does_not(self):
 151 | +        e = self.edges([{"text": "and", "start": 0.40, "end": 0.80}], 1.55)          # 750 ms after a non-ending word
 152 | +        self.assertTrue(e["in"]["ok"], e["in"])
 153 | +        self.assertIn("measured pause of 750 ms", e["in"]["why"])
 154 | +        self.assertEqual(e["in"]["pause_ms"], 750)
 155 | +        e = self.edges([{"text": "and", "start": 0.40, "end": 0.80}], 1.45)          # 650 ms
 156 | +        self.assertFalse(e["in"]["ok"], e["in"])
 157 | +        self.assertIn("runs on into the clip ('and', 650 ms", e["in"]["why"])
 158 | +        e = self.edges([{"text": "path.", "start": 0.40, "end": 0.80}], 0.95)        # a sentence end needs no pause
 159 | +        self.assertTrue(e["in"]["ok"])
 160 | +        self.assertEqual(e["in"]["why"], "a sentence ends before the clip")
 161 | +
 162 | +    def test_the_files_first_spoken_word_opens_and_a_window_that_starts_at_the_clip_does_not(self):
 163 | +        e = self.edges([], 0.30, wav_start=0.0)                       # the window reaches the file head, no word
 164 | +        self.assertTrue(e["in"]["ok"], e["in"])
 165 | +        self.assertIn("file's first spoken word", e["in"]["why"])
 166 | +        e = self.edges([], 0.30, wav_start=2.0)                       # not the file head: 300 ms measured, no pause
 167 | +        self.assertFalse(e["in"]["ok"], e["in"])
 168 | +        self.assertEqual(e["in"]["why"], "the window starts at the clip: no word before it")
 169 | +        e = self.edges([], 1.00, wav_start=2.0)                       # 1000 ms with no recognised word: a pause
 170 | +        self.assertTrue(e["in"]["ok"], e["in"])
 171 | +        self.assertIn("measured pause of 1000 ms", e["in"]["why"])
 172 | +
 173 | +    def test_a_self_repair_opens_the_clip_and_the_pause_is_measured_before_it(self):
 174 | +        ws = [{"text": "and", "start": 0.10, "end": 0.40, "speaker": "s0"},
 175 | +              {"text": "Bit-", "start": 1.20, "end": 1.30, "speaker": "s0"}]       # 800 ms before the false start
 176 | +        e = self.edges(ws, 1.50)
 177 | +        self.assertTrue(e["in"]["ok"], e["in"])
 178 | +        self.assertEqual((e["in"]["self_repair"], e["in"]["pause_ms"]), ("Bit-", 800))
 179 | +
 180 | +    def test_the_window_reaches_4_s_before_the_clip_and_stops_at_the_file_head(self):
 181 | +        import tempfile
 182 | +        self.assertEqual((TT.PAD_BEFORE_S, TT.PAD_S, TT.PAUSE_MIN_S), (4.0, 1.5, 0.7))
 183 | +        with tempfile.TemporaryDirectory() as d:
 184 | +            for start, end, stem, a in ((10.0, 20.0, "v_6000_21500", 6.0), (2.35, 11.81, "v_0_13310", 0.0)):
 185 | +                open(os.path.join(d, stem + ".wav"), "w").close()          # cached: no fetch
 186 | +                self.assertEqual(TT.audio_window("v", start, end, d), (os.path.join(d, stem + ".wav"), a))
 187 | +
 188 | +    def test_a_spoken_number_matches_the_clips_digits_at_both_edges(self):
 189 | +        text = "Bitcoin is down around 67 to 68,000."
 190 | +        spoken = "Bitcoin is down around sixty-seven to sixty-eight thousand."
 191 | +        ws, end = self.ws([{"text": "real.", "start": 0.2, "end": 0.6}], 1.4, text=spoken, after="James")
 192 | +        e = TT.edges({"words": ws}, 2.0, 3.4, 2.0 + end, text)
 193 | +        self.assertTrue(e["out"]["ok"], e["out"])                   # the 02:37 build's lost OUT edge
 194 | +        self.assertEqual((e["out"]["word"], e["out"]["after"]), ("thousand.", "James"))
 195 | +        self.assertTrue(e["cuttable"])
 196 | +        text2 = "25 % of their portfolio is Bitcoin."
 197 | +        ws2, end2 = self.ws([{"text": "now.", "start": 0.2, "end": 0.6}], 1.4,
 198 | +                            text="Twenty-five percent of their portfolio is Bitcoin.")
 199 | +        e2 = TT.edges({"words": ws2}, 2.0, 3.4, 2.0 + end2, text2)
 200 | +        self.assertTrue(e2["in"]["ok"], e2["in"])
 201 | +        self.assertEqual(e2["in"]["word"], "Twenty-five")
 202 | +        e3 = TT.edges({"words": ws2}, 2.0, 3.4, 2.0 + end2, "26 % of their portfolio is Bitcoin.")
 203 | +        self.assertFalse(e3["in"]["ok"])                              # another number never matches
 204 | +
 205 | +    def test_verify_segment_reads_the_edges_against_the_new_window(self):
 206 | +        class R:
 207 | +            def __init__(self, ws):
 208 | +                self.ws = ws
 209 | +
 210 | +            def transcribe(self, role, wav):
 211 | +                return {"text": " ".join(w["text"] for w in self.ws), "segments": [], "words": self.ws}, \
 212 | +                    type("Rep", (), {"backend": "s", "replayed": False})()
 213 | +        ws, end = self.ws([{"text": "and", "start": 3.00, "end": 3.20}], 4.0)       # a 4 s pre-pad; 800 ms pause
 214 | +        t = TT.verify_segment(R(ws), "v", 10.0, 6.0 + end, self.TEXT, "/nonexistent", wav="w.wav", wav_start=6.0)
 215 | +        self.assertTrue(t["edges"]["cuttable"], t["edges"])
 216 | +        self.assertEqual(t["edges"]["in"]["pause_ms"], 800)
 217 | +        self.assertTrue(t["ok"], t)
 218 | +
 219 | +
 220 |  class TestMajorityOnce(unittest.TestCase):
 221 |      def test_once_then_the_majority_only_when_the_first_run_fails(self):
 222 |          """08:18 item 4 / 08:29: a model verdict that passes its first run runs once; one that does not gets the
 223 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
pipeline/transcript_truth.py runs law L-v 2 on every selected clip: a SECOND, independent recogniser (scribe, with
word timing and diarisation) transcribes the SOURCE audio around the clip. Its edges() is CUTTABLE (orchestrator
rulings C / 7):
- the clip's IN must follow the independent recogniser's own sentence end;
- the clip's OUT must end on one, with a next word heard after it.
Store or caption punctuation is never evidence.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why (orchestrator rulings 03:12 ET Nov 13, from the measured funnel of the 02:37 build):
- 38. IN edge "no word before it": measure a longer window before the clip (pad 4 s). "The acceptance rule is
  unchanged: the independent recogniser must show a sentence end before the clip, or a measured pause of at least
  700 ms with no speech. A clip that starts at the first spoken word of the file counts as a sentence start when the
  window reaches the file head and holds no speech."
  - Measured: 3 of the build's 5 stage-3 losses were IN edges where the 1.5 s window ended inside a pause. The audio
    there was -54 to -59 dBFS for ~1.0 s, and the recogniser heard no word. One clip was an episode's first words
    (2.35 s into the file).
- 39. OUT edge number match (K2, a defect): the edge matcher uses the same number canonicaliser as L-v 2.
  - Measured: the primary's "…67 to 68,000." vs the recogniser's "…sixty-seven to sixty-eight thousand." ending at
    9.48 s (the clip ends at 9.44 s), next word "James". The matcher compared the first 4 letters ("thou" vs "6800")
    and lost a clean sentence end. L-v 2's own comparison canonicalises and had passed the clip.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass. The two acceptance additions here (the 700 ms
  pause and the file head) are the orchestrator's own ruling 38, quoted above.

The change (pipeline/transcript_truth.py):
1. PAD_BEFORE_S = 4.0. audio_window() fetches [start - 4.0, end + 1.5] (PAD_S after, unchanged), clamped at the file
   head. verify_segment's fallbacks use PAD_BEFORE_S. The WAV's name holds its bounds, so new windows are new files
   and new recogniser calls.
2. edges() IN: the clip's opening word (its ruling-8 self-repair when there is one) is accepted when:
   (a) the recogniser's word before it ends in terminal punctuation (unchanged); or
   (b) gap >= PAUSE_MIN_S = 0.700 s, where gap = the opening word's start minus the previous recognised word's end
       (no recognised word in between, by construction); with no recognised word before it in the window, the gap is
       measured from the window's start; or
   (c) the window reaches the file head (wav_start <= 0) and holds no recognised word before the clip.
   The record adds pause_ms and a reason for each case. Everything else in the IN and OUT logic is unchanged.
3. edges() matching (ruling 39): the clip's first / last word is found by the old 4-letter rule OR by canon.canon_tokens
   (the L-v 2 canonicaliser) on a run of up to CANON_RUN = 6 recogniser words starting at (IN) / ending at (OUT) the
   candidate word, compared with the clip text's first / last canonical token. The time windows (0.6 s IN, 0.8 s OUT)
   are unchanged.
4. tests/package/test_angles.py, new class TestEdgesRulings38And39:
   - the 750 / 650 ms boundary;
   - a sentence end needs no pause;
   - the file head vs a window that starts at the clip, and a 1000 ms no-word stretch;
   - a self-repair (the pause is measured before it);
   - audio_window's 4 s pre-pad and the clamp at the file head (cached files, no network);
   - the spoken-number match at OUT ("thousand." + "James") and at IN ("Twenty-five percent" = "25 %"), and a
     different number never matching;
   - verify_segment end to end.

Check in particular:
- that (b) and (c) cannot pass a clip whose opening word FOLLOWS a recognised word by less than 700 ms;
- whether measuring the pause on the recogniser's word timing alone is enough for "a measured pause ... with no
  speech", or whether speech the recogniser missed could pass. Say what you can verify;
- that the canonical match cannot match a DIFFERENT word or number at an edge (a run reaching another number, a
  repeated word);
- off-by-one and index errors in the run slicing (ws[i:i+6], ws[i-5:i+1]) and in j / j+1 with a self-repair;
- that nothing else that the OUT rule or L-v 2's compare / speaker checks accept has changed.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".

