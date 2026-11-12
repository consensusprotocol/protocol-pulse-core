# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-11 22:34 UTC
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

### File: docs/audits/pulse-sentence-law/CURRENT.diff (1290 lines)
```
   1 | diff --git a/pipeline/telegram.py b/pipeline/telegram.py
   2 | index df9df791..5aa8a60a 100644
   3 | --- a/pipeline/telegram.py
   4 | +++ b/pipeline/telegram.py
   5 | @@ -1,11 +1,11 @@
   6 |  #!/usr/bin/env python3
   7 | -"""pipeline/telegram.py — Telegram preview drop with VERIFIED_BY_ORCHESTRATOR guard (M16).
   8 | -
   9 | -The ONLY path for sending review drops. Wraps segment_v1/tg_preview.py with
  10 | -width, height, supports_streaming parameters. Refuses to send unless:
  11 | -  1. Both aspect gate reports are all-pass (no GATE_FAIL.txt)
  12 | -  2. segment/VERIFIED_BY_ORCHESTRATOR file exists (created by the orchestrator)
  13 | +"""pipeline/telegram.py — the ONE path for review drops to the approval chat (never publishing).
  14 |  
  15 | +Red-team 2026-11-11 (A): a drop is sent only when release_auth.authorise(run_dir) passes: the run's attestation is
  16 | +ALL_PASS, deliverable, and every bound file (both finals, EDL, manifests, gate report, verification pack, contact
  17 | +sheets) still has its attested sha256. There is no other send path: the legacy send_telegram_preview (guards on
  18 | +VERIFIED_BY_ORCHESTRATOR / gate_results_*.json / GATE_FAIL.txt, 16:9 only, "gates PASS") is removed, and a run
  19 | +that is not authorised is never sent (no REVIEW ONLY drop; a HOLD's run dir is its record, orchestrator 08:30).
  20 |  Ad-hoc requests.post / curl sends are FORBIDDEN (M16).
  21 |  """
  22 |  import json
  23 | @@ -13,146 +13,40 @@ import os
  24 |  import sys
  25 |  
  26 |  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
  27 | -from config import resolve_paths
  28 | -
  29 | -
  30 | -def send_telegram_preview(segment_dir, qa_version=None):
  31 | -    """Send both outputs to Telegram. Raises on any guard failure."""
  32 | -    paths = resolve_paths(segment_dir, qa_version)
  33 | -    qa_dir = paths["qa_dir"]
  34 | -    out_dir = paths["out_dir"]
  35 | -
  36 | -    # Guard 1: VERIFIED_BY_ORCHESTRATOR must exist
  37 | -    verified_path = os.path.join(segment_dir, "VERIFIED_BY_ORCHESTRATOR")
  38 | -    if not os.path.exists(verified_path):
  39 | -        raise RuntimeError(
  40 | -            f"STOP: Telegram refused — {verified_path} not found. "
  41 | -            "The orchestrator must verify and create this file first (M9, M16)."
  42 | -        )
  43 | -
  44 | -    # Guard 2: no GATE_FAIL.txt in qa_dir
  45 | -    gate_fail = os.path.join(qa_dir, "GATE_FAIL.txt")
  46 | -    if os.path.exists(gate_fail):
  47 | -        raise RuntimeError(f"STOP: Telegram refused — gates failed: {gate_fail}")
  48 | -
  49 | -    # Guard 3: both finals exist
  50 | -    final_16 = os.path.join(out_dir, "segment.mp4")
  51 | -    final_9 = os.path.join(out_dir, "segment_vertical.mp4")
  52 | -    for f in [final_16, final_9]:
  53 | -        if not os.path.exists(f):
  54 | -            raise FileNotFoundError(f"STOP: final output missing: {f}")
  55 | -
  56 | -    # Guard 4: gate results for BOTH aspects exist and show all-pass
  57 | -    for aspect in ["16x9", "9x16"]:
  58 | -        results_path = os.path.join(qa_dir, f"gate_results_{aspect}.json")
  59 | -        if not os.path.exists(results_path):
  60 | -            raise FileNotFoundError(
  61 | -                f"STOP: Telegram refused — gate results missing: {results_path}"
  62 | -            )
  63 | -        with open(results_path) as fp:
  64 | -            results = json.load(fp)
  65 | -        if not results.get("all_pass", False):
  66 | -            raise RuntimeError(
  67 | -                f"STOP: Telegram refused — {aspect} gates not all-pass"
  68 | -            )
  69 | -
  70 | -    # Delegate to tg_preview.py (sendVideo with dimensions)
  71 | -    sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")
  72 | -    try:
  73 | -        from tg_preview import send_preview
  74 | -        segment_name = os.path.basename(os.path.normpath(segment_dir))
  75 | -        caption = f"Pulse Check {segment_name} — gates PASS"
  76 | -        send_preview(final_16, caption)
  77 | -    except ImportError:
  78 | -        # Fallback: use requests directly with proper dimensions
  79 | -        _send_via_requests(final_16, final_9, segment_dir)
  80 |  
  81 |  
  82 | -def _send_via_requests(final_16, final_9, segment_dir):
  83 | -    """Direct Telegram sendVideo with width/height/supports_streaming (M16)."""
  84 | -    import requests
  85 | -    import subprocess
  86 | -
  87 | -    sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
  88 | -    from relay import get_key
  89 | -
  90 | -    bot_token = get_key("TELEGRAM_BOT_TOKEN")
  91 | -    chat_id = get_key("TELEGRAM_CHAT_ID")
  92 | -    if not bot_token or not chat_id:
  93 | -        raise RuntimeError("STOP: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
  94 | -
  95 | -    base = f"https://api.telegram.org/bot{bot_token}"
  96 | -    segment_name = os.path.basename(os.path.normpath(segment_dir))
  97 | -
  98 | -    for path, w, h, label in [
  99 | -        (final_16, 1920, 1080, "16:9"),
 100 | -        (final_9, 1080, 1920, "9:16"),
 101 | -    ]:
 102 | -        # Get duration
 103 | -        r = subprocess.run(
 104 | -            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 105 | -             "-of", "csv=p=0", path],
 106 | -            capture_output=True, text=True, timeout=10, check=True,
 107 | -        )
 108 | -        dur = int(float(r.stdout.strip()))
 109 | -
 110 | -        with open(path, "rb") as f:
 111 | -            resp = requests.post(
 112 | -                f"{base}/sendVideo",
 113 | -                data={
 114 | -                    "chat_id": chat_id,
 115 | -                    "caption": f"{segment_name} ({label}) — gates PASS",
 116 | -                    "width": w,
 117 | -                    "height": h,
 118 | -                    "duration": dur,
 119 | -                    "supports_streaming": "true",
 120 | -                },
 121 | -                files={"video": f},
 122 | -                timeout=300,
 123 | -            )
 124 | -        data = resp.json()
 125 | -        if data.get("ok"):
 126 | -            print(f"  Telegram {label}: message_id={data['result']['message_id']}")
 127 | -        else:
 128 | -            raise RuntimeError(f"STOP: Telegram send failed ({label}): {data}")
 129 | +def send_telegram_preview(*_a, **_k):
 130 | +    """Removed (red-team A, GPT-gates F03 / Claude-gates X5 / C3): the legacy entry point trusted
 131 | +    VERIFIED_BY_ORCHESTRATOR, a truthy all_pass and GATE_FAIL.txt. Every drop goes through deliver_run."""
 132 | +    raise RuntimeError("STOP: send_telegram_preview is removed; use telegram.deliver_run (release_auth.authorise)")
 133 |  
 134 |  
 135 |  # ==============================================================
 136 | -# run_fresh drops (mission 4a / DEC-8, 2026-11-11): both aspects, the verdict in the caption
 137 | +# run_fresh drops (mission 4a / DEC-8; red-team A 2026-11-11): authorised runs only, both aspects
 138 |  # ==============================================================
 139 |  
 140 | -HOLD_OK = "HOLD FOR APPROVAL - all gates passed, no waivers"
 141 | -REVIEW = "REVIEW ONLY"
 142 | +HOLD_OK = "HOLD FOR APPROVAL - all release gates passed, no waivers"
 143 |  CAPTION_MAX = 1024                       # Telegram caption limit
 144 | +TEXT_MAX = 4096                          # Telegram sendMessage limit
 145 | +VIDEO_MAX_BYTES = 49_000_000             # Bot API upload limit is 50 MB; checked BEFORE the first send (X1)
 146 |  DIMS = {"16x9": (1920, 1080), "9x16": (1080, 1920)}
 147 | +FINALS = {"16x9": "out/segment.mp4", "9x16": "out/segment_vertical.mp4"}
 148 |  
 149 |  
 150 | -def gate_status(run_dir):
 151 | -    """(all_pass, failing) from GATE_REPORT.json: every row of both formats must read PASS. Placeholder rows
 152 | -    '<gate>(run_gates)' point to the real row (G11 parity in 9x16) and are not results themselves."""
 153 | -    with open(os.path.join(run_dir, "GATE_REPORT.json")) as f:
 154 | -        rows = json.load(f)["rows"]
 155 | -    failing = [f"{k} ({fmt}): {v[:60]}" for fmt in ("16x9", "9x16") for k, v in rows.get(fmt, {}).items()
 156 | -               if not k.endswith("(run_gates)") and not str(v).startswith("PASS")]
 157 | -    if not rows.get("16x9") or not rows.get("9x16"):
 158 | -        failing.append("gate rows missing for a format")
 159 | -    return not failing, failing
 160 | +def _fit(text, limit):
 161 | +    """text within limit characters, the cut marked (Claude-gates X3: the marker is counted)."""
 162 | +    sfx = " ...(see GATE_REPORT)"
 163 | +    return text if len(text) <= limit else text[:limit - len(sfx)] + sfx
 164 |  
 165 |  
 166 | -def build_caption(run_dir, fmt, option=None, duration=None):
 167 | -    """Verdict line first: HOLD FOR APPROVAL only when every gate passed with no waiver AND the
 168 | -    automated verification pack is complete; otherwise REVIEW ONLY with the failing list."""
 169 | +def build_caption(run_dir, fmt, att, option=None, duration=None):
 170 | +    """The caption of an AUTHORISED run: verdict line first; the MONITORING rows that did not pass are listed as
 171 | +    reported, not release-deciding (addendum '22:15' item 4)."""
 172 | +    import release_auth
 173 |      import vertical_layout
 174 | -    ok, failing = gate_status(run_dir)
 175 | -    vpath = os.path.join(run_dir, "VERIFY", "VERIFICATION.json")
 176 | -    pack_ok = os.path.exists(vpath) and json.load(open(vpath)).get("complete") is True
 177 | -    if not pack_ok:
 178 | -        failing.append("verification pack missing or incomplete")
 179 |      with open(os.path.join(run_dir, "edl.json")) as f:
 180 |          edl = json.load(f)
 181 | -    head = HOLD_OK if (ok and pack_ok) else f"{REVIEW} - {len(failing)} failing"
 182 | -    if option:
 183 | -        head = f"OPTION {option} (transition choice, not a release candidate) | {head}"
 184 | +    head = HOLD_OK if not option else f"OPTION {option} (transition choice) | {HOLD_OK}"
 185 |      lines = [head, f"{os.path.basename(os.path.normpath(run_dir))} | {fmt} {DIMS[fmt][0]}x{DIMS[fmt][1]}"
 186 |               + (f" | {duration:.1f} s" if duration else ""),
 187 |               f"Story: {edl.get('topic', '')}",
 188 | @@ -160,10 +54,10 @@ def build_caption(run_dir, fmt, option=None, duration=None):
 189 |      note = vertical_layout.layout_note(edl) if fmt == "9x16" else ""
 190 |      if note:
 191 |          lines.append(note)
 192 | -    if failing:
 193 | -        lines.append("Failing: " + "; ".join(failing))
 194 | -    cap = "\n".join(lines)
 195 | -    return cap if len(cap) <= CAPTION_MAX else cap[:CAPTION_MAX - 20] + " ...(see GATE_REPORT)"
 196 | +    mon = release_auth.monitoring_report(att.get("rows") or {}).get(fmt) or {}
 197 | +    if mon:
 198 | +        lines.append("Monitoring (reported, not release-deciding): " + "; ".join(f"{k} {v}" for k, v in mon.items()))
 199 | +    return _fit("\n".join(lines), CAPTION_MAX)
 200 |  
 201 |  
 202 |  def _dims(path):
 203 | @@ -175,40 +69,115 @@ def _dims(path):
 204 |      return int(j["streams"][0]["width"]), int(j["streams"][0]["height"]), float(j["format"]["duration"])
 205 |  
 206 |  
 207 | -def deliver_run(run_dir, option=None, send=None, sheets=True):
 208 | -    """Send a run_fresh run's two finals to the approval chat (never publishing), each with its caption,
 209 | -    plus (sheets=True) the verification pack's contact sheets; transition options send the two finals only.
 210 | -    send(kind, path, fields) -> message_id (tests inject it).
 211 | -    Writes TELEGRAM_DELIVERY.json. Raises on a missing/misdimensioned final (fail closed)."""
 212 | -    import hashlib
 213 | -    send = send or _send_bot_api
 214 | -    finals = {"16x9": os.path.join(run_dir, "out", "segment.mp4"),
 215 | -              "9x16": os.path.join(run_dir, "out", "segment_vertical.mp4")}
 216 | -    record = {"option": option, "messages": []}
 217 | -    for fmt, path in finals.items():
 218 | -        if not os.path.exists(path):
 219 | -            raise FileNotFoundError(f"STOP: final output missing: {path}")
 220 | +def headline_numbers_said(run_dir):
 221 | +    """Claude-gates T13: every number in the headline the drop shows (caption story line, suggested title) is said
 222 | +    in the video: it occurs in the locked sentences of the hook or a clip (canon form). Returns the numbers that
 223 | +    are not."""
 224 | +    import canon
 225 | +    import re
 226 | +    with open(os.path.join(run_dir, "edl.json")) as f:
 227 | +        edl = json.load(f)
 228 | +    said = set()
 229 | +    for seg in [edl.get("hook") or {}] + list(edl.get("clips") or []):
 230 | +        said |= set(canon.canon_tokens((seg.get("selection_lock") or {}).get("text") or ""))
 231 | +    heads = " ".join(x for x in (edl.get("headline"), edl.get("topic")) if x)
 232 | +    return sorted({t for t in canon.canon_tokens(heads) if re.fullmatch(r"\d+(\.\d+)?", t)} - said)
 233 | +
 234 | +
 235 | +def _plan(run_dir, option, sheets, att):
 236 | +    """Every message of the drop, built and checked BEFORE anything is sent (X1 / X4 / T13): the two finals at
 237 | +    their real dimensions and size, the contact sheets, and (release drop) the publishing kit."""
 238 | +    plan = []
 239 | +    bad = headline_numbers_said(run_dir)
 240 | +    if bad:
 241 | +        raise RuntimeError(f"STOP: the headline states numbers the video does not say: {bad}")
 242 | +    for fmt, rel in FINALS.items():
 243 | +        path = os.path.join(run_dir, rel)
 244 |          w, h, dur = _dims(path)
 245 |          if (w, h) != DIMS[fmt]:
 246 |              raise RuntimeError(f"STOP: {fmt} final is {w}x{h}, expected {DIMS[fmt][0]}x{DIMS[fmt][1]}")
 247 | -        cap = build_caption(run_dir, fmt, option, duration=dur)
 248 | -        mid = send("video", path, {"caption": cap, "width": w, "height": h, "duration": int(round(dur)),
 249 | -                                   "supports_streaming": "true"})
 250 | -        record["messages"].append({"format": fmt, "message_id": mid, "caption": cap,
 251 | -                                   "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()})
 252 | +        if os.path.getsize(path) > VIDEO_MAX_BYTES:
 253 | +            raise RuntimeError(f"STOP: {fmt} final is {os.path.getsize(path)} bytes > {VIDEO_MAX_BYTES} (Bot API limit)")
 254 | +        plan.append({"key": f"video:{fmt}", "kind": "video", "path": path, "rel": rel, "format": fmt,
 255 | +                     "fields": {"caption": build_caption(run_dir, fmt, att, option, duration=dur), "width": w,
 256 | +                                "height": h, "duration": int(round(dur)), "supports_streaming": "true"}})
 257 |      for fmt in (("16x9", "9x16") if sheets else ()):        # one contact sheet of the finished video per format
 258 | -        p = os.path.join(run_dir, "qa", f"contact_sheet_{fmt}.jpg")
 259 | -        if os.path.exists(p):
 260 | -            kind = "photo" if _photo_ok(p) else "document"
 261 | -            mid = send(kind, p, {"caption": f"contact sheet {fmt}: 2 s stills, +-3 frames at every boundary, "
 262 | -                                            f"full-resolution credits" + (" and segment first frames" if fmt == "9x16" else "")})
 263 | -            record["messages"].append({"sheet": os.path.basename(p), "message_id": mid, "as": kind})
 264 | +        rel = f"qa/contact_sheet_{fmt}.jpg"
 265 | +        p = os.path.join(run_dir, rel)
 266 | +        kind = "photo" if _photo_ok(p) else "document"
 267 | +        if kind == "document" and os.path.getsize(p) > VIDEO_MAX_BYTES:
 268 | +            raise RuntimeError(f"STOP: {rel} is too large for a document send")
 269 | +        plan.append({"key": f"sheet:{fmt}", "kind": kind, "path": p, "rel": rel, "sheet": os.path.basename(p),
 270 | +                     "fields": {"caption": f"contact sheet {fmt}: 2 s stills, +-3 frames at every boundary, "
 271 | +                                           f"full-resolution credits" + (" and segment first frames" if fmt == "9x16" else "")}})
 272 |      if not option:                          # the publishing kit (orchestrator 2026-11-11 15:30), same thread
 273 |          kit = publish_kit(run_dir)
 274 | -        mid = send("message", "", {"text": kit})
 275 | -        record["messages"].append({"publish_kit": kit, "message_id": mid})
 276 | -    with open(os.path.join(run_dir, f"TELEGRAM_DELIVERY{'_' + option if option else ''}.json"), "w") as f:
 277 | -        json.dump(record, f, indent=2)
 278 | +        if len(kit) > TEXT_MAX:
 279 | +            raise RuntimeError(f"STOP: publishing kit is {len(kit)} characters > {TEXT_MAX}")
 280 | +        plan.append({"key": "kit", "kind": "message", "path": "", "rel": None, "kit": kit, "fields": {"text": kit}})
 281 | +    return plan
 282 | +
 283 | +
 284 | +def deliver_run(run_dir, option=None, send=None, sheets=True):
 285 | +    """Send an AUTHORISED run's two finals to the approval chat (never publishing), each with its caption, plus
 286 | +    (sheets=True) both contact sheets and (release drop) the publishing kit. send(kind, path, fields) ->
 287 | +    message_id (tests inject it).
 288 | +      - release_auth.authorise first: not authorised = nothing is sent (raises with the reasons)
 289 | +      - every payload is built and checked against Telegram's limits before the first send
 290 | +      - each file's digest is checked again immediately before it is sent
 291 | +      - TELEGRAM_DELIVERY[_<option>].json is rewritten after EVERY message (atomic): a rerun resumes after the
 292 | +        last sent message and never sends one twice; a message whose outcome is unknown (the request may have
 293 | +        reached Telegram) stops the drop and is never resent automatically; a complete drop is never repeated."""
 294 | +    import hashlib
 295 | +    import release_auth
 296 | +    send = send or _send_bot_api
 297 | +    ok, why, att = release_auth.authorise(run_dir)
 298 | +    if not ok:
 299 | +        raise RuntimeError("STOP: not authorised for release: " + "; ".join(why))
 300 | +    rpath = os.path.join(run_dir, f"TELEGRAM_DELIVERY{'_' + option if option else ''}.json")
 301 | +    att_sha = release_auth.sha256(os.path.join(run_dir, "ATTESTATION.json"))
 302 | +    record = {"option": option, "authorised": True, "attestation_sha256": att_sha, "status": "in_progress",
 303 | +              "messages": [], "unknown": []}
 304 | +    if os.path.exists(rpath):
 305 | +        record = json.load(open(rpath))
 306 | +        if record.get("status") == "complete":
 307 | +            raise RuntimeError(f"STOP: already delivered: {rpath}")
 308 | +        if record.get("attestation_sha256") != att_sha:
 309 | +            raise RuntimeError("STOP: a partial delivery of another attestation exists; reconcile it by hand")
 310 | +        if record.get("unknown"):
 311 | +            raise RuntimeError(f"STOP: outcome unknown for {record['unknown']}; reconcile in the chat before resending")
 312 | +    sent = {m.get("key") for m in record["messages"]}
 313 | +
 314 | +    def save():
 315 | +        tmp = rpath + ".tmp"
 316 | +        with open(tmp, "w") as f:
 317 | +            json.dump(record, f, indent=2)
 318 | +        os.replace(tmp, rpath)
 319 | +    for item in _plan(run_dir, option, sheets, att):
 320 | +        if item["key"] in sent:
 321 | +            continue
 322 | +        if item["rel"] and not release_auth.check_file(run_dir, att, item["rel"]):
 323 | +            raise RuntimeError(f"STOP: {item['rel']} changed after it was authorised")
 324 | +        try:
 325 | +            mid = send(item["kind"], item["path"], item["fields"])
 326 | +        except SendRejected:
 327 | +            raise                                    # Telegram said no: nothing was sent; a rerun may retry it
 328 | +        except Exception:
 329 | +            record["unknown"].append(item["key"])     # the request may have reached Telegram
 330 | +            save()
 331 | +            raise
 332 | +        m = {"key": item["key"], "message_id": mid}
 333 | +        if item["kind"] == "video":
 334 | +            m.update(format=item["format"], caption=item["fields"]["caption"],
 335 | +                     sha256=hashlib.sha256(open(item["path"], "rb").read()).hexdigest())
 336 | +        elif item["key"].startswith("sheet:"):
 337 | +            m.update(sheet=item["sheet"], **{"as": item["kind"]})
 338 | +        else:
 339 | +            m.update(publish_kit=item["kit"])
 340 | +        record["messages"].append(m)
 341 | +        save()
 342 | +    record["status"] = "complete"
 343 | +    save()
 344 |      return record
 345 |  
 346 |  
 347 | @@ -234,11 +203,15 @@ def publish_kit(run_dir):
 348 |      headline = (edl.get("headline") or edl.get("topic") or "").strip().rstrip(".")
 349 |      lines = [f"SUGGESTED TITLE: {headline} | Pulse Check", "", "DESCRIPTION:",
 350 |               f"{headline}. Every clip in this Pulse Check is a creator's own words; go follow them:"]
 351 | +    missing = [ch for ch in credited if not (reg.get(ch, {}).get("yt_handle") and reg.get(ch, {}).get("url")
 352 | +                                             and vids.get(ch))]
 353 | +    if not credited or missing:                      # Claude-gates X4: never a bare name or an empty link
 354 | +        raise RuntimeError(f"STOP: publishing kit incomplete (handle / url / source video): {missing or 'no credits'}")
 355 |      for ch in credited:
 356 | -        e = reg.get(ch, {})
 357 | -        src = ", ".join(f"https://www.youtube.com/watch?v={v}" for v in vids.get(ch, []))
 358 | -        lines.append(f"- {ch} {e.get('yt_handle', '')}: {e.get('url', '')} (clip from {src})")
 359 | -    handles = " ".join(reg.get(ch, {}).get("yt_handle") or ch for ch in credited)
 360 | +        e = reg[ch]
 361 | +        src = ", ".join(f"https://www.youtube.com/watch?v={v}" for v in vids[ch])
 362 | +        lines.append(f"- {ch} {e['yt_handle']}: {e['url']} (clip from {src})")
 363 | +    handles = " ".join(reg[ch]["yt_handle"] for ch in credited)
 364 |      lines += ["", "FIRST COMMENT:", f"credits: {handles}", ORANGE_HEART]
 365 |      return "\n".join(lines)
 366 |  
 367 | @@ -258,27 +231,34 @@ def _photo_ok(path):
 368 |      return os.path.getsize(path) <= PHOTO_MAX_BYTES and w + h <= 10000 and max(w, h) / max(1, min(w, h)) <= 20
 369 |  
 370 |  
 371 | +class SendRejected(RuntimeError):
 372 | +    """Telegram answered and refused the message: it was NOT sent (a rerun may send it)."""
 373 | +
 374 | +
 375 |  def _send_bot_api(kind, path, fields):
 376 | -    """One sendVideo / sendPhoto to the approval chat (M16 path; credentials never printed)."""
 377 | +    """One sendVideo / sendPhoto / sendDocument / sendMessage to the approval chat (M16 path). Credentials never
 378 | +    printed: a network error is re-raised by type only (its text carries the URL with the token, Claude-gates X2);
 379 | +    a refusal from Telegram raises SendRejected; anything else (timeout, connection, unreadable answer) means the
 380 | +    outcome is unknown and the caller must not resend it automatically."""
 381 |      import requests
 382 | -    sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
 383 | +    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video_pipeline_v3"))
 384 |      from relay import get_key
 385 |      tok, chat = get_key("TELEGRAM_BOT_TOKEN"), get_key("TELEGRAM_CHAT_ID")
 386 |      if not tok or not chat:
 387 | -        raise RuntimeError("STOP: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
 388 | -    if kind == "message":                   # plain text in the same chat (the publishing kit)
 389 | -        resp = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", data={"chat_id": chat, **fields},
 390 | -                             timeout=60)
 391 | -        data = resp.json()
 392 | -        if not data.get("ok"):
 393 | -            raise RuntimeError(f"STOP: Telegram sendMessage failed: {data.get('description')}")
 394 | -        return data["result"]["message_id"]
 395 | +        raise SendRejected("STOP: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
 396 |      method, field = {"video": ("sendVideo", "video"), "photo": ("sendPhoto", "photo"),
 397 | -                     "document": ("sendDocument", "document")}[kind]
 398 | -    with open(path, "rb") as fh:
 399 | -        resp = requests.post(f"https://api.telegram.org/bot{tok}/{method}", data={"chat_id": chat, **fields},
 400 | -                             files={field: fh}, timeout=600)
 401 | -    data = resp.json()
 402 | +                     "document": ("sendDocument", "document"), "message": ("sendMessage", None)}[kind]
 403 | +    try:
 404 | +        if field is None:                       # plain text in the same chat (the publishing kit)
 405 | +            resp = requests.post(f"https://api.telegram.org/bot{tok}/{method}", data={"chat_id": chat, **fields},
 406 | +                                 timeout=60)
 407 | +        else:
 408 | +            with open(path, "rb") as fh:
 409 | +                resp = requests.post(f"https://api.telegram.org/bot{tok}/{method}", data={"chat_id": chat, **fields},
 410 | +                                     files={field: fh}, timeout=600)
 411 | +        data = resp.json()
 412 | +    except Exception as e:
 413 | +        raise RuntimeError(f"STOP: Telegram {method}: outcome unknown ({type(e).__name__})") from None
 414 |      if not data.get("ok"):
 415 | -        raise RuntimeError(f"STOP: Telegram {method} failed: {data.get('description')}")
 416 | +        raise SendRejected(f"STOP: Telegram {method} refused: {data.get('error_code')} {data.get('description')}")
 417 |      return data["result"]["message_id"]
 418 | diff --git a/pipeline/test_edl_rules.py b/pipeline/test_edl_rules.py
 419 | index 23714078..dab6f618 100644
 420 | --- a/pipeline/test_edl_rules.py
 421 | +++ b/pipeline/test_edl_rules.py
 422 | @@ -628,17 +628,24 @@ class TestFailClosedShoutout(unittest.TestCase):
 423 |  
 424 |  
 425 |  class TestTelegramGuard(unittest.TestCase):
 426 | -    """M16: telegram.py refuses without VERIFIED_BY_ORCHESTRATOR."""
 427 | +    """M16 on the release contract (red-team A): the legacy entry point is removed, and deliver_run refuses a run
 428 | +    without an attestation before anything is sent."""
 429 |  
 430 |      def test_refuses_without_verification(self):
 431 | -        from telegram import send_telegram_preview
 432 |          import tempfile
 433 | +        import telegram
 434 | +        from telegram import send_telegram_preview
 435 |          with tempfile.TemporaryDirectory() as tmpdir:
 436 |              os.makedirs(os.path.join(tmpdir, "out"))
 437 |              os.makedirs(os.path.join(tmpdir, "qa"))
 438 |              with self.assertRaises(RuntimeError) as ctx:
 439 |                  send_telegram_preview(tmpdir)
 440 | -            self.assertIn("VERIFIED_BY_ORCHESTRATOR", str(ctx.exception))
 441 | +            self.assertIn("removed", str(ctx.exception))
 442 | +            sent = []
 443 | +            with self.assertRaises(RuntimeError) as ctx:
 444 | +                telegram.deliver_run(tmpdir, send=lambda k, p, f: sent.append(k) or 1)
 445 | +            self.assertIn("not authorised", str(ctx.exception))
 446 | +            self.assertEqual(sent, [])
 447 |  
 448 |  
 449 |  class TestAcousticModule(unittest.TestCase):
 450 | diff --git a/pipeline/test_failure_blocks.py b/pipeline/test_failure_blocks.py
 451 | index a2cd60ed..17e04250 100644
 452 | --- a/pipeline/test_failure_blocks.py
 453 | +++ b/pipeline/test_failure_blocks.py
 454 | @@ -1,17 +1,14 @@
 455 |  #!/usr/bin/env python3
 456 | -"""Addendum 2 item 6: failure blocks delivery tests.
 457 | -
 458 | -Each test creates a scratch copy of a passing run dir, sabotages one element,
 459 | -and verifies that send_telegram_preview raises before sending.
 460 | -
 461 | -Tests:
 462 | -  (a) Delete a required clip record from gate results
 463 | -  (b) Delete one expected gate result file
 464 | -  (c) Modify the mp4 after VERIFIED_BY_ORCHESTRATOR (hash mismatch scenario)
 465 | -  (d) Remove VERIFIED_BY_ORCHESTRATOR marker
 466 | -
 467 | -No Telegram calls are made. The guard logic raises before reaching the sender.
 468 | -"""
 469 | +"""Addendum 2 item 6 (failure blocks delivery), on the release contract of 2026-11-11 (red-team A).
 470 | +
 471 | +Each test builds a complete AUTHORISED run dir (test_release_auth.make_run), sabotages one element, and verifies
 472 | +that telegram.deliver_run refuses before anything is sent:
 473 | +  (a) a required gate row deleted from GATE_REPORT.json after the attestation
 474 | +  (b) a required gate row set to FAIL (re-attested: the attestation itself is HOLD)
 475 | +  (c) the mp4 modified after the attestation (digest mismatch)
 476 | +  (d) the attestation removed (the old VERIFIED_BY_ORCHESTRATOR marker is gone; this is its replacement)
 477 | +  (e) a legacy GATE_FAIL.txt / truthy gate_results_*.json no longer authorise anything
 478 | +No Telegram calls are made: the sender is injected and must never be called."""
 479 |  import json
 480 |  import os
 481 |  import shutil
 482 | @@ -20,125 +17,53 @@ import tempfile
 483 |  import unittest
 484 |  
 485 |  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
 486 | -from config import resolve_paths
 487 | -
 488 | -# We need telegram.py
 489 | -from telegram import send_telegram_preview
 490 | +import release_auth as RA  # noqa: E402
 491 | +import telegram as TG  # noqa: E402
 492 | +from test_release_auth import edit_json, make_run, passing_rows  # noqa: E402
 493 |  
 494 |  
 495 |  class TestFailureBlocksDelivery(unittest.TestCase):
 496 | -    """Sabotage tests against the Telegram guard in pipeline/telegram.py."""
 497 | -
 498 | -    @classmethod
 499 | -    def setUpClass(cls):
 500 | -        """Create a minimal scratch run dir that would pass all guards."""
 501 | -        cls.tmpdir = tempfile.mkdtemp(prefix="failure_blocks_")
 502 | -        cls.segment_dir = cls.tmpdir
 503 | -
 504 | -        # Create out dir with dummy mp4s
 505 | -        out_dir = os.path.join(cls.tmpdir, "out")
 506 | -        os.makedirs(out_dir)
 507 | -        for name in ("segment.mp4", "segment_vertical.mp4"):
 508 | -            with open(os.path.join(out_dir, name), "wb") as f:
 509 | -                f.write(b"\x00" * 1024)  # dummy content
 510 | -
 511 | -        # Create qa dir with passing gate results
 512 | -        qa_dir = os.path.join(cls.tmpdir, "qa")
 513 | -        os.makedirs(qa_dir)
 514 | -        for aspect in ("16x9", "9x16"):
 515 | -            results = {
 516 | -                "all_pass": True,
 517 | -                "G1_voice": {"pass": True},
 518 | -                "G3_cuts": {"pass": True},
 519 | -                "G5_tech": {"pass": True},
 520 | -                "G8_sharpness": {"pass": True},
 521 | -            }
 522 | -            with open(os.path.join(qa_dir, f"gate_results_{aspect}.json"), "w") as f:
 523 | -                json.dump(results, f)
 524 | -
 525 | -        # Create VERIFIED_BY_ORCHESTRATOR marker
 526 | -        with open(os.path.join(cls.tmpdir, "VERIFIED_BY_ORCHESTRATOR"), "w") as f:
 527 | -            f.write("verified")
 528 | -
 529 | -        # Create edl.json (for config.resolve_paths)
 530 | -        with open(os.path.join(cls.tmpdir, "edl.json"), "w") as f:
 531 | -            json.dump({"clips": []}, f)
 532 | -
 533 | -    @classmethod
 534 | -    def tearDownClass(cls):
 535 | -        shutil.rmtree(cls.tmpdir, ignore_errors=True)
 536 | -
 537 | -    def _fresh_copy(self):
 538 | -        """Return a fresh copy of the passing run dir."""
 539 | -        copy_dir = tempfile.mkdtemp(prefix="sabotage_")
 540 | -        shutil.copytree(self.segment_dir, copy_dir, dirs_exist_ok=True)
 541 | -        return copy_dir
 542 | -
 543 | -    def test_a_delete_gate_result_blocks(self):
 544 | -        """(a) Delete one gate result file — telegram must refuse."""
 545 | -        d = self._fresh_copy()
 546 | -        try:
 547 | -            qa_dir = os.path.join(d, "qa")
 548 | -            os.remove(os.path.join(qa_dir, "gate_results_16x9.json"))
 549 | -            with self.assertRaises((FileNotFoundError, RuntimeError)) as ctx:
 550 | -                send_telegram_preview(d)
 551 | -            self.assertIn("gate", str(ctx.exception).lower())
 552 | -        finally:
 553 | -            shutil.rmtree(d, ignore_errors=True)
 554 | -
 555 | -    def test_b_set_gate_fail_blocks(self):
 556 | -        """(b) Set all_pass=false in gate results — telegram must refuse."""
 557 | -        d = self._fresh_copy()
 558 | -        try:
 559 | -            qa_dir = os.path.join(d, "qa")
 560 | -            path = os.path.join(qa_dir, "gate_results_9x16.json")
 561 | -            with open(path) as f:
 562 | -                data = json.load(f)
 563 | -            data["all_pass"] = False
 564 | -            with open(path, "w") as f:
 565 | -                json.dump(data, f)
 566 | -            with self.assertRaises(RuntimeError) as ctx:
 567 | -                send_telegram_preview(d)
 568 | -            self.assertIn("not all-pass", str(ctx.exception))
 569 | -        finally:
 570 | -            shutil.rmtree(d, ignore_errors=True)
 571 | -
 572 | -    def test_c_modify_mp4_after_verified(self):
 573 | -        """(c) Modify mp4 after VERIFIED — currently only checks existence.
 574 | -        This test verifies the file still blocks if deleted entirely."""
 575 | -        d = self._fresh_copy()
 576 | -        try:
 577 | -            out_dir = os.path.join(d, "out")
 578 | -            os.remove(os.path.join(out_dir, "segment.mp4"))
 579 | -            with self.assertRaises(FileNotFoundError) as ctx:
 580 | -                send_telegram_preview(d)
 581 | -            self.assertIn("missing", str(ctx.exception).lower())
 582 | -        finally:
 583 | -            shutil.rmtree(d, ignore_errors=True)
 584 | -
 585 | -    def test_d_remove_verified_marker_blocks(self):
 586 | -        """(d) Remove VERIFIED_BY_ORCHESTRATOR — telegram must refuse."""
 587 | -        d = self._fresh_copy()
 588 | -        try:
 589 | -            os.remove(os.path.join(d, "VERIFIED_BY_ORCHESTRATOR"))
 590 | -            with self.assertRaises(RuntimeError) as ctx:
 591 | -                send_telegram_preview(d)
 592 | -            self.assertIn("VERIFIED_BY_ORCHESTRATOR", str(ctx.exception))
 593 | -        finally:
 594 | -            shutil.rmtree(d, ignore_errors=True)
 595 | -
 596 | -    def test_e_gate_fail_txt_blocks(self):
 597 | -        """(e) Create GATE_FAIL.txt — telegram must refuse even with passing results."""
 598 | -        d = self._fresh_copy()
 599 | -        try:
 600 | -            qa_dir = os.path.join(d, "qa")
 601 | -            with open(os.path.join(qa_dir, "GATE_FAIL.txt"), "w") as f:
 602 | -                f.write("G8 sharpness below floor")
 603 | -            with self.assertRaises(RuntimeError) as ctx:
 604 | -                send_telegram_preview(d)
 605 | -            self.assertIn("gates failed", str(ctx.exception).lower())
 606 | -        finally:
 607 | -            shutil.rmtree(d, ignore_errors=True)
 608 | +    def setUp(self):
 609 | +        self.tmp = tempfile.mkdtemp(prefix="failure_blocks_")
 610 | +        self.addCleanup(shutil.rmtree, self.tmp, True)
 611 | +
 612 | +    def refused(self, rd, needle):
 613 | +        sent = []
 614 | +        with self.assertRaises(RuntimeError) as ctx:
 615 | +            TG.deliver_run(rd, send=lambda kind, path, fields: sent.append(kind) or 1)
 616 | +        self.assertEqual(sent, [])
 617 | +        self.assertIn(needle, str(ctx.exception))
 618 | +
 619 | +    def test_a_deleted_gate_row_blocks(self):
 620 | +        rd = make_run(self.tmp)
 621 | +        edit_json(os.path.join(rd, "GATE_REPORT.json"), lambda d: d["rows"]["16x9"].pop("G18_word_for_word"))
 622 | +        self.refused(rd, "GATE_REPORT.json rows / evidence differ")
 623 | +
 624 | +    def test_b_failing_gate_blocks(self):
 625 | +        rows = passing_rows()
 626 | +        rows["9x16"]["G9_tail"] = "FAIL"
 627 | +        self.refused(make_run(self.tmp, rows=rows), "9x16 G9_tail: FAIL")
 628 | +
 629 | +    def test_c_modified_mp4_after_attestation_blocks(self):
 630 | +        rd = make_run(self.tmp)
 631 | +        with open(os.path.join(rd, "out", "segment.mp4"), "ab") as f:
 632 | +            f.write(b"\0" * 16)
 633 | +        self.refused(rd, "out/segment.mp4: changed since it was attested")
 634 | +
 635 | +    def test_d_no_attestation_blocks(self):
 636 | +        rd = make_run(self.tmp)
 637 | +        os.remove(os.path.join(rd, "ATTESTATION.json"))
 638 | +        self.refused(rd, "no readable attestation")
 639 | +
 640 | +    def test_e_legacy_markers_authorise_nothing(self):
 641 | +        rd = make_run(self.tmp, attest=False)
 642 | +        open(os.path.join(rd, "VERIFIED_BY_ORCHESTRATOR"), "w").write("verified")
 643 | +        for fmt in ("16x9", "9x16"):
 644 | +            json.dump({"all_pass": True}, open(os.path.join(rd, "qa", f"gate_results_{fmt}.json"), "w"))
 645 | +        self.refused(rd, "no readable attestation")
 646 | +        with self.assertRaises(RuntimeError):
 647 | +            TG.send_telegram_preview(rd)
 648 | +        self.assertFalse(RA.authorise(rd)[0])
 649 |  
 650 |  
 651 |  if __name__ == "__main__":
 652 | diff --git a/pipeline/test_telegram_delivery.py b/pipeline/test_telegram_delivery.py
 653 | index d35c9278..390a3028 100644
 654 | --- a/pipeline/test_telegram_delivery.py
 655 | +++ b/pipeline/test_telegram_delivery.py
 656 | @@ -1,7 +1,10 @@
 657 |  #!/usr/bin/env python3
 658 | -"""Mission 4a / DEC-8 delivery contract: 'HOLD FOR APPROVAL - all gates passed, no waivers' only when every
 659 | -gate row of both formats is PASS and the automated verification pack is complete; otherwise 'REVIEW ONLY'
 660 | -with the failing list. Both aspects, real dimensions; safe frames named in the 9:16 caption. No network:
 661 | +"""Delivery contract (mission 4a / DEC-8; red-team 2026-11-11 A): telegram.deliver_run sends ONLY a run that
 662 | +release_auth.authorise passes, captioned 'HOLD FOR APPROVAL - all release gates passed, no waivers'; a run that
 663 | +is not authorised sends NOTHING (no REVIEW ONLY drop). Every payload is checked before the first send; each file's
 664 | +digest is checked again right before it is sent; every message is checkpointed, a rerun resumes without
 665 | +duplicates, an unknown outcome is never resent automatically, a complete drop is never repeated. Both aspects at
 666 | +real dimensions; safe frames named in the 9:16 caption; the publishing kit closes the release drop. No network:
 667 |  the sender is injected. Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_telegram_delivery.py"""
 668 |  import json
 669 |  import os
 670 | @@ -14,124 +17,187 @@ import unittest
 671 |  PIPELINE = os.path.dirname(os.path.abspath(__file__))
 672 |  sys.path.insert(0, PIPELINE)
 673 |  
 674 | +import release_auth as RA  # noqa: E402
 675 |  import telegram as TG  # noqa: E402
 676 | +from test_release_auth import edit_json, make_run, passing_rows  # noqa: E402
 677 |  
 678 | -ROWS = {"16x9": {"G1_voice": "PASS", "G11_parity(run_gates)": "NOT RUN BY run_gates (no horiz) — see G11 below",
 679 | -                 "G16_sentence_boundary": "PASS", "G18_word_for_word": "PASS"},
 680 | -        "9x16": {"G1_voice": "PASS", "G11_parity(run_gates)": "NOT RUN BY run_gates (no horiz) — see G11 below",
 681 | -                 "G11_parity": "PASS", "G4s_layout_truth": "PASS", "G18_word_for_word": "PASS"}}
 682 | -
 683 | -
 684 | -class TestDelivery(unittest.TestCase):
 685 | -    @classmethod
 686 | -    def setUpClass(cls):
 687 | -        cls.media = tempfile.mkdtemp(prefix="tgm_")
 688 | -        for name, (w, h) in (("segment.mp4", (1920, 1080)), ("segment_vertical.mp4", (1080, 1920)),
 689 | -                             ("wrong.mp4", (1280, 720))):
 690 | -            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r=24:d=1",
 691 | -                            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
 692 | -                            os.path.join(cls.media, name)], check=True)
 693 | -
 694 | -    @classmethod
 695 | -    def tearDownClass(cls):
 696 | -        shutil.rmtree(cls.media, ignore_errors=True)
 697 | -
 698 | -    def run_dir(self, rows=ROWS, pack_complete=True, flagged=False):
 699 | -        rd = tempfile.mkdtemp(prefix="tgr_")
 700 | -        self.addCleanup(shutil.rmtree, rd, True)
 701 | -        os.makedirs(os.path.join(rd, "out"))
 702 | -        os.makedirs(os.path.join(rd, "VERIFY"))
 703 | -        for name in ("segment.mp4", "segment_vertical.mp4"):
 704 | -            shutil.copy(os.path.join(self.media, name), os.path.join(rd, "out", name))
 705 | -        json.dump({"rows": rows}, open(os.path.join(rd, "GATE_REPORT.json"), "w"))
 706 | -        json.dump({"complete": pack_complete}, open(os.path.join(rd, "VERIFY", "VERIFICATION.json"), "w"))
 707 | -        shot = {"start": 0.0, "end": 9.4, "class": "screen" if flagged else "single", "flagged": flagged}
 708 | -        json.dump({"topic": "Bitcoin price dip",
 709 | -                   "hook": {"channel": "Yahoo Finance", "vertical_layout": {"shots": [shot], "flagged": flagged}},
 710 | -                   "clips": [{"index": 1, "channel": "Natalie Brunell",
 711 | -                              "vertical_layout": {"shots": [dict(shot, **{"class": "single", "flagged": False})],
 712 | -                                                  "flagged": False}}]},
 713 | -                  open(os.path.join(rd, "edl.json"), "w"))
 714 | -        return rd
 715 | -
 716 | -    def deliver(self, rd, option=None):
 717 | +
 718 | +class Base(unittest.TestCase):
 719 | +    def setUp(self):
 720 | +        self.tmp = tempfile.mkdtemp(prefix="tg_")
 721 | +        self.addCleanup(shutil.rmtree, self.tmp, True)
 722 | +
 723 | +    def deliver(self, rd, option=None, fail_at=None, exc=None, sheets=True):
 724 |          sent = []
 725 | -        rec = TG.deliver_run(rd, option=option, send=lambda kind, path, fields: sent.append(
 726 | -            (kind, os.path.basename(path), fields)) or len(sent))
 727 | +
 728 | +        def send(kind, path, fields):
 729 | +            if fail_at is not None and len(sent) == fail_at:
 730 | +                raise exc
 731 | +            sent.append((kind, os.path.basename(path), fields))
 732 | +            return len(sent)
 733 | +        rec = TG.deliver_run(rd, option=option, send=send, sheets=sheets)
 734 |          return rec, sent
 735 |  
 736 | -    def test_all_pass_with_complete_pack_is_hold_for_approval_in_both_aspects(self):
 737 | -        rd = self.run_dir()
 738 | +
 739 | +class TestAuthorisedDrop(Base):
 740 | +    def test_an_authorised_run_goes_out_in_both_aspects_with_sheets_and_kit(self):
 741 | +        rd = make_run(self.tmp)
 742 |          rec, sent = self.deliver(rd)
 743 |          vids = [s for s in sent if s[0] == "video"]
 744 |          self.assertEqual([(s[1], s[2]["width"], s[2]["height"]) for s in vids],
 745 |                           [("segment.mp4", 1920, 1080), ("segment_vertical.mp4", 1080, 1920)])
 746 |          for s in vids:
 747 |              self.assertTrue(s[2]["caption"].startswith(TG.HOLD_OK), s[2]["caption"])
 748 | -            self.assertNotIn("Failing", s[2]["caption"])
 749 | +        self.assertEqual([(s[0], s[1]) for s in sent if s[0] not in ("video", "message")],
 750 | +                         [("photo", "contact_sheet_16x9.jpg"), ("photo", "contact_sheet_9x16.jpg")])
 751 | +        self.assertEqual(sent[-1][0], "message")
 752 |          written = json.load(open(os.path.join(rd, "TELEGRAM_DELIVERY.json")))
 753 | +        self.assertEqual(written["status"], "complete")
 754 | +        self.assertTrue(written["authorised"])
 755 |          self.assertEqual([m["format"] for m in written["messages"] if "format" in m], ["16x9", "9x16"])
 756 |  
 757 | -    def test_any_failing_row_is_review_only_with_the_list(self):
 758 | -        rows = json.loads(json.dumps(ROWS))
 759 | -        rows["9x16"]["G4s_layout_truth"] = "FAIL"
 760 | -        _, sent = self.deliver(self.run_dir(rows))
 761 | -        cap = sent[0][2]["caption"]
 762 | -        self.assertTrue(cap.startswith("REVIEW ONLY - 1 failing"), cap)
 763 | -        self.assertIn("G4s_layout_truth (9x16): FAIL", cap)
 764 | -
 765 | -    def test_a_waiver_is_not_a_pass(self):
 766 | -        rows = json.loads(json.dumps(ROWS))
 767 | -        rows["16x9"]["G8_sharpness"] = "FLAG/LIMITED (absolute floor vs soft source)"
 768 | -        _, sent = self.deliver(self.run_dir(rows))
 769 | -        self.assertTrue(sent[0][2]["caption"].startswith("REVIEW ONLY"), sent[0][2]["caption"])
 770 | -        self.assertIn("G8_sharpness (16x9): FLAG/LIMITED", sent[0][2]["caption"])
 771 | -
 772 | -    def test_incomplete_verification_pack_is_review_only(self):
 773 | -        _, sent = self.deliver(self.run_dir(pack_complete=False))
 774 | -        self.assertIn("verification pack missing or incomplete", sent[0][2]["caption"])
 775 | -        self.assertTrue(sent[0][2]["caption"].startswith("REVIEW ONLY"))
 776 | -
 777 | -    def test_safe_frame_is_named_in_the_vertical_caption(self):
 778 | -        _, sent = self.deliver(self.run_dir(flagged=True))
 779 | +    def test_the_caption_carries_the_duration_and_the_vertical_names_its_safe_frames(self):
 780 | +        edl = json.load(open(os.path.join(make_run(self.tmp, attest=False), "edl.json")))
 781 | +        shot = {"start": 0.0, "end": 9.4, "class": "screen", "flagged": True}
 782 | +        edl["hook"]["vertical_layout"] = {"shots": [shot], "flagged": True}
 783 | +        rd = make_run(self.tmp, edl=edl)
 784 | +        _, sent = self.deliver(rd)
 785 | +        self.assertIn(" s", sent[0][2]["caption"].split("\n")[1])
 786 |          vert = [s for s in sent if s[1] == "segment_vertical.mp4"][0][2]["caption"]
 787 |          self.assertIn("9:16 SAFE FRAME hook (Yahoo Finance): layout=screen 0.00-9.40 s", vert)
 788 |  
 789 | -    def test_option_label_comes_first(self):
 790 | -        _, sent = self.deliver(self.run_dir(), option="B")
 791 | -        self.assertTrue(sent[0][2]["caption"].startswith("OPTION B (transition choice"), sent[0][2]["caption"])
 792 | +    def test_monitoring_rows_are_reported_in_the_caption_not_deciding(self):
 793 | +        rows = passing_rows()
 794 | +        rows["16x9"]["G1_voice"] = "FAIL"
 795 | +        _, sent = self.deliver(make_run(self.tmp, rows=rows))
 796 | +        self.assertTrue(sent[0][2]["caption"].startswith(TG.HOLD_OK))
 797 | +        self.assertIn("Monitoring (reported, not release-deciding): G1_voice FAIL", sent[0][2]["caption"])
 798 |  
 799 | -    def test_one_contact_sheet_per_format_with_the_main_drop_only(self):
 800 | -        from PIL import Image
 801 | -        rd = self.run_dir()
 802 | -        os.makedirs(os.path.join(rd, "qa"), exist_ok=True)
 803 | -        Image.new("RGB", (1920, 2600)).save(os.path.join(rd, "qa", "contact_sheet_16x9.jpg"))
 804 | -        Image.new("RGB", (6000, 4500)).save(os.path.join(rd, "qa", "contact_sheet_9x16.jpg"))   # too big for a photo
 805 | -        _, sent = self.deliver(rd)
 806 | -        self.assertEqual([(s[0], s[1]) for s in sent if s[0] not in ("video", "message")],
 807 | -                         [("photo", "contact_sheet_16x9.jpg"), ("document", "contact_sheet_9x16.jpg")])
 808 | -        sent2 = []
 809 | -        TG.deliver_run(rd, option="A", sheets=False, send=lambda k, p, f: sent2.append(k) or 1)
 810 | -        self.assertEqual(sent2, ["video", "video"])
 811 | +    def test_an_option_is_labelled_first_and_carries_no_kit(self):
 812 | +        rd = make_run(self.tmp)
 813 | +        _, sent = self.deliver(rd, option="B", sheets=False)
 814 | +        self.assertTrue(sent[0][2]["caption"].startswith("OPTION B (transition choice)"), sent[0][2]["caption"])
 815 | +        self.assertEqual([s[0] for s in sent], ["video", "video"])
 816 |  
 817 |      def test_the_release_drop_ends_with_the_publishing_kit(self):
 818 |          # orchestrator 2026-11-11 15:30: a suggested title, a description crediting and linking every source,
 819 |          # and the first-comment line "credits:" + every creator's @handle, a line break, the orange heart alone
 820 | -        rd = self.run_dir()
 821 | -        _, sent = self.deliver(rd)
 822 | -        self.assertEqual(sent[-1][0], "message")
 823 | +        _, sent = self.deliver(make_run(self.tmp))
 824 |          kit = sent[-1][2]["text"]
 825 |          self.assertIn("SUGGESTED TITLE: Bitcoin price dip", kit)
 826 |          self.assertIn("- Yahoo Finance @YahooFinance: https://www.youtube.com/@YahooFinance", kit)
 827 |          self.assertIn("- Natalie Brunell @nataliebrunell: https://www.youtube.com/@nataliebrunell", kit)
 828 |          self.assertTrue(kit.endswith("credits: @YahooFinance @nataliebrunell\n\U0001F9E1"), kit[-80:])
 829 | -        _, sent_opt = self.deliver(rd, option="B")
 830 | -        self.assertNotIn("message", [s[0] for s in sent_opt])         # transition options carry no kit
 831 |  
 832 | -    def test_the_caption_carries_the_duration(self):
 833 | -        rd = self.run_dir()
 834 | -        _, sent = self.deliver(rd)
 835 | -        self.assertIn(" s", sent[0][2]["caption"].split("\n")[1])
 836 | +
 837 | +class TestNothingIsSentUnlessAuthorised(Base):
 838 | +    def refused(self, rd, label):
 839 | +        sent = []
 840 | +        with self.assertRaises(RuntimeError, msg=label):
 841 | +            TG.deliver_run(rd, send=lambda k, p, f: sent.append(k) or 1)
 842 | +        self.assertEqual(sent, [], label)
 843 | +
 844 | +    def test_a_failing_row_a_waiver_string_an_incomplete_pack_or_no_attestation_send_nothing(self):
 845 | +        for fmt, row, v in (("9x16", "G4s_layout_truth", "FAIL"), ("16x9", "G8_sharpness", "FLAG/LIMITED (soft)"),
 846 | +                            ("16x9", "G17_onset_tail", "PASS (L-c)")):
 847 | +            rows = passing_rows()
 848 | +            rows[fmt][row] = v
 849 | +            self.refused(make_run(self.tmp, rows=rows), f"{row} = {v}")
 850 | +        rd = make_run(self.tmp, attest=False)
 851 | +        edit_json(os.path.join(rd, "VERIFY", "VERIFICATION.json"), lambda d: d.__setitem__("complete", False))
 852 | +        RA.attest(rd, {"ok": True, "why": []})
 853 | +        self.refused(rd, "incomplete pack")
 854 | +        self.refused(make_run(self.tmp, attest=False), "no attestation")
 855 | +
 856 | +    def test_a_final_changed_after_authorisation_is_refused_before_it_is_sent(self):
 857 | +        rd = make_run(self.tmp)
 858 | +        real = TG._plan
 859 | +
 860 | +        def plan_then_tamper(*a, **k):                  # the 9:16 changes between authorise and its send
 861 | +            p = real(*a, **k)
 862 | +            with open(os.path.join(rd, "out", "segment_vertical.mp4"), "ab") as f:
 863 | +                f.write(b"\0")
 864 | +            return p
 865 | +        TG._plan = plan_then_tamper
 866 | +        try:
 867 | +            sent = []
 868 | +            with self.assertRaises(RuntimeError) as cm:
 869 | +                TG.deliver_run(rd, send=lambda k, p, f: sent.append(os.path.basename(p)) or 1)
 870 | +        finally:
 871 | +            TG._plan = real
 872 | +        self.assertIn("changed after it was authorised", str(cm.exception))
 873 | +        self.assertEqual(sent, ["segment.mp4"])
 874 | +
 875 | +    def test_wrong_dimensions_or_an_oversize_final_stop_before_the_first_send(self):
 876 | +        rd = make_run(self.tmp, attest=False)
 877 | +        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=24:d=1",
 878 | +                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
 879 | +                        os.path.join(rd, "out", "segment.mp4")], check=True)
 880 | +        m = os.path.join(rd, "GATE_REPORT.json")
 881 | +        edit_json(m, lambda d: d["measured_files"].__setitem__("out/segment.mp4", RA.sha256(os.path.join(rd, "out", "segment.mp4"))))
 882 | +        RA.attest(rd, {"ok": True, "why": []})
 883 | +        self.refused(rd, "1280x720 16:9 final")
 884 | +        rd = make_run(self.tmp)
 885 | +        saved = TG.VIDEO_MAX_BYTES
 886 | +        TG.VIDEO_MAX_BYTES = 10
 887 | +        try:
 888 | +            self.refused(rd, "oversize final")
 889 | +        finally:
 890 | +            TG.VIDEO_MAX_BYTES = saved
 891 | +
 892 | +    def test_a_headline_number_the_video_does_not_say_stops_the_drop(self):
 893 | +        edl = json.load(open(os.path.join(make_run(self.tmp, attest=False), "edl.json")))
 894 | +        edl["headline"] = "Bitcoin falls to $74,000 on November 8th"       # E-FAIL-038's invented date
 895 | +        self.refused(make_run(self.tmp, edl=edl), "headline date not said")
 896 | +        edl["headline"] = "Bitcoin falls to $74,000"                         # said in the hook's lock
 897 | +        self.assertEqual(TG.headline_numbers_said(make_run(self.tmp, edl=edl)), [])
 898 | +
 899 | +
 900 | +class TestCheckpoint(Base):
 901 | +    def test_a_refused_send_resumes_without_duplicates(self):
 902 | +        rd = make_run(self.tmp)
 903 | +        with self.assertRaises(TG.SendRejected):
 904 | +            self.deliver(rd, fail_at=1, exc=TG.SendRejected("429 Too Many Requests"))
 905 | +        rec = json.load(open(os.path.join(rd, "TELEGRAM_DELIVERY.json")))
 906 | +        self.assertEqual([m["key"] for m in rec["messages"]], ["video:16x9"])
 907 | +        self.assertEqual(rec["status"], "in_progress")
 908 | +        _, sent = self.deliver(rd)                      # resumes after the 16:9
 909 | +        self.assertEqual(sent[0][1], "segment_vertical.mp4")
 910 | +        self.assertNotIn("segment.mp4", [s[1] for s in sent])
 911 | +        with self.assertRaises(RuntimeError) as cm:     # a complete drop is never repeated
 912 | +            self.deliver(rd)
 913 | +        self.assertIn("already delivered", str(cm.exception))
 914 | +
 915 | +    def test_an_unknown_outcome_is_never_resent_automatically(self):
 916 | +        rd = make_run(self.tmp)
 917 | +        with self.assertRaises(RuntimeError):
 918 | +            self.deliver(rd, fail_at=2, exc=RuntimeError("STOP: Telegram sendPhoto: outcome unknown (ReadTimeout)"))
 919 | +        rec = json.load(open(os.path.join(rd, "TELEGRAM_DELIVERY.json")))
 920 | +        self.assertEqual(rec["unknown"], ["sheet:16x9"])
 921 | +        with self.assertRaises(RuntimeError) as cm:
 922 | +            self.deliver(rd)
 923 | +        self.assertIn("outcome unknown", str(cm.exception))
 924 | +
 925 | +    def test_the_sender_never_puts_the_token_in_an_error(self):
 926 | +        import types
 927 | +        from unittest import mock
 928 | +        relay = types.ModuleType("relay")
 929 | +        relay.get_key = lambda name: "SECRET-" + name
 930 | +        import requests
 931 | +
 932 | +        def boom(url, **kw):
 933 | +            raise requests.ConnectionError(f"HTTPSConnectionPool: Max retries exceeded with url: {url}")
 934 | +        with mock.patch.dict(sys.modules, {"relay": relay}), mock.patch.object(requests, "post", boom):
 935 | +            with self.assertRaises(RuntimeError) as cm:
 936 | +                TG._send_bot_api("message", "", {"text": "x"})
 937 | +        self.assertNotIn("SECRET", str(cm.exception))
 938 | +        self.assertIn("outcome unknown", str(cm.exception))
 939 | +
 940 | +
 941 | +class TestLimits(unittest.TestCase):
 942 | +    def test_caption_fits_including_its_marker(self):
 943 | +        self.assertEqual(len(TG._fit("x" * 5000, TG.CAPTION_MAX)), TG.CAPTION_MAX)
 944 | +        self.assertEqual(TG._fit("short", TG.CAPTION_MAX), "short")
 945 |  
 946 |      def test_photo_limits_at_their_boundaries(self):
 947 |          """Audit M1: size (PHOTO_MAX_BYTES), width + height (10000) and aspect ratio (20) boundaries."""
 948 | @@ -157,11 +223,10 @@ class TestDelivery(unittest.TestCase):
 949 |          open(bad, "wb").write(b"\xff\xd8\xff")                          # not an image: document, not a crash
 950 |          self.assertFalse(TG._photo_ok(bad))
 951 |  
 952 | -    def test_wrong_dimensions_stop(self):
 953 | -        rd = self.run_dir()
 954 | -        shutil.copy(os.path.join(self.media, "wrong.mp4"), os.path.join(rd, "out", "segment.mp4"))
 955 | -        with self.assertRaises(RuntimeError):
 956 | -            self.deliver(rd)
 957 | +    def test_the_legacy_entry_point_is_gone(self):
 958 | +        with self.assertRaises(RuntimeError) as cm:
 959 | +            TG.send_telegram_preview("/tmp/whatever")
 960 | +        self.assertIn("removed", str(cm.exception))
 961 |  
 962 |  
 963 |  if __name__ == "__main__":
 964 | diff --git a/pipeline/test_visual_check.py b/pipeline/test_visual_check.py
 965 | index 622b4751..e0e92ce6 100644
 966 | --- a/pipeline/test_visual_check.py
 967 | +++ b/pipeline/test_visual_check.py
 968 | @@ -219,16 +219,38 @@ class TestSheetWiring(unittest.TestCase):
 969 |                  mock.patch.object(V, "boundary_check", side_effect=AssertionError("cuts asked")):
 970 |              verify_pack._sheets_and_checklist(rd, rep, pack, vision=True)     # out/ finals do not exist
 971 |          ask.assert_not_called()
 972 | +        out = json.load(open(os.path.join(rd, "GATE_REPORT.json")))       # V1 lands in the report ON DISK
 973 |          for fmt in ("16x9", "9x16"):
 974 |              self.assertFalse(os.path.exists(os.path.join(rd, "qa", f"contact_sheet_{fmt}.jpg")))
 975 | -            self.assertTrue(rep["rows"][fmt]["V1_visual_checklist"].startswith("FAIL (no contact sheet"),
 976 | -                            rep["rows"][fmt]["V1_visual_checklist"])
 977 | +            self.assertEqual(out["rows"][fmt]["V1_visual_checklist"], "FAIL")       # exact verdict, reason in notes
 978 | +            self.assertTrue(out["notes"][fmt]["V1_visual_checklist"].startswith("no contact sheet"),
 979 | +                            out["notes"][fmt]["V1_visual_checklist"])
 980 | +
 981 | +
 982 | +class TestPackArtefacts(unittest.TestCase):
 983 | +    def test_a_sheet_with_any_missing_frame_is_no_sheet_and_a_failed_frame_never_reuses_an_old_file(self):
 984 | +        """GPT-gates F09 / F10: a partial sheet is not a sheet; a frame ffmpeg could not grab is None, even when a
 985 | +        file of that name is left from an earlier render."""
 986 | +        import verify_pack
 987 | +        from PIL import Image
 988 | +        tmp = tempfile.mkdtemp(prefix="pack_")
 989 | +        self.addCleanup(shutil.rmtree, tmp, True)
 990 | +        p = os.path.join(tmp, "a.jpg")
 991 | +        Image.new("RGB", (64, 36)).save(p)
 992 | +        self.assertIsNone(verify_pack._sheet([("a", p), ("b", None)], os.path.join(tmp, "s.jpg"), 64))
 993 | +        self.assertIsNone(verify_pack._sheet([], os.path.join(tmp, "s.jpg"), 64))
 994 | +        self.assertTrue(verify_pack._sheet([("a", p)], os.path.join(tmp, "s.jpg"), 64))
 995 | +        stale = os.path.join(tmp, "stale.jpg")
 996 | +        Image.new("RGB", (64, 36)).save(stale)
 997 | +        self.assertIsNone(verify_pack._frame(os.path.join(tmp, "missing.mp4"), 1.0, stale))
 998 | +        self.assertFalse(os.path.exists(stale))
 999 |  
1000 |  
1001 |  class TestCutWiring(unittest.TestCase):
1002 |      """The next-shot line is answered one cut at a time; the whole-sheet answer is advisory."""
1003 |  
1004 | -    def wire(self, sheet_next, cuts_ok):
1005 | +    def wire(self, sheet_next, cuts_ok, per=None, shots=None, vision=True):
1006 | +        """V1 rows + notes as written into GATE_REPORT.json, with the panel / shots / cuts injected."""
1007 |          from unittest import mock
1008 |          import verify_pack
1009 |          rd = tempfile.mkdtemp(prefix="cutwire_")
1010 | @@ -237,25 +259,60 @@ class TestCutWiring(unittest.TestCase):
1011 |          json.dump({"hook": {"channel": "A", "vertical_layout": {"shots": [], "flagged": False}}, "clips": []},
1012 |                    open(os.path.join(rd, "edl.json"), "w"))
1013 |          for fmt in ("16x9", "9x16"):
1014 | -            json.dump({"segments": [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 4.0}]},
1015 | +            json.dump({"segments": [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 4.0},
1016 | +                                    {"label": "outro", "type": "outro", "start": 4.0, "end": 8.0}]},
1017 |                        open(os.path.join(rd, "qa", f"concat_manifest_{fmt}.json"), "w"))
1018 | +        json.dump({"rows": {}}, open(os.path.join(rd, "GATE_REPORT.json"), "w"))
1019 |          rows = {k: {"answer": "yes", "why": "w", "ok": True} for k, _ in V.CHECKLIST}
1020 |          rows[verify_pack.NEXT_SHOT] = {"answer": sheet_next, "why": "w", "ok": sheet_next == "yes"}
1021 | +        per = per if per is not None else {m: {"rows": dict(rows), "raw": {}} for m in V.VISION_MODELS}
1022 | +        shots = shots if shots is not None else [{"label": "hook", "shot": 0, "ok": True}]
1023 | +        cut = {"boundary": "hook|outro", "ok": cuts_ok}
1024 |          rep, pack = {"rows": {}}, {}
1025 |          with mock.patch.object(V, "contact_sheet", return_value={"path": "s.jpg"}), \
1026 | -                mock.patch.object(V, "ask_panel", return_value=(sheet_next == "yes", {"m": {"rows": rows, "raw": {}}})), \
1027 | +                mock.patch.object(V, "ask_panel", return_value=(sheet_next == "yes", per)), \
1028 |                  mock.patch.object(V, "shot_frames", return_value=[]), \
1029 | -                mock.patch.object(V, "letterbox_check", return_value=(True, [])), \
1030 | +                mock.patch.object(V, "letterbox_check", return_value=(all(x["ok"] for x in shots), shots)), \
1031 |                  mock.patch.object(V, "boundary_pairs", return_value=[]), \
1032 | -                mock.patch.object(V, "boundary_check",
1033 | -                                  return_value=(cuts_ok, [] if cuts_ok else [{"boundary": "hook|clip_01", "ok": False}])):
1034 | -            verify_pack._sheets_and_checklist(rd, rep, pack, vision=True)
1035 | -        return rep["rows"]
1036 | +                mock.patch.object(V, "boundary_check", return_value=(cuts_ok, [cut])):
1037 | +            verify_pack._sheets_and_checklist(rd, rep, pack, vision=vision)
1038 | +        out = json.load(open(os.path.join(rd, "GATE_REPORT.json")))
1039 | +        return out["rows"], out.get("notes", {}), out.get("evidence", {})
1040 |  
1041 |      def test_the_cut_check_decides_the_next_shot_line(self):
1042 | -        self.assertEqual(self.wire("no", True)["16x9"]["V1_visual_checklist"], "PASS")     # sheet answer advisory
1043 | -        r = self.wire("yes", False)["9x16"]["V1_visual_checklist"]
1044 | -        self.assertTrue(r.startswith("FAIL") and "next shot before the cut: hook|clip_01" in r, r)
1045 | +        rows, _, ev = self.wire("no", True)
1046 | +        self.assertEqual(rows["16x9"]["V1_visual_checklist"], "PASS")     # sheet answer advisory
1047 | +        self.assertGreaterEqual(ev["16x9"]["V1_visual_checklist"]["samples"], 1)
1048 | +        rows, notes, _ = self.wire("yes", False)
1049 | +        self.assertEqual(rows["9x16"]["V1_visual_checklist"], "FAIL")
1050 | +        self.assertIn("next shot before the cut: hook|outro", notes["9x16"]["V1_visual_checklist"])
1051 | +
1052 | +    def test_an_empty_or_partial_panel_is_never_a_pass(self):
1053 | +        """GPT-gates F07 / Claude-gates M1: one model missing, a model that answered nothing, a line missing,
1054 | +        a truthy string for ok: each FAILS V1."""
1055 | +        import verify_pack
1056 | +        full = {k: {"answer": "yes", "why": "w", "ok": True} for k, _ in V.CHECKLIST}
1057 | +        one = V.VISION_MODELS[0]
1058 | +        cases = {"one model only": {one: {"rows": full}},
1059 | +                 "a model answered nothing": {m: {"rows": full if m == one else {}} for m in V.VISION_MODELS},
1060 | +                 "a line missing": {m: {"rows": {k: r for k, r in full.items() if k != "watermark_present"}}
1061 | +                                    for m in V.VISION_MODELS},
1062 | +                 "ok is a string": {m: {"rows": {**full, "watermark_present": {"answer": "yes", "ok": "true"}}}
1063 | +                                    for m in V.VISION_MODELS},
1064 | +                 "no panel": {}}
1065 | +        for name, per in cases.items():
1066 | +            self.assertFalse(verify_pack.panel_ok(per), name)
1067 | +            rows, _, _ = self.wire("no", True, per=per)
1068 | +            self.assertEqual(rows["16x9"]["V1_visual_checklist"], "FAIL", name)
1069 | +        self.assertTrue(verify_pack.panel_ok({m: {"rows": full} for m in V.VISION_MODELS}))
1070 | +
1071 | +    def test_no_shots_asked_and_vision_off_are_never_a_pass(self):
1072 | +        rows, _, _ = self.wire("no", True, shots=[])                     # zero letterbox frames (Claude-gates M2)
1073 | +        self.assertEqual(rows["9x16"]["V1_visual_checklist"], "FAIL")
1074 | +        rows, notes, ev = self.wire("no", True, vision=False)            # GPT-gates F08: a waiver switch leaves a trace
1075 | +        for fmt in ("16x9", "9x16"):
1076 | +            self.assertEqual(rows[fmt]["V1_visual_checklist"], "SKIPPED")
1077 | +            self.assertEqual(ev[fmt]["V1_visual_checklist"], {"executed": False, "samples": 0})
1078 |  
1079 |  
1080 |  def _has_vision_key():
1081 | @@ -300,5 +357,34 @@ class TestVisionMustFail(unittest.TestCase):
1082 |          self.assertTrue(ok, rows)
1083 |  
1084 |  
1085 | +
1086 | +@unittest.skipUnless(_has_vision_key(), "Heimdall vision route key not available")
1087 | +class TestVisionMustPass(unittest.TestCase):
1088 | +    """Addendum '22:15' item 4: V1's REAL PASSING fixture. The PBX-approved preview (references/
1089 | +    pulse_preview_2026-11-11, read only) passes the whole V1 row in both formats with the current code: the sheet
1090 | +    checklist from every vision model, the letterbox per shot (9:16) and the next shot per cut. Its failing
1091 | +    fixtures are TestVisionMustFail; its missing-evidence answer is TestCutWiring / TestSheetWiring."""
1092 | +
1093 | +    def test_the_approved_preview_passes_v1_in_both_formats(self):
1094 | +        import verify_pack
1095 | +        ref = os.path.join(REPO, "references", "pulse_preview_2026-11-11")
1096 | +        self.assertTrue(os.path.isfile(os.path.join(ref, "out", "segment.mp4")), f"must-pass fixture missing: {ref}")
1097 | +        rd = tempfile.mkdtemp(prefix="v1pass_")
1098 | +        self.addCleanup(shutil.rmtree, rd, True)
1099 | +        for sub in ("out", "qa"):
1100 | +            os.makedirs(os.path.join(rd, sub))
1101 | +        for rel in ("out/segment.mp4", "out/segment_vertical.mp4"):
1102 | +            os.symlink(os.path.join(ref, rel), os.path.join(rd, rel))           # read only: ffmpeg reads them
1103 | +        for rel in ("edl.json", "VERTICAL_LAYOUT.json", "qa/concat_manifest_16x9.json", "qa/concat_manifest_9x16.json"):
1104 | +            shutil.copy(os.path.join(ref, rel), os.path.join(rd, rel))
1105 | +        json.dump({"rows": {}}, open(os.path.join(rd, "GATE_REPORT.json"), "w"))
1106 | +        pack = {}
1107 | +        verify_pack._sheets_and_checklist(rd, {}, pack, vision=True)
1108 | +        out = json.load(open(os.path.join(rd, "GATE_REPORT.json")))
1109 | +        for fmt in ("16x9", "9x16"):
1110 | +            self.assertEqual(out["rows"][fmt]["V1_visual_checklist"], "PASS",
1111 | +                             f"{fmt}: {out.get('notes', {}).get(fmt)} | " + json.dumps(pack["visual"].get(fmt), default=str)[:3000])
1112 | +
1113 | +
1114 |  if __name__ == "__main__":
1115 |      unittest.main()
1116 | diff --git a/pipeline/verify_pack.py b/pipeline/verify_pack.py
1117 | index 113ca816..daf11e9b 100644
1118 | --- a/pipeline/verify_pack.py
1119 | +++ b/pipeline/verify_pack.py
1120 | @@ -9,7 +9,10 @@ What a reviewer checks by eye, produced for every run before any delivery and at
1121 |    4. sheets  (orchestrator 06:20 ET) qa/contact_sheet_<fmt>.jpg: the timestamped contact sheet of the finished
1122 |               video (visual_check.contact_sheet), and the fixed visual checklist answered FROM the sheet by the
1123 |               Heimdall vision panel (visual_check.ask_panel); any "no" or no answer = row V1_visual_checklist FAIL.
1124 | -VERIFY/VERIFICATION.json records every artefact; `complete` is True only when all of them exist.
1125 | +VERIFY/VERIFICATION.json records every artefact; `complete` is True only when all of them exist (every requested
1126 | +frame, both G18 tables, both credits sheets, both contact sheets), and `passed` only when the pack is complete,
1127 | +built WITH the vision check, and the visual verdict of both formats is exactly True (red-team A: a pack without
1128 | +the vision check, a model that answered nothing, a missing frame are never a pass; release_auth reads this).
1129 |  """
1130 |  import json
1131 |  import os
1132 | @@ -19,6 +22,8 @@ FPS = 24
1133 |  
1134 |  
1135 |  def _frame(video, t, out):
1136 | +    if os.path.exists(out):                          # never let a frame of an earlier render stand in (GPT-gates F10)
1137 | +        os.remove(out)
1138 |      try:
1139 |          subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1",
1140 |                          "-q:v", "3", out], check=True, timeout=60)
1141 | @@ -28,11 +33,12 @@ def _frame(video, t, out):
1142 |  
1143 |  
1144 |  def _sheet(items, out, tile_w):
1145 | -    """items: [(label, path)] -> one labelled grid image (3 per row)."""
1146 | +    """items: [(label, path)] -> one labelled grid image (3 per row); None when ANY requested frame is missing
1147 | +    (GPT-gates F09: a partial sheet is not a sheet)."""
1148 |      from PIL import Image, ImageDraw
1149 | -    ims = [(lab, Image.open(p).convert("RGB")) for lab, p in items if p]
1150 | -    if not ims:
1151 | +    if not items or any(not p for _, p in items):
1152 |          return None
1153 | +    ims = [(lab, Image.open(p).convert("RGB")) for lab, p in items]
1154 |      th = int(round(ims[0][1].height * tile_w / ims[0][1].width))
1155 |      cols = 3
1156 |      rows = (len(ims) + cols - 1) // cols
1157 | @@ -51,7 +57,7 @@ def build(run_dir, vision=True):
1158 |      os.makedirs(vdir, exist_ok=True)
1159 |      with open(os.path.join(run_dir, "GATE_REPORT.json")) as f:
1160 |          rep = json.load(f)
1161 | -    pack = {"words": rep.get("G18"), "joins": {}, "credits": {"G12": {}, "G15": {}}}
1162 | +    pack = {"words": rep.get("G18"), "joins": {}, "credits": {"G12": {}, "G15": {}}, "vision": bool(vision)}
1163 |      for fmt, final, tile in (("16x9", "segment.mp4", 480), ("9x16", "segment_vertical.mp4", 270)):
1164 |          final = os.path.join(run_dir, "out", final)
1165 |          with open(os.path.join(run_dir, "qa", f"concat_manifest_{fmt}.json")) as f:
1166 | @@ -69,7 +75,7 @@ def build(run_dir, vision=True):
1167 |                                _frame(final, t, os.path.join(vdir, f"join_{fmt}_{tag}_{name}.jpg"))))
1168 |          pack["joins"][fmt] = {"frames": [p for _, p in items], "sheet": _sheet(
1169 |              items, os.path.join(vdir, f"joins_{fmt}.jpg"), tile)}
1170 | -        sh = next((s for s in segs if s["label"] == "shoutout"), None)
1171 | +        sh = next((s for s in segs if s.get("type") == "shoutout"), None)     # by type, as the gates (V7)
1172 |          if sh:
1173 |              c_items = [(f"{fmt} credits {t:.2f}s", _frame(final, t, os.path.join(vdir, f"credits_{fmt}_{k}.jpg")))
1174 |                         for k, t in enumerate((sh["start"] + 1.0, (sh["start"] + sh["end"]) / 2, sh["end"] - 0.5))]
1175 | @@ -81,14 +87,33 @@ def build(run_dir, vision=True):
1176 |              [pack["credits"].get(f, {}).get("sheet") for f in ("16x9", "9x16")]
1177 |      credits_rows = [pack["credits"][g].get(f) for g in ("G12", "G15") for f in ("16x9", "9x16")]
1178 |      _sheets_and_checklist(run_dir, rep, pack, vision)
1179 | -    pack["complete"] = bool(pack["words"]) and all(p and os.path.exists(p) for p in files) \
1180 | +    words = pack["words"] if isinstance(pack["words"], dict) else {}
1181 | +    pack["complete"] = all(isinstance(words.get(f), list) and words[f] for f in ("16x9", "9x16")) \
1182 | +        and all(p and os.path.exists(p) for p in files) \
1183 |          and all(r is not None for r in credits_rows) \
1184 |          and all(os.path.exists((pack["contact_sheets"].get(f) or {}).get("path") or "") for f in ("16x9", "9x16"))
1185 | -    with open(os.path.join(vdir, "VERIFICATION.json"), "w") as f:
1186 | +    pack["passed"] = pack["complete"] is True and pack["vision"] is True and \
1187 | +        all((pack["visual"].get(f) or {}).get("ok") is True for f in ("16x9", "9x16"))
1188 | +    tmp = os.path.join(vdir, "VERIFICATION.json.tmp")
1189 | +    with open(tmp, "w") as f:
1190 |          json.dump(pack, f, indent=2, default=str)
1191 | +    os.replace(tmp, os.path.join(vdir, "VERIFICATION.json"))
1192 |      return pack
1193 |  
1194 |  
1195 | +def panel_ok(per):
1196 | +    """The panel passed the sheet: EVERY vision model answered EVERY checklist line (the whole-sheet next-shot
1197 | +    line is advisory, asked per cut instead) and every answer is exactly ok True (GPT-gates F07, Claude-gates
1198 | +    M1: a model that answered nothing, a missing line, a truthy string are never a pass)."""
1199 | +    import visual_check as VC
1200 | +    keys = [k for k, _ in VC.CHECKLIST if k != NEXT_SHOT]
1201 | +    if not isinstance(per, dict) or set(per) != set(VC.VISION_MODELS):
1202 | +        return False
1203 | +    return all(isinstance(d, dict) and isinstance(d.get("rows"), dict) and
1204 | +               all(isinstance(d["rows"].get(k), dict) and d["rows"][k].get("ok") is True for k in keys)
1205 | +               for d in per.values())
1206 | +
1207 | +
1208 |  NEXT_SHOT = "no_next_shot_before_transition"
1209 |  
1210 |  
1211 | @@ -104,6 +129,7 @@ def _sheets_and_checklist(run_dir, rep, pack, vision):
1212 |      channels_note = ("Channels whose clips appear in this video (from the edit decision list): " +
1213 |                       ", ".join(f"{s.get('channel')} ({label})" for label, s in segs_edl) + ".")
1214 |      pack["contact_sheets"], pack["visual"] = {}, {}
1215 | +    v1_rows = {}                                        # fmt -> (exact verdict, note, answers counted)
1216 |      for fmt, final in (("16x9", "segment.mp4"), ("9x16", "segment_vertical.mp4")):
1217 |          with open(os.path.join(run_dir, "qa", f"concat_manifest_{fmt}.json")) as f:
1218 |              segs = json.load(f)["segments"]
1219 | @@ -115,7 +141,8 @@ def _sheets_and_checklist(run_dir, rep, pack, vision):
1220 |                                                             os.path.join(run_dir, "VERIFY", f"sheet_{fmt}"))
1221 |          except Exception as e:                          # no sheet = incomplete pack and a failing V1 row
1222 |              pack["contact_sheets"][fmt] = {"error": f"{type(e).__name__}: {e}"}
1223 | -        if not vision:
1224 | +        if not vision:                                   # the vision check is off: V1 did not run (never a pass)
1225 | +            v1_rows[fmt] = ("SKIPPED", "vision check off for this pack", 0)
1226 |              continue
1227 |          if "error" in pack["contact_sheets"][fmt]:
1228 |              pack["visual"][fmt] = {"ok": False, "error": f"no contact sheet: {pack['contact_sheets'][fmt]['error']}"}
1229 | @@ -125,7 +152,7 @@ def _sheets_and_checklist(run_dir, rep, pack, vision):
1230 |                                         channels_note=channels_note)
1231 |                  # the next-shot line is answered one cut at a time (below); the whole-sheet answer stays as
1232 |                  # advisory text (run 6: it misread tile labels and missed the real defect)
1233 | -                ok = bool(per) and all(r["ok"] for d in per.values() for k, r in d["rows"].items() if k != NEXT_SHOT)
1234 | +                ok = panel_ok(per)
1235 |                  pack["visual"][fmt] = {"ok": ok, "per_model": per,
1236 |                                         "sheet_next_shot_advisory": {m: d["rows"].get(NEXT_SHOT) for m, d in per.items()}}
1237 |              except Exception as e:
1238 | @@ -139,16 +166,18 @@ def _sheets_and_checklist(run_dir, rep, pack, vision):
1239 |                      os.path.join(run_dir, "out", final), segs, layout, os.path.join(run_dir, "VERIFY", "shots_9x16")))
1240 |              except Exception as e:
1241 |                  lb_ok, lb_rows = False, [{"error": f"{type(e).__name__}: {e}"}]
1242 | +            lb_ok = lb_ok is True and bool(lb_rows)            # zero shots asked is no answer (Claude-gates M2)
1243 |              v["letterbox_per_shot"] = {"ok": lb_ok, "shots": lb_rows}
1244 | -            v["ok"] = v["ok"] and lb_ok
1245 | +            v["ok"] = v["ok"] is True and lb_ok
1246 |          if "error" not in pack["contact_sheets"][fmt]:
1247 |              try:                                        # next shot before a cut: ONE pair of frames per cut
1248 |                  bd_ok, bd_rows = VC.boundary_check(VC.boundary_pairs(
1249 |                      os.path.join(run_dir, "out", final), segs, os.path.join(run_dir, "VERIFY", f"cuts_{fmt}")))
1250 |              except Exception as e:
1251 |                  bd_ok, bd_rows = False, [{"error": f"{type(e).__name__}: {e}"}]
1252 | +            bd_ok = bd_ok is True and len(bd_rows) == max(0, len(segs) - 1) and bool(bd_rows)   # every cut asked
1253 |              v["boundaries"] = {"ok": bd_ok, "cuts": bd_rows}
1254 | -            v["ok"] = v["ok"] and bd_ok
1255 | +            v["ok"] = v["ok"] is True and bd_ok
1256 |          nos = sorted({k for d in (v.get("per_model") or {}).values() for k, r in (d.get("rows") or {}).items()
1257 |                        if not r.get("ok") and k != NEXT_SHOT})
1258 |          if not (v.get("boundaries") or {"ok": True})["ok"]:
1259 | @@ -158,9 +187,25 @@ def _sheets_and_checklist(run_dir, rep, pack, vision):
1260 |              bad = [f"{r.get('label')}#{r.get('shot')}" for r in v["letterbox_per_shot"]["shots"] if not r.get("ok")]
1261 |              nos.append(f"letterbox per shot: {', '.join(bad)}")
1262 |          why = "; ".join(x for x in (v.get("error"), ("no/missing: " + ", ".join(nos)) if nos else None) if x)
1263 | -        rep.setdefault("rows", {}).setdefault(fmt, {})["V1_visual_checklist"] = \
1264 | -            "PASS" if v["ok"] else f"FAIL ({why or 'no answer'})"
1265 | +        answered = sum(len(d.get("rows") or {}) for d in (v.get("per_model") or {}).values()) + \
1266 | +            len((v.get("letterbox_per_shot") or {}).get("shots") or []) + len((v.get("boundaries") or {}).get("cuts") or [])
1267 | +        v1_rows[fmt] = ("PASS", None, answered) if v["ok"] is True else ("FAIL", why or "no answer", answered)
1268 | +    # V1 joins the report: re-read NOW (never rewrite a snapshot taken minutes ago) and replace atomically
1269 | +    path = os.path.join(run_dir, "GATE_REPORT.json")
1270 | +    with open(path) as f:
1271 | +        cur = json.load(f)
1272 | +    for fmt, (verdict, note, n) in v1_rows.items():
1273 | +        cur.setdefault("rows", {}).setdefault(fmt, {})["V1_visual_checklist"] = verdict
1274 | +        cur.setdefault("evidence", {}).setdefault(fmt, {})["V1_visual_checklist"] = \
1275 | +            {"executed": verdict != "SKIPPED", "samples": n}
1276 | +        notes = cur.setdefault("notes", {}).setdefault(fmt, {})
1277 | +        if note:
1278 | +            notes["V1_visual_checklist"] = note
1279 | +        else:
1280 | +            notes.pop("V1_visual_checklist", None)
1281 |      if vision:
1282 | -        rep["V1"] = pack["visual"]
1283 | -        with open(os.path.join(run_dir, "GATE_REPORT.json"), "w") as f:
1284 | -            json.dump(rep, f, indent=2, default=str)
1285 | +        cur["V1"] = pack["visual"]
1286 | +    tmp = path + ".tmp"
1287 | +    with open(tmp, "w") as f:
1288 | +        json.dump(cur, f, indent=2, default=str)
1289 | +    os.replace(tmp, path)
1290 | 
```

---

## YOUR REVIEW TASK: PULSE CHECK SENTENCE LAW / ONSET / CREDITS (Python pipeline, no UI, no DB)

The only file is the exact staged diff of ONE commit. Review that diff, nothing else.
Only state what you can verify from the diff shown. If uncertain, say so. Do not guess. Cite diff lines.

### Q1: CORRECTNESS
Does each changed function do what its docstring and the laws above say? Off-by-one in time/index
handling, wrong units (seconds vs ms), wrong comparisons, silent exceptions, state that leaks between
clips. Can any path produce a PASS (or a cut, a lock, a window) when data is missing or a model failed?

### Q2: LAW COMPLIANCE
For each law above: COMPLIANT / VIOLATION / PARTIAL with the diff line. In particular: can a cut move
outside the locked sentence's silence, can expected words be recomputed after selection, can a gate
threshold have been loosened, can the v2f reference path behave differently?

### Q3: TESTS
Do the tests prove the claim (must-fail fixtures FAIL for the right reason; controls PASS for the right
reason)? Any assertion that could pass vacuously?

### Q4: VERDICT
List every defect as: SEVERITY | diff line | issue | fix. End with READY or NOT READY.

