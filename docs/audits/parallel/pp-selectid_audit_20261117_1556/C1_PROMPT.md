# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261117_1556
# Branch: pp-selectid
# Generated: 2026-11-17 15:56 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261117_1556/C1_STEP.diff (255 lines)
```
   1 | diff --git a/pipeline/transcript_truth.py b/pipeline/transcript_truth.py
   2 | index 02f1207..ce4edcd 100644
   3 | --- a/pipeline/transcript_truth.py
   4 | +++ b/pipeline/transcript_truth.py
   5 | @@ -29,6 +29,41 @@ PAUSE_MIN_S = 0.700          # ruling 38: a measured pause this long with no rec
   6 |  CANON_RUN = 6                # recogniser words read together at an edge, so a spoken number is one canonical token
   7 |  
   8 |  
   9 | +MIN_SECTION_SHARE = 0.5   # RULING 142 (3) on this side: a fetched section under half its window's length is empty
  10 | +POST_LIVE_CACHE = "/home/ultron/protocol_pulse/data/post_live_cache"   # the integrator's whole streams (batch 111;
  11 | +#   read only): <video_id>/audio.m4a (format 140) and video.mp4 (137), used first when they hold media
  12 | +WHOLE = {"audio": ("audio.m4a", "bestaudio[acodec^=mp4a]/bestaudio")}   # the integrator's audio format (15:5x ET)
  13 | +
  14 | +
  15 | +def media_seconds(path):
  16 | +    """A media file's duration in seconds (ffprobe); 0.0 when it has none or cannot be read (a post_live stream's section
  17 | +    download gives a file of 0 s: MeC8YEmUx_w, 15:5x ET Nov 17, 258 bytes)."""
  18 | +    try:
  19 | +        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
  20 | +                             capture_output=True, text=True, timeout=60).stdout.strip()
  21 | +        return float(out or 0.0)
  22 | +    except (OSError, ValueError, subprocess.SubprocessError):
  23 | +        return 0.0
  24 | +
  25 | +
  26 | +def whole_stream(video_id, fmt, out_dir, tag):
  27 | +    """RULING 142 (3) on this side (the integrator's batch 111 does the same for the render): a post_live YouTube stream
  28 | +    (DASH segments only) gives an EMPTY section download, so its whole stream in `fmt` is fetched ONCE per video and tag,
  29 | +    kept in out_dir as <video_id>.whole-<tag>.<ext>, and every window is cut from it locally. -> the file's path."""
  30 | +    theirs = os.path.join(POST_LIVE_CACHE, video_id, {"audio": "audio.m4a", "video": "video.mp4"}.get(tag, "-"))
  31 | +    if os.path.isfile(theirs) and media_seconds(theirs) > 0:   # the integrator's copy of the same stream: read only
  32 | +        return theirs
  33 | +    stem = f"{video_id}.whole-{tag}"
  34 | +    find = lambda: [f for f in sorted(os.listdir(out_dir)) if os.path.splitext(f)[0] == stem]
  35 | +    if not find():
  36 | +        subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", fmt, "-o", os.path.join(out_dir, stem + ".%(ext)s"),
  37 | +                        f"https://www.youtube.com/watch?v={video_id}"], check=True, timeout=1800, capture_output=True)
  38 | +    have = find()
  39 | +    if not have:
  40 | +        raise OSError(f"the whole stream of {video_id} ({fmt}) was not fetched")
  41 | +    return os.path.join(out_dir, have[0])
  42 | +
  43 | +
  44 |  def audio_window(video_id, start, end, out_dir, pad=PAD_S, pad_before=PAD_BEFORE_S):
  45 |      """WAV (16 kHz mono) of [start - pad_before, end + pad] (clamped at the video head), fetched with yt-dlp's
  46 |      download sections -> (path, the window's real start in video seconds)."""
  47 | @@ -42,8 +77,17 @@ def audio_window(video_id, start, end, out_dir, pad=PAD_S, pad_before=PAD_BEFORE
  48 |      subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", "bestaudio", "--download-sections", f"*{a:.2f}-{b:.2f}",
  49 |                      "--force-keyframes-at-cuts", "-o", base + ".%(ext)s", f"https://www.youtube.com/watch?v={video_id}"],
  50 |                     check=True, timeout=300, capture_output=True)
  51 | -    src = next(os.path.join(out_dir, f) for f in sorted(os.listdir(out_dir))
  52 | -               if os.path.splitext(f)[0] == stem and not f.endswith(".wav"))       # exact stem: never a longer id
  53 | +    src = next((os.path.join(out_dir, f) for f in sorted(os.listdir(out_dir))
  54 | +                if os.path.splitext(f)[0] == stem and not f.endswith(".wav")), None)   # exact stem: never a longer id
  55 | +    if src is None or media_seconds(src) < MIN_SECTION_SHARE * (b - a):   # RULING 142 (3): a post_live stream's empty
  56 | +        whole = whole_stream(video_id, WHOLE["audio"][1], out_dir, "audio")   # (or absent) section: the whole audio
  57 | +        #   stream once, the window cut here
  58 | +        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{a:.3f}", "-i", whole, "-t", f"{b - a:.3f}",
  59 | +                        "-ac", "1", "-ar", "16000", wav], check=True, timeout=300)
  60 | +        if media_seconds(wav) < MIN_SECTION_SHARE * (b - a):            # still empty: never a cached, never a pass
  61 | +            os.remove(wav)
  62 | +            raise OSError(f"{video_id} {a:.2f}-{b:.2f}: no audio in the section or the whole stream")
  63 | +        return wav, a
  64 |      subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True,
  65 |                     timeout=120)
  66 |      return wav, a
  67 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
  68 | index 24ed7a1..f4b1fcf 100644
  69 | --- a/pipeline/visual_pin.py
  70 | +++ b/pipeline/visual_pin.py
  71 | @@ -149,14 +149,29 @@ def fetch(video_id, start, end, work_dir):
  72 |      os.makedirs(d, exist_ok=True)
  73 |      stem = f"{video_id}_{int(start * 1000)}_{int(end * 1000)}"
  74 |      have = [f for f in sorted(os.listdir(d)) if os.path.splitext(f)[0] == stem and not f.endswith(".jpg")]
  75 | +    cut = os.path.join(d, stem + ".cut.mp4")                    # RULING 142 (3): a post_live span cut before
  76 | +    if not have and os.path.exists(cut):
  77 | +        return cut
  78 |      if not have:
  79 |          subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", FORMAT, "--download-sections",
  80 |                          f"*{start:.2f}-{end:.2f}", "--force-keyframes-at-cuts", "-o", os.path.join(d, stem + ".%(ext)s"),
  81 |                          f"https://www.youtube.com/watch?v={video_id}"], check=True, timeout=300, capture_output=True)
  82 |          have = [f for f in sorted(os.listdir(d)) if os.path.splitext(f)[0] == stem and not f.endswith(".jpg")]
  83 | -    if not have:
  84 | -        raise OSError(f"no video fetched for {stem}")
  85 | -    return os.path.join(d, have[0])
  86 | +    import transcript_truth as TT
  87 | +    path = os.path.join(d, have[0]) if have else None
  88 | +    if path is not None and TT.media_seconds(path) >= TT.MIN_SECTION_SHARE * (end - start):
  89 | +        return path
  90 | +    #   RULING 142 (3): a post_live stream's empty (or absent) section: the whole
  91 | +    if not (os.path.exists(cut) and TT.media_seconds(cut) >= TT.MIN_SECTION_SHARE * (end - start)):   # stream once
  92 | +        whole = TT.whole_stream(video_id, FORMAT, d, "video")          # (<= 480p), the span cut here, frame-exact
  93 | +        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-i", whole, "-t",
  94 | +                        f"{end - start:.3f}", "-an", "-vf", "scale=-2:'min(480,ih)'", "-c:v", "libx264", "-preset",
  95 | +                        "veryfast", "-crf", "28", cut],
  96 | +                       check=True, timeout=300)
  97 | +        if TT.media_seconds(cut) < TT.MIN_SECTION_SHARE * (end - start):
  98 | +            os.remove(cut)
  99 | +            raise OSError(f"no video in the section or the whole stream for {stem}")
 100 | +    return cut
 101 |  
 102 |  
 103 |  def sheet(video, start, end, work_dir):
 104 | diff --git a/tests/package/test_ruling_142_post_live.py b/tests/package/test_ruling_142_post_live.py
 105 | new file mode 100644
 106 | index 0000000..1447d03
 107 | --- /dev/null
 108 | +++ b/tests/package/test_ruling_142_post_live.py
 109 | @@ -0,0 +1,145 @@
 110 | +#!/usr/bin/env python3
 111 | +"""RULING 142 (3) on the builder's side (orchestrator 14:32 ET Nov 17): a post_live YouTube stream (DASH segments only)
 112 | +gives an EMPTY section download (MeC8YEmUx_w, 15:5x ET: 258 bytes, 0 s), so this side's word check
 113 | +(transcript_truth.audio_window) and frame sheet (visual_pin.fetch) would fail closed on every clip of it. They now fetch
 114 | +the whole stream once per video (the integrator's read-only cache first, batch 111), cut the window locally, and still
 115 | +fail closed when even that holds no media. Offline: yt-dlp, ffmpeg and the duration probe are stubbed."""
 116 | +import os
 117 | +import sys
 118 | +import tempfile
 119 | +import unittest
 120 | +from unittest import mock
 121 | +
 122 | +HERE = os.path.dirname(os.path.abspath(__file__))
 123 | +REPO = os.path.dirname(os.path.dirname(HERE))
 124 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 125 | +import transcript_truth as TT  # noqa: E402
 126 | +import visual_pin as VP  # noqa: E402
 127 | +
 128 | +
 129 | +class Media:
 130 | +    """yt-dlp / ffmpeg stand-ins that write the files they would, and a duration table for media_seconds."""
 131 | +
 132 | +    def __init__(self, section_s=0.0, cut_s=None, write_section=True):
 133 | +        self.calls, self.section_s, self.cut_s, self.write_section = [], section_s, cut_s, write_section
 134 | +        self.seconds = {}
 135 | +
 136 | +    def run(self, cmd, **kw):
 137 | +        self.calls.append(list(cmd))
 138 | +        if cmd[0] == "yt-dlp":
 139 | +            out = cmd[cmd.index("-o") + 1].replace("%(ext)s", "m4a" if "bestaudio" in cmd[cmd.index("-f") + 1]
 140 | +                                                   else "mp4")
 141 | +            if "--download-sections" in cmd:
 142 | +                if self.write_section:
 143 | +                    open(out, "w").write("x")
 144 | +                    self.seconds[out] = self.section_s
 145 | +            else:
 146 | +                open(out, "w").write("whole")
 147 | +                self.seconds[out] = 5700.0
 148 | +        elif cmd[0] == "ffmpeg":
 149 | +            out = cmd[-1]
 150 | +            open(out, "w").write("cut")
 151 | +            if "-ss" in cmd:                          # a cut from a whole stream
 152 | +                self.seconds[out] = float(cmd[cmd.index("-t") + 1]) if self.cut_s is None else self.cut_s
 153 | +            else:
 154 | +                self.seconds[out] = 15.0
 155 | +        return mock.Mock(returncode=0, stdout="", stderr="")
 156 | +
 157 | +    def secs(self, path):
 158 | +        return self.seconds.get(path, 0.0)
 159 | +
 160 | +    def wholes(self):
 161 | +        return [c for c in self.calls if c[0] == "yt-dlp" and "--download-sections" not in c]
 162 | +
 163 | +
 164 | +class Base(unittest.TestCase):
 165 | +    def setUp(self):
 166 | +        self.tmp = tempfile.TemporaryDirectory()
 167 | +        self.d, self.cache = os.path.join(self.tmp.name, "w"), os.path.join(self.tmp.name, "theirs")
 168 | +        os.makedirs(self.d)
 169 | +
 170 | +    def tearDown(self):
 171 | +        self.tmp.cleanup()
 172 | +
 173 | +    def patched(self, m):
 174 | +        return [mock.patch.object(TT.subprocess, "run", m.run), mock.patch.object(TT, "media_seconds", m.secs),
 175 | +                mock.patch.object(TT, "POST_LIVE_CACHE", self.cache)]
 176 | +
 177 | +    def go(self, m, fn):
 178 | +        ps = self.patched(m)
 179 | +        for p in ps:
 180 | +            p.start()
 181 | +        try:
 182 | +            return fn()
 183 | +        finally:
 184 | +            for p in ps:
 185 | +                p.stop()
 186 | +
 187 | +
 188 | +class TestTheWordChecksWindow(Base):
 189 | +    def test_an_empty_section_is_cut_from_the_whole_stream_fetched_once(self):
 190 | +        m = Media(section_s=0.0)
 191 | +        wav, a = self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
 192 | +        self.assertEqual((a, m.secs(wav) > 0), (96.0, True))
 193 | +        self.assertEqual(len(m.wholes()), 1)
 194 | +        cut = [c for c in m.calls if c[0] == "ffmpeg"][-1]
 195 | +        self.assertEqual((cut[cut.index("-ss") + 1], cut[cut.index("-t") + 1]), ("96.000", "15.500"))
 196 | +        self.go(m, lambda: TT.audio_window("vid", 200.0, 210.0, self.d))         # another window: the same stream
 197 | +        self.assertEqual(len(m.wholes()), 1)
 198 | +
 199 | +    def test_the_integrators_cached_stream_is_read_first(self):
 200 | +        os.makedirs(os.path.join(self.cache, "vid"))
 201 | +        theirs = os.path.join(self.cache, "vid", "audio.m4a")
 202 | +        open(theirs, "w").write("whole")
 203 | +        m = Media(section_s=0.0)
 204 | +        m.seconds[theirs] = 5700.0
 205 | +        self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
 206 | +        self.assertEqual(m.wholes(), [])                                           # no download of our own
 207 | +        self.assertIn(theirs, [c for c in m.calls if c[0] == "ffmpeg"][-1])
 208 | +
 209 | +    def test_no_section_file_at_all_takes_the_whole_stream_too(self):
 210 | +        m = Media(write_section=False)
 211 | +        wav, _ = self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
 212 | +        self.assertTrue(m.secs(wav) > 0)
 213 | +        self.assertEqual(len(m.wholes()), 1)
 214 | +
 215 | +    def test_a_normal_section_is_used_as_before(self):
 216 | +        m = Media(section_s=15.5)
 217 | +        self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
 218 | +        self.assertEqual(m.wholes(), [])
 219 | +        self.assertNotIn("-ss", [c for c in m.calls if c[0] == "ffmpeg"][-1])
 220 | +
 221 | +    def test_a_cut_with_no_audio_fails_closed_and_is_never_kept(self):
 222 | +        m = Media(section_s=0.0, cut_s=0.0)
 223 | +        with self.assertRaises(OSError):
 224 | +            self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
 225 | +        self.assertFalse([f for f in os.listdir(self.d) if f.endswith(".wav")])
 226 | +
 227 | +
 228 | +class TestTheFrameSheetsVideo(Base):
 229 | +    def test_an_empty_section_is_cut_from_the_whole_stream_and_kept(self):
 230 | +        m = Media(section_s=0.0)
 231 | +        v = self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d))
 232 | +        self.assertTrue(v.endswith(".cut.mp4") and m.secs(v) > 0, v)
 233 | +        cut = [c for c in m.calls if c[0] == "ffmpeg"][-1]
 234 | +        self.assertEqual((cut[cut.index("-ss") + 1], cut[cut.index("-t") + 1]), ("100.000", "10.000"))
 235 | +        self.assertIn("scale=-2:'min(480,ih)'", cut)                               # the sheet's <= 480p
 236 | +        n = len(m.calls)
 237 | +        self.assertEqual(self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d)), v)   # cut once, then kept
 238 | +        self.assertEqual(len(m.calls), n)
 239 | +
 240 | +    def test_a_normal_section_is_returned_as_before(self):
 241 | +        m = Media(section_s=10.0)
 242 | +        v = self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d))
 243 | +        self.assertTrue(v.endswith("vid_100000_110000.mp4"), v)
 244 | +        self.assertEqual(m.wholes(), [])
 245 | +
 246 | +    def test_a_cut_with_no_picture_fails_closed_and_is_never_kept(self):
 247 | +        m = Media(section_s=0.0, cut_s=0.0)
 248 | +        with self.assertRaises(OSError):
 249 | +            self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d))
 250 | +        self.assertFalse(os.path.exists(os.path.join(self.d, "visual", "vid_100000_110000.cut.mp4")))
 251 | +
 252 | +
 253 | +if __name__ == "__main__":
 254 | +    unittest.main()
 255 | 
```

---

pp-selectid: RULING 142 (3) (orchestrator 14:32 ET Nov 17: post_live streams, "do not wait for YouTube") ON THE BUILDER'S
SIDE. The integrator's batch 111 made the render and its lock pre-check fetch a post_live stream whole and cut locally
(its read-only cache /home/ultron/protocol_pulse/data/post_live_cache/<video>/audio.m4a, video.mp4). This side's two
fetchers still used yt-dlp --download-sections, which on the post_live stream MeC8YEmUx_w gives an EMPTY file (tested
15:5x ET: 258 bytes, 0 s): the word check (transcript_truth.audio_window, L-v 2 + CUTTABLE, HARD) and the frame sheet
(visual_pin.fetch, the visual check, HARD) would fail closed on every clip of it, and every 3-channel story today needs
one. Files: pipeline/transcript_truth.py, pipeline/visual_pin.py, tests/package/test_ruling_142_post_live.py (new).

THE CHANGE:
(a) transcript_truth: media_seconds(path) (ffprobe; 0.0 when unreadable); whole_stream(video_id, fmt, out_dir, tag):
    the integrator's cached whole stream first when it holds media (read only), else ONE yt-dlp download of the whole
    stream per video and tag into out_dir, reused after. audio_window: when the section file is ABSENT or shorter than
    MIN_SECTION_SHARE (0.5) of its window, the window is cut from the whole audio stream (ffmpeg -ss <start> -i whole -t
    <len>, 16 kHz mono); a cut that still holds under half the window raises OSError and leaves no wav (fail closed: the
    word check reads it as not measured). A normal section takes the unchanged path.
(b) visual_pin.fetch: the same for the <= 480p frame clip: an absent or empty section is replaced by a cut from the
    whole video stream (re-encoded, scaled to at most 480 lines, no audio), kept as <stem>.cut.mp4 and reused; an empty
    cut raises and is removed. A normal section is returned as before.
    No offset check of our own: the integrator cuts audio and video from the same DASH stream timestamps, and its HARD
    offset guard checks the audio clock; a shift here makes the word check fail closed (its words would not match).

EVIDENCE: a real run (free) on MeC8YEmUx_w 5409.96-5420.32 from the integrator's cache: the word check's window 15.86 s,
the frame clip 10.38 s. TESTS (8, offline, yt-dlp / ffmpeg / ffprobe stubbed): an empty section cut from the whole
stream fetched once; the integrator's cache read first; no section file at all; a normal section unchanged; an empty
audio cut fails closed and is not kept; the video cut is kept and reused, scaled to 480; a normal video section
unchanged; an empty video cut fails closed and is removed. Mutations: 8 of 8 killed.

PLEASE CHECK: (1) can an empty or wrong window ever be returned as measured? (2) is a normal (non post_live) video
unaffected? (3) the cache and download paths (concurrent builds, partial downloads); (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
