# DEFINITION OF DONE — PULSE CHECK (living document, started 2026-11-11 02:52 ET)

Every PBX rule mapped to the check that enforces it and the must-fail test that proves the check
works. A rule with no check is listed as **UNENFORCED** (in red), never left out. Updated as the work
lands; the commit that changes a row is named in it.

Legend: G = gate (runs in run_fresh.stage_gates / pre-render stage), T = must-fail test file.

## LIVE STATE (updated 2026-11-11 14:09 ET; newest first)

- 14:04 4b RUN 1 HELD (pipeline defect, DEC-8: fix, audit, the count restarts): editorial crashed in
  story_semantics.emergent_clusters on sorted({None, ...}): four whisper_words records hand-made 2026-11-10
  ~05:28 ET outside the writer (qo8rDU3bbMo Simply Bitcoin, jbDqdLytkNM Bitcoin Magazine, eEB0nt6jvEw Marty
  Bent, RXTVaDsN11M DataDash) carry channel_id / channel_name None; their meta.json has both. Fix (batch 11,
  audit running): chunks take missing identity from meta.json, none anywhere = no chunks; the writer refuses
  an identity-less meta. The four records now chunk with their channels (22 / 34 / 32 / 69 chunks). Bible
  E-FAIL-030. The Law 22 run at 36e769d0 was stopped (superseded); 4b restarts at the batch-11 HEAD with a
  Law 22 re-proof there.
  Replay of recut #2 finished (runs/pinned_20261111_172202_replay_cut1329): G12 / G15 PASS both formats
  (DEC-11); G3c clip_01 PASS; still not passing: G9 both, G10 16:9, G14 (t=24.083, peak 0.174, same pause),
  G3c hook, and NEW 16:9 G3b clip_01: the final's context-free tail ASR heard 'in the monday route.' for
  '... rally.' (9:16 G3b PASS; prepare's edge check heard 'rally.'; G17b and G18 PASS): the 83 ms DEC-10 fade
  at the true minimum 80.84 ends 35 ms after the word, and one ASR decode under the bed misheard it (OD-6
  class: single-word ASR; nothing changed).

- 14:03 4b STARTED at HEAD 36e769d0 (pushed): run 1 via the wrapper (auto), runs/fresh_20261111_190259;
  Law 22 re-proof at the same HEAD running alongside. Commits since the 13:15 note, each audited: 9b459ec6
  (8d valley search inside the transcript gap), af5447c6 (DEC-11 credit rings + registered-avatar discs;
  G15 fails closed), 36e769d0 (batch 10: the 9:16 safe frame keeps its input's colour matrix).
  Replay of recut #2 from the cut with 8d (runs/pinned_20261111_172202_replay_cut1329; scratch driver: the
  replay harness's copy + production stage_cut / stage_sentence_law, then run_tail; vision off): Natalie cut
  68.38-80.84; G3c clip_01 tail -33.7 vs limit -31.7 PASS (was -22.4: the kept 'Bu'), clip_02 head onset N
  PASS, clip_03 PASS; G3c still FAILS only on the HOOK tail -42.7 vs -43.9 (16:9) / -42.8 vs -44.1 (9:16):
  the 340 ms pause after 'take.' holds no next word; DataDash's room tone sits 10.4 dB under his quiet speech
  (-32.3), G3c asks 11.63: the gate measures the source's ratio, not a cut into a neighbour (OD-5 class; an
  envelope-minimum cut with the 2-frame fade would pass it but is a cutter-wide change: not made during 4b).
  G9 in the replay: 16:9 14.3 / 9:16 14.5 (its vertical render predates batch 10). Nov 10 story: NOT sent;
  blockers G9 (OD-4 residual 0.03 both formats), G10 (16:9 BM lower third: needs a 16:9 framing decision for
  has_chyron channels), G14 (pause under the bed), G3c hook (source ratio).

- 13:32 ORCHESTRATOR NOTE 13:15 (time box 14:30) on recut #2 runs/pinned_20261111_172202 (HEAD 29299ea5,
  71.17 s both formats, not delivered). Gate rows: G16 / G17 / G18 / G19 PASS both formats; NOT PASS: 16:9
  G3c, G9, G10, G14 (inconclusive), G15; 9:16 G3c, G9, G14 (inconclusive), G15. Per item:
  1a G9 (not a rounding / equality failure; the reference passes its own floor): sampled at identical offsets
     from the end, ours 16:9 14.3021 (14.1194 / 14.3162 / 14.4707) vs floor 14.33 (v2f 14.3357); 9:16 14.4652 vs
     14.77 (v2f 14.7715). Two causes: (i) RENDER DEFECT found: our 9:16 final carries color_space=unknown (v2f's
     9:16 and both 16:9 files: bt709), so the decoder converts with BT.601: decoded as bt709 our 9:16 reads
     14.7418, and v2f decoded as BT.601 reads 14.4971; the vertical path loses the tag when the first segment
     is a safe-frame layout (fix pending, Law 22 re-proof needed). (ii) the remaining ~0.03 in BOTH formats
     (14.3021 vs 14.3357; 14.7418 vs 14.7715) is the same locked outro (12.69 decoded directly) lifted
     differently by the final re-encode = OD-4 (floor 0.006 under v2f, encode-to-encode spread 0.03). No
     constant changed: G9 cannot pass on this render until OD-4 is decided.
  1b G3c (limit = segment speech median - 11.63 dB in the last 60 ms; head = no 10 ms jump from < -35 to
     > -30 dBFS): hook tail -42.7 vs -43.9 (DataDash's room tone after 'take.' is only 10.4 dB under his
     quiet speech, -32.3; the tail holds no next word: 340 ms pause before it); clip_01 tail -22.4 vs -31.7 =
     a REAL defect: the cut at 80.93 kept 'Bu' of 'But' (fixed in 9b459ec6, batch 8d: the minimum search left
     the transcript gap by 80 ms; the true minimum is 80.84, -22 dB); clip_02 head onset (the 83 ms DEC-10 fade
     from the shallow minimum between abutting 'days.' | 'Of' at 38.20, -20 dB vs speech -13.2, crosses
     -35 -> -30 dBFS inside 10 ms in the final). Replay from the cut with the 8d fix running for the exact
     clip_01 number. Expected conflict (to confirm): G3c's 11.6 dB-deep 60 ms tail and its head rule cannot be
     met by a 2-frame fade at a minimum only 2-7 dB under speech (abutting words): OD-8 below if confirmed.
  2  G14 inconclusive at t=24.167 (clip_02 +2.0 s = source 40.195-40.695): NOT a transition (the only dissolve
     is after clip_02, ~41.2 s) and NOT a VO freeze (no body VO). The window is a 0.6 s PAUSE inside Yahoo's
     sentence (source -44 .. -84 dB after a syllable ending 40.17; 'massively' starts 40.90; Whisper stretches
     'pretty' over it), so the final holds only the music bed (-38 .. -45 dB) there: xcorr peak 0.154 < 0.3.
     Conclusive needs source speech in the 0.5 s window. The authorised sampling skip (declared transition /
     VO-freeze intervals) does not cover it; nothing changed (same class as OD-7).
  3  DEC-11 implemented (pipeline/credit_rings.py; G12 in segment_v1/qa_gates.py, G15 in pipeline/gates.py;
     run_fresh passes the credited channels): ring = brand-red mask contour of ring size, ellipse fitted to it,
     aspect >= 0.95 unchanged, count == EDL channels at the layout positions. MEASURED: yesterday's card's RINGS
     are round (0.999-1.000, at the layout positions); its D4 defect was the 1280x720 thumbnail squashed into
     each disc. To keep DEC-11's must-fail, G15 also requires each disc to be the credited channel's registered
     avatar (correlation r >= 0.90; measured 0.999-1.000 on every v2f and Nov 11 node, yesterday 0.297 / -0.030
     / -0.142). Tests: yesterday fails G15 (avatars) with round rings; v2f + today's card pass G12 + G15 both
     formats; a card squeezed to 80 % fails on ring aspect; 3 rings for 4 channels fails G12. Audit batch 9
     running.
  4  clip_03 sentence start confirmed: lock first word 'Last' (word 45; previous 'Bitcoin.' 14.18-14.38, heard
     until 14.67); silence 14.68-14.88, breath 14.89-15.13 (-35 .. -46 dB), 'Last' 15.20-15.37, 'night' from
     15.42. The cut 14.94 sits in the breath, 260 ms before 'Last'; G3 heard 'last'; G16 / G18 PASS. No fix.
  NOT in the 13:15 list: G10 16:9 clip_03 FAIL is REAL: the 16:9 frame shows Bitcoin Magazine's burned-in
     lower third (sponsor bar, stock + BTC tickers, 'ORACLE REMINGTON ... | BMTV' name chyron); bottom-12 %
     edge density 0.0846-0.0854 vs 0.08, 0.084 even without the watermark strip. The 16:9 path has no chyron
     crop (has_chyron only routes the channel to G10); the 9:16 safe frame blurs it (PASS). Needs a decision:
     a 16:9 framing for has_chyron channels (crop / safe frame) or a BM window without the lower third.
  Verdict: no clean pass is possible on this story before OD-4 (G9) and the G10 framing are decided; nothing
  sent. After batch 9 + the replay numbers: 4b.

- 12:03 DEC-10 recut #1 (wrapper, HEAD ae965c95; runs/pinned_20261111_170153) HELD at stage cut, before any
  render: run_fresh.stage_cut's M19-era cut acceptance (cut_accept) rejected exactly the two edges the
  sentence-law cutter placed at the envelope minimum: clip_01 Natalie OUT 80.93 "cut_out not inside a
  genuine pause with >= 60 ms ahead" (the old 60 ms guard; DEC-10 b: 0 ms) and clip_02 Yahoo IN 38.20
  "inside continuous speech (no boundary dip in prior 100 ms)", lookback min -18.4 dB vs loud -25.6 (the
  words 'days.' | 'Of' abut; the minimum between them is -19.5 dB). hook and clip_03 ACCEPT. Not delivered.
  Root cause: my DEC-10 implementation changed the cutter but missed this second edge check. DEC-10 d: "a
  clip is rejected for edges only if (i), (ii) or (iii) cannot be met"; the M19 quotas are none of them.
  Change (batch 8c, audit running): for an edge flagged valley_in / valley_out in cuts_final.json (set only
  by sentence_law.accepted_cut; a human PIN's table never carries it), stage_cut keeps the M19 reading in
  CUT_ACCEPTANCE.json (as "m19") and leaves the verdict to the next stage, G16 (legal range +
  neighbour_clear with the cut's own fades, HOLD before any render). Every other edge unchanged. Tests:
  valley edge left to G16 with its M19 reading kept; a normal edge failing M19 still holds; no flag = no
  change. The prepare clip contract (first 5 ms >= 9 dB under 25-45 ms) is expected to pass an 83 ms
  linear fade (~20 dB).

- 11:36 DEC-10 batch 8 answered (docs/audits/pulse-sentence-law/batch8_dec10_edge_timing/AUDIT_RESPONSE.md):
  gospel + docstrings ratify the recalibration; VALLEY_FADE_S = 2 video frames at 24 fps = 83 ms; valley test
  rewritten (was vacuous). Follow-up 8b (audit running on its own diff): (1) the quiet run is searched between
  the two words' midpoints (the rewritten fixture caught a tie with the neighbouring junction); (2) DEC-10 d
  made explicit: an edge whose quiet run is < 80 ms (in) / < 140 ms (out) (the 01:50 legality minimums, now
  choosing only the METHOD) is cut at its envelope minimum with the 83 ms fade; (3) Heimdall F2: an edge NOT
  at a minimum must pass cut_accept's unchanged checks also when the other edge is at one (mocked tests both
  ways). Lineup re-measured with (1)-(3), unchanged: hook 0.03-9.33 (+0.25 s pad, 20/30), Natalie
  68.38-80.93 (in 20 ms; out at the minimum, 83 ms), Yahoo 38.20-57.37 (in at the minimum, 83 ms; out 30),
  Bitcoin Magazine 14.94-31.79 (20/30, quiet run out exactly 140 ms -> standard). 58.1 s of clips; every
  neighbour_clear row below the valley threshold (worst -34.9 dB vs -25.4).
  Law 22 re-proof with batch 8 in the tree: runs/v2f_20261111_160348 byte-identical (472938134157b649 /
  5545a261feedd8c1). Next: suites + regressions, commit + push, then the DEC-10 recut via the wrapper.
- 11:05 DEC-10 implemented (sentence_law: timing minimums 0 = v2f worst; legal cut range = the HEARD gap
  (previous word's offset .. next word's onset at speech - 6 dB); neighbour side ends at the envelope
  minimum; abutting words cut at that minimum with a 2-frame fade; NEW neighbour_clear (c-ii): no frame of
  the neighbour above speech - 12 dB after the fade; D1 file-head / hook rule unchanged at 80 ms; per-cut
  fades through prerender, v2f's 20 / 30 unchanged). Tests: v2f must-pass on 5 of its 8 edges; 3 recorded,
  each by measurement: hook head (D1 head rule: 70 ms, no pad, same side as yesterday's D1), clip_01 OUT
  (PBX's own one-time exception; cut at 249.63 inside the soft "So"), clip_02 IN (cut at 624.63 inside a
  110 ms voiced stretch at speech level, -20..-26 dB): (c-ii) fails them, so (c-ii) is not loosened.
  Yesterday's D1 / D2 / D3a / D3b still FAIL (D2 now "outside the legal range": the 120 ms pause after
  'week.' became legal, yesterday's cut is 2.3 s past it). Audit batch8 + Law 22 re-proof running.
- 11:08 DEC-10e lineup on the PIN's frozen sources, exact measurements:
    hook DataDash 0.00-9.08 "Bitcoin has now seen a 16 % decline ... give or take." LEGAL: cut 0.03-9.33 +
      the 0.25 s D1 pad (60 ms genuine lead at the file head), fades 20/30; scorer 4.0.
    Natalie as written "It went ... how the market shapes up this week." CUTTABLE (68.38-85.41) but 5
      sentences > the 1-3 sentence law -> REJECTED by that measure. Its first 3 sentences "It went ...
      Monday rally." LEGAL: cut 68.38-80.93 (12.55 s; out at the envelope minimum after 'rally.', 83 ms
      fade); scorer 5.0. ("Bitcoin also wasn't spared ... last week." is legal too but 11.78 s < the 12 s
      clip minimum.)
    Yahoo "Of course, Bitcoin dropped ... many times." LEGAL: cut 38.20-57.37 (19.17 s; in at the envelope
      minimum between abutting 'days.' | 'Of', 83 ms fade); scorer 5.0.
    G5: those three = 41.3 s of content + ~9 s credits + 4.46 s outro = ~54.7 s < 60 (G5 FAIL by ~5 s).
    Decision (logged): a 4th segment from a 4th channel, as v2f had: Bitcoin Magazine 14.68-31.34 "Last
      night was Bitcoin's first weekly close below the 50-week moving average since September. The 50-week
      was around $75,500, and Bitcoin closed around $74,700, just 1 % below the line. But one percent is
      still a miss." (legal; scorer 4.0 in one batch, 3.0 in the lineup batch: the scorer moves with its
      batch). PIN: pipeline/PIN_RECUT_NOV10_DEC10_20261111.json (~72 s).
  Still expected to fail by construction: G9 (OD-4), G15 with "Natalie Brunell" on the card (OD-1).

- 10:25 LINEUP SEARCH RESULT for the Nov 10 story (direction 1), every rule unchanged. Sources searched:
  full Bitcoin Magazine "Bitcoin Loses Key Moving Average" (104/130 budget windows legal), full DataDash
  (89/218), full Yahoo (133/158), CoinTelegraph (118/140), Marty Bent 0-7 min (22/30; his 50-week sentence
  is later in a 44-min show, not fetched), Natalie (no legal Bitcoin window). Production scorer on the event
  "Bitcoin fell sharply ... losing its 50-week moving average ... below about $74,000 ... tech selloff":
    hooks >= 4.0 that pass the stand-alone/topic rule: ONE: Bitcoin Magazine 269.45-281.38 "From the COVID
      era, the continued outflows and broad spot sellers pushing our closes down week by week has us
      rhyming with 2012. We want to see Bitcoin reclaim the 50-week urgently." (4.0) - its first sentence is
      a punctuation split (the audio reads "...eventual bailout from the COVID era." as the previous
      sentence's end), so to a listener it starts mid-thought. Every other legal hook scores 1-3 (history,
      Saylor's purchase, Scaramucci's $200K).
    clips >= 3.5: Bitcoin Magazine 14.94-31.95 "Last night was Bitcoin's first weekly close below the
      50-week moving average since September. The 50-week was around $75,500, and Bitcoin closed around
      $74,700, just 1 % below the line. But one percent is still a miss." (4.0; 16.66 s: no legal boundary
      after its first two sentences, so it cannot be the 8-12 s hook) and DataDash 143.62-161.67 "But we've
      seen a really nice decline here on Bitcoin, okay? 16 % so far ..." (5.0). Every other legal clip <= 3.0.
    best legal lineup: 11.20 + 16.66 + 17.64 = 45.5 s of content + ~9 s credits + 4.46 s outro = ~59 s:
      G5 duration (60-120 s) fails by ~1 s; body VO is off by default (Editorial Law 2 / M20); and gates
      in the open decisions would still fail a correct render (OD-4 G9 always; OD-1 G15 with some names;
      OD-5 G17a and OD-6 G3 on DataDash's gated "But").
  => A clean pass of the Nov 10 story is not reachable with the current laws and gates. Decisions that
  would unblock it (orchestrator / PBX): OD-4 (G9 on a locked black-ending outro), OD-1 (G15 on glyphs),
  OD-5/OD-6 (G17a gated silence, G3 single word), and either a VO intro with a declared job or a hook
  budget > 12 s for a story whose event sentence runs 16.7 s. Meanwhile: land batches 6-7, then 4b
  (fresh stories search every channel and story, where the same laws may find cleaner material).
- 10:20 V1 batch (batch 7) audited; consensus implemented (stand-alone empty subject fails closed, vacuous
  panel verdict, test strengthening); G19 rows in both formats.

- 09:45 replay of run 6 from prepare (runs/pinned_20261111_123750_replay_20261111_134458, batch-6 code)
  proved on real data: G18 PASS on every segment, both formats (decimal canonicaliser); prepare's shot snap
  held clip_02's last 3 frames on Natalie's own shot; 9:16 V1 PASS (incl. next shot, credits, per-shot
  letterbox). 16:9 V1 FAIL only because qwen's reply lacked its final '}' (all six answers present: 6 x
  "missing"). Remaining rows are the diagnosed set: G3, G5, G9, G14, G15, G17 (OD-1, OD-4..OD-7 below).
- 09:45 V1 batch (in the working tree, audit next): the credits question gets the EDL's channel list (a
  9:16 crop can hide a show's branding: qwen called Yahoo "absent" on run 6); the next-shot line is answered
  ONE CUT AT A TIME from the cut's -3f/+3f frames side by side (on run 6 the whole-sheet answer misread tile
  labels and neither model saw the real defect), the sheet answer kept as advisory; a reply missing only
  its final braces is closed (max 3, nothing else repaired); NEW deterministic G19 EDGE SHOTS on both finals
  (no hard shot change inside a talking head outside its speech): must-fail on run 6's own final (clip_02
  at 41.1-41.3 s), must-pass on the snapped replay.
- 09:30 wider sources transcribed: Bitcoin Magazine "Bitcoin Loses Key Moving Average" (104 of 130 budget
  windows legal: clean pauses), DataDash full (89), Yahoo full (133), CoinTelegraph; Marty Bent's crashed on
  CUDA OOM (GPU0 shared by three of my jobs: my error, serialised since). Full videos fetched natively;
  the mp4 audio is bit-identical to the transcribed m4a (PCM sha). Lineup search (65 windows pass the
  opener/topic screen) is being scored by the production scorer now.

- 08:53 batch for the 08:30 note staged + in audit (batch6_orch0830): replay harness (run_fresh.run_tail +
  pipeline/replay.py), stand-alone + topic rule (pipeline/stand_alone.py at validate for every run, and at
  auto selection on final windows), G18 canonicaliser (decimal = one token), shot_snap (V1 next shot),
  wrapper sends Telegram only on a clean pass. Replay of run 6 from prepare running with these: prepare
  snapped clip_02 "tail: frames 315-317 were the next shot, held on frame 314" (audio untouched).
- 08:50 lineup search widened (direction 1, decision above): full audio of Bitcoin Magazine jbDqdLytkNM
  ("Bitcoin Loses Key Moving Average"), Marty Bent eEB0nt6jvEw, DataDash RXTVaDsN11M, Yahoo 36HPi9UZPOc,
  CoinTelegraph LGzfQjA2SHA in runs/recut_sources_20261111b (whisper large-v3 words + punctuation running);
  video only for the chosen windows afterwards. Run 6 REPORT.md has the six-window table (proposed windows
  score 4.0 / 4.0 / 5.0 and pass stand-alone; each is blocked by a measured edge pause under the law).

- 08:38 4b landed on this branch (55eb579b + 376c4127, audited: batch4 AUDIT_RESPONSE.md). Suites 166
  passed; the one failure is the documented pre-existing live-LLM test (test_editorial_robust
  positive_control_real_midterms: story_semantics only, byte-identical before/after 4b);
  regression_test.sh 26 PASS / 0 FAIL; regression.sh PASS (0.041 s).
- 08:30 ORCHESTRATOR NOTE (do not send failing cuts; four directions). Run 6 had ALREADY been delivered
  at 08:20 as REVIEW ONLY by the wrapper (msgs 67570/67571 videos, 67572/67573 contact sheets), before the
  note: the wrapper sent REVIEW ONLY drops by design. Changing: Telegram only on a clean pass.
  Evidence so far (verified, not assumed):
  * G9: tail = the hash-identical locked outro; luma run 6 16:9 14.3058 / v2f 14.3357 (floor 14.33),
    9:16 14.7430 / 14.7715 (floor 14.77); the conformed outro itself 12.69. Encode-level 0.03 on a
    black-ending card vs a floor 0.006 under the reference: calibration margin question (OD-4), gate kept.
  * G5: duration 54.83 s < 60 (hook 10.1 + clips 18.1 + 13.3 = 41.4 s of content); loudness -15.6 LUFS
    (target -14 +- 1): per segment hook -13.3, clip_01 DataDash -21.6, clip_02 -15.0, shoutout -15.3,
    outro -13.1; v2f whole -14.6. The DataDash segment is 8 LU under the rest.
  * G14: NOT the dissolve offset: 16:9 frame_sim >= 0.99 on every sample incl. all of clip_02 after the
    dissolve (reference 28.133 s = source 24.695 s = cut_in + 45 ms); the 0.00-0.04 values are the 9:16
    crop-vs-source comparison, which the gate itself marks LIMITED (unscored). The one scored failure is a
    0.5 s audio window in DataDash's clip (t = 12.08 s): speech at -39 dB median (quieter than his -28..-32)
    matched 4.6 s away at xcorr 0.42 (>= 0.3, so not "inconclusive").
  * G15 (OD-1 evidence, docs/audits/pulse-sentence-law/od1_g15_evidence/): the three avatar rings measure
    round; the only "squished ring" is the capital N of "Natalie Brunell" (contour bbox 31 x 36 px; its
    fitted ellipse 122 x 212 passes G15's size filter, which tests the ellipse, not the contour). G15 kept.
  * G17a clip_01 lead 60 ms: DataDash's source is noise-gated: the 320 ms before "But" is mostly below
    the -100 dBFS digital floor, which G17a does not count as genuine quiet; only 60 ms is above it.
    Moving the in-point or the room-tone pad cannot change that measurement (OD question, gate kept).
  * G3: heard 'bye!' / 'no' for 'But' (hook, clip_01); G18 edges (first two words, full-context ASR)
    and G17b first_word_ratio 0.98 / 0.95 say the words are intact.
  * G18: one real comparator hole found while fixing it: '5.5 %' became tokens '5 5' and the
    repeat-collapser merged them to '5', so 5.5 % and 5 % compared EQUAL. Fix: a decimal is one token;
    'one point three' / 'five and a half' map to it; tests both directions.
  * V1 next shot: real defect: Natalie's source cuts to an NVIDIA/AMD/MICRON graphic inside the pause
    before "Nvidia" (37.94); our out-point 37.86 keeps those frames.
  * Lineup (direction 1): the better windows are excluded by MEASURED audio under the unchanged law, not
    by a bug or a budget: DataDash 0.00-9.08 hook: file-head in-edge fine (0.25 s pad declared), but after
    "give or take." the genuine quiet run is 9.30-9.39 before a breath, so the law's tail (pause start +
    80 ms = 9.37) and cut_accept's run (9.33 with its 60 ms margin) never meet. Natalie "Bitcoin also
    wasn't spared ... last week." (3 sentences, 11.78 s): out-pause 120 ms < 80 ms tail + 60 ms guard;
    her 5-sentence window breaks the 1-3 sentence law and "rally." has no pause. Yahoo "Of course, Bitcoin
    dropped ...": no >= 80 ms pause before it (nor before the two sentences ahead of it). Under the
    stand-alone + topic rule, the frozen 5-min sources hold NO legal lineup for this story: Natalie has no
    legal Bitcoin window; DataDash no legal topical hook. Decision (logged): widen the search (full-length
    sources of the three videos + the approved channels that quoted the same price drop on Nov 10, e.g.
    Marty Bent, Bitcoin Magazine), never relax the law.

- 07:23 recut run 5 (runs/pinned_20261111_120910, HEAD b74c3b6c) HELD at render after 642 s:
  env..layout PASS (clip_02 fade retry 37.86 PASS; all six edges PASS). ffmpeg refused the transition
  graph: "First input link main timebase (1/1000000) do not match ... xfade timebase (1/24)": no room
  for a dissolve at hook->clip_01 (hard cut = concat filter), dissolve at clip_01->clip_02 (2 frames,
  bounded by measured non-speech) took the concat output as its first input. Phase 3 tests only dissolved
  at the first junction. Fix: settb=1/24 on xfade's running input; reproduced on the real graph (1290
  frames = 53.75 s, A/V equal) and by a new A,A,B test that fails on the old code with the production
  message (E-FAIL-025). Audit (batch5_xfade_timebase) + regressions running; then commit, push, run 6.
  Nothing delivered for run 5 (no finals).

- 07:15 4b on branch pulse-4b-wip (a2b56e53, worktree ~/worktrees/pulse-4b, pushed): same-event merge,
  DEC-9 story ledger (+ wrapper hook), letterbox one frame per shot, runbook, bible E-FAIL-023/024. Batch
  audit 4 (b74c3b6c..pulse-4b-wip) running; lands on this branch after run 5 + options, then Law 22
  re-proof at that HEAD, then the three fresh runs.
- 07:09 recut run 5 at HEAD b74c3b6c (pushed): runs/pinned_20261111_120910 via scripts/pulse_check_run.sh
  (foreground: this session lives in tmux pipeline_pp_dod). env..prepare PASS (clip_02 fade retry ->
  37.86 PASS; all edges PASS), layout done, render in progress.

- 07:05 batch 3 audit answered (AUDIT_RESPONSE.md): 9 fixes, each with a test failing on the audited code
  (review index `true`, vacuous second-edge move in the fade retry, stale contact sheet in copied runs,
  vision route retries, malformed answer line, key error, `_parse`, photo limits); rejections with evidence.
- 06:38 batch 3 (render fix + 06:20 contact sheet/visual checklist + batch-2 consensus) staged for ONE audit
  (deepseek,qwen27b + cross-LLM), then commit + push + recut run 5 via scripts/pulse_check_run.sh.
  Run 4 (runs/pinned_20261111_111252) passed env..layout and HELD at render: `module 'transitions' has no
  attribute 'plan'` = pipeline/transitions.py shadowed by video_pipeline_v3/transitions.py (render16 puts
  that folder first on sys.path) -> renamed pipeline/pulse_transitions.py + fresh-interpreter import-order
  test (E-FAIL-021). Suites 111 pass; regression_test.sh 26 PASS / 0 FAIL; regression.sh PASS (0.041 s).
- 06:40 vision panel (qwen3.8-27b + nemotron-3.5-super-vl) on yesterday's 9:16 sheet: HOLD, both name the
  credits thumbnails (D4); BOTH miss the letterboxed Melker/Brunell talking heads (D5) although the sheet
  shows them plainly (I read it). The vision line is an extra check; letterbox is caught by G4s, not by
  vision (E-FAIL-022 "still open").
- 06:50 vision follow-up (NOT in batch 3; lands before the 4b runs): asked ONE frame at a time ("is the
  sharp picture only a band with a blurred copy above and below?"), both models answer correctly on
  yesterday's frames: Melker clip_02 yes, DataDash chart hook yes (a screen: allowed), credits no. Plan:
  one full-res frame per SHOT of every 9:16 talking-head segment (VERTICAL_LAYOUT.json classes), any
  non-screen shot called letterboxed by either model (or unanswered) = V1 FAIL; must-fail on the
  fixture's Melker panel.
- 06:48 4b same-event merge (scratch copy, 7 tests pass; lands after run 5): link = the same counted
  STATEMENT (same video, shared supporting chunk, >= 5 consecutive shared words in the evidence quotes);
  a shared chunk alone is not enough (roundup shows). Real Nov 10 record: links exactly #13 "ETFs shed
  $1.3B" + #20 "Falls amid tech selloff" (identical Yahoo quote); #4 "below $74K" had NO counted verdict,
  #13 alone already had 2 channels and failed on hook quality (my earlier "each fell short on coverage"
  was wrong). Re-judge budget goes to not-counted verdicts by retrieval score. The tests caught a real
  NameError (`_decide_coverage` lost its local story_semantics import when moved out).
- DEC-9 decision (logged, not asked): the 72 h universe means runs 3 h apart still share most stories,
  so "genuinely different" is enforced by a delivered-story LEDGER (same event identity as the merge);
  each run takes the engine's top story not already delivered. A "no producible story" HOLD (with its
  rejection ledger) neither counts nor resets; then the next run waits for new stories.
- ORCHESTRATOR NOTE 06:45: after run 5 renders, REPORT.md gets the full text of every segment and the
  clip scorer's stand-alone score + reason (hook opens "I don't check it", clips open "But"/"And");
  selection is NOT changed now.
- 06:42 the production scorer (story_semantics.rate_passages, gemma3:27b, one batch as auto mode calls it)
  on the PIN text: hook Yahoo 3.0 "starts_mid_thought" (HOOK_MIN_SCORE 4.0: BELOW the auto floor);
  clip_01 DataDash 5.0 none; clip_02 Natalie 4.0 none (CLIP_MIN_SCORE 3.5). The auto window-start rule
  (editorial_select.start_is_boundary, CONTINUATION_OPENERS) rejects ALL THREE starts ("But", "But",
  "And"). The PIN path checks neither: I chose its windows by the sentence law alone. Not changed (06:45
  note); reported in run 5's REPORT.md. Evidence: scratchpad recut/standalone_scores.json.

- 06:12 recut run 4 at HEAD 8d10fcb7 (runs/pinned_20261111_111252) in progress, delivery to the approval
  chat by scripts/pulse_check_run.sh; then A/B/C (pipeline/transition_options.py) on the same cut.
- Recut runs so far, each HOLD fixed at the root cause, gates unchanged:
  run 1 05:45 (HEAD 497d8224) editorial gate LAW_1 "clip 2 missing": the review validator RETURNED its error
  (chat_json only reacts to exceptions) -> 99d20fb5 (E-FAIL-019);
  run 2 05:49 (99d20fb5) prepare: clip_02 fade-out (cut 37.87 on a tick inside the legal pause; real
  prepare at 37.84/37.80 passes) -> 9a0307c8 retry the failing edge at the next legal point (E-FAIL-020);
  run 3 06:03 (9a0307c8) prepare: CUDA OOM (another session's 22 GB model on the shared GPU0 Ollama) ->
  8d10fcb7 Whisper stages release GPU0 first (editorial-stage convention).
- Batched audit 1 (a1e732e1..497d8224) answered in 8d10fcb7 (AUDIT_RESPONSE.md); batched audit 2
  (497d8224..8d10fcb7) running. Its Grok call tripped the shared xAI $1/day ceiling at 05:49 and the gateway
  posted one "[xAI BUDGET]" alert to Telegram; audit wrappers now blank TELEGRAM_*; Grok blocked today.
- Law 22 re-proven with Phase 2+3+4a in the tree (runs/v2f_20261111_103004 byte-identical).
- 4b plan (read-only map, 05:47): (A) same-event MERGE after the coverage loop in editorial_select
  (~:802, before the word pass): group candidates of one event, one merged query (derive_story_query),
  pool verdicts deduped by video, RE-JUDGE the uncounted CURRENT_EVENT verdicts on their stored excerpts
  against the merged event (pooling alone would not have rescued Nov 10: only Yahoo + Natalie counted;
  the hand fix upgraded DataDash by re-judging), recompute coverage/currentness/decision. (B) widen the
  word-timestamp pass (`need`, ~:805-810) to every newly counted layout-eligible video, inside the one GPU0
  swap. Tests: test_window_review RoutedLLM + test_editorial_robust Orchestration fakes; a Nov 10
  story-split fixture from runs/fresh_20261110_093150. DEC-9 story ledger uses the same event identity.
- ORCHESTRATOR NOTE 05:40: deliver the corrected Nov 10 re-cut (gated + Telegram) and the A/B/C options
  before any further Phase 1 refinement; heimdall panel = deepseek + qwen27b (+ Grok via cross-LLM);
  batch related diffs into one audit. In progress: Phase 2 + Phase 3 + 4a code audited as ONE batch
  while the 4a PIN run renders; then 2 commits (Phase 2 vertical; Phase 3 + 4a).
- 4a PIN (frozen local 5-min windows, runs/recut_sources_20261111, sha-pinned, machine cuts by the law):
  hook Yahoo 47.31-57.37 ("...bounced very nicely ... around $74,000 ... 50-weekly MA ..."),
  clip_01 DataDash 143.62-161.67 ("...really nice decline here on Bitcoin, okay? 16 % so far ..."),
  clip_02 Natalie 24.65-37.87 ("...NASDAQ fell even harder, dropping 5.5 % ... concentrated in AI.").
  Her ETF/price sentences have no >= 140 ms pause anywhere in her first 5 min (not cuttable).
- Committed + pushed: 1a b6e7d436, 1b+1c 99add647, 1e 3641440f, 1d 9ad93344, DEC-1 9aa4fdb2,
  1d follow-up 0449a3ce, DEC-1 follow-up d10832cb, 1b fix a1e732e1 (model adjudicator removed: it
  rubber-stamped 19/19 Yahoo gaps; punctuation from a second ASR decode, E-FAIL-013).
- Working tree, uncommitted: Phase 2 (vertical auto layout, SCRFD pinned, G4s band-correlation safe-frame
  test, stack band_cy, caption note), Phase 3 (transitions; ffmpeg 4.4.2 xfade put the dissolved-into
  clip's picture 1 frame behind its sound; fixed + content test), 4a (G18 word_diff edges+identity,
  verify_pack stage, telegram.deliver_run, transition_options, scripts/pulse_check_run.sh, RUNBOOK).
- Law 22 re-render with all of the above in the tree: running (runs/v2f_20261111_103004).
- Full suite: 284 passed; 2 failures pre-existing LLM editorial tests (same failure at 3641440f).

## OPEN DECISIONS FOR THE ORCHESTRATOR (evidence; work continues meanwhile)

**OD-1 G12/G15 misfire on correct credit cards (DEC-7).** With the render fixed (real square
avatars from the registry; rings measured 0.999), the UNCHANGED gates still fail the rebuilt Nov 10
card: 16:9 G12 counts 5 "circles" — the extra ones sit on Natalie Brunell's real avatar's ORANGE
background (G12's red mask R>100, R>G+40, R>B+40 includes orange); 9:16 G15 fits a 0.457 ellipse at
(481, 1076) = the middle channel's NAME LABEL text, not a ring. Yesterday's 9:16 G15 failure was the
same label contour. So G12/G15 are content-sensitive; a story crediting such a channel cannot pass
them unchanged. Not changed (mission 1e, DEC-7, M2). If re-specified, the rings-only measurement
would no longer see warped avatar CONTENT, so D4 is now guarded deterministically before render
(shoutout.validate_avatar: square + registry sha prefix; tests in pipeline/test_pulse_20261110_mustfail.py).
Evidence: scratch renders of the rebuilt card, g12_circles overlay (circles on the orange background).

**OD-2 G16/G17 not calibrated to v2f (DEC-1 applied to G3c/G5/G8/G9 only).** v2f predates the
sentence law and fails it on all four segments (table below). Calibrating would set lead/tail to 0 ms
and admit mid-sentence starts, i.e. re-admit D1-D3; PBX's own v2f record calls clip_01's out edge a
ONE-TIME exception with "the 60 ms rule unchanged". New renders must meet the law; v2f stays the
approved legacy reference for everything else.

**OD-3 Prepare-stage picture fidelity is ungated (late Heimdall finding on DEC-1, measured).** G8
compares the final against the PREPARED clip (its pre-DEC-1 approved "relative reference"), so it
measures the render stage only. Measured at G8's own sample instants: on the approved v2f, prepare
(lanczos to 1920x1080, NVENC QP 20) keeps only 0.696 (clip_02) / 0.760 (hook) of the original
download's Laplacian variance (largely grain removal); Nov 10 keeps 0.985-1.040. With the original
download as G8's source the APPROVED reference would fail the unchanged 0.85 ratio (0.689 / 0.770), so
that wiring would need a ratio calibration (an acceptance change) — not taken. Decision for the
orchestrator: gate prepare fidelity (and against what), or accept it as part of the approved look.
Evidence: docs/audits/pulse-sentence-law/dec1_calibration/HEIMDALL_RUN_FRESH_RESPONSE.md.

**OD-1 (addendum, run 6, 2026-11-11 08:40).** Same class again: 16:9 G15's only "squished ring" is the
capital N of "Natalie Brunell" (contour bbox 31 x 36 px; fitted ellipse 122 x 212 passes the size filter,
which tests the ellipse not the contour); 9:16 at (324,1515) the same glyph. Overlays:
docs/audits/pulse-sentence-law/od1_g15_evidence/. Any card crediting "Natalie Brunell" fails G15 unchanged.

**OD-4 G9 tail luma measures encoder lift on a black-ending card, not the content.** The tail is the
hash-identical locked outro. Decoded directly, its last second has luma 12.69; finals measure 14.31
(run 6) / 14.34 (v2f) / 14.74 / 14.77 (9:16) because the final re-encode lifts near-black. DEC-1 set the
floor 0.006 under v2f's own value (14.33 / 14.77), smaller than the 0.03 encode-to-encode difference, so a
correct render passes or fails by encoder state; a lossless outro would fail outright (12.69). Decision:
what G9 should measure on a locked black-ending outro (e.g. hash/identity of the outro region, or the
floor with an encode margin). Not changed.

**OD-5 G17a counts noise-gated digital silence as "not genuine".** DataDash's source pauses sit below the
-100 dBFS digital floor (noise gate). Run 6 clip_01 has 320 ms of silence before "But", of which 60 ms is
above -100 dBFS, so G17a reads lead 60 ms < 80. Moving the in-point or the room-tone pad cannot change
that reading. Decision: is gated digital silence inside a source pause (not at a file head, where D1
lives) genuine quiet for G17a? Not changed; selection avoids such edges meanwhile.

**OD-6 G3 judges ONE first word from a context-free ASR of the clip head.** Run 6: 'bye!' / 'no' for
"But" (hook, clip_01) while G18's word-for-word edges (full-context ASR) and G17b's first-word acoustic
ratio (0.98 / 0.95) show the word intact. Short function words fail G3 by ASR, not by render. Decision:
keep G3 as is (selection then avoids conjunction-opening clips), or measure the first word with context.
Not changed.

**OD-7 G14 0.5 s audio windows under the music bed.** Run 6's one scored G14 miss is a window in
DataDash's quiet passage (speech -39 dB median vs his -28..-32 elsewhere) matched 4.6 s away at xcorr
0.42 (>= the 0.3 'conclusive' bar); every other sample of the 16:9 matched exactly. A quiet source under
the bed weakens the correlation. Not changed; G5 loudness work (segment levels) would also raise the
speech-to-bed ratio there.

## 1f — the gate suite on the frozen v2f reference (2026-11-11, scratch copy, production stage_gates)

| gate | format | v2f measured | threshold | approved video shows the defect, or gate stricter than approved? |
|---|---|---|---|---|
| G3c acoustic tail | both | hook: tail rise to −31.4 dB vs speech −21.7 dB → "onset"; passes at depth ≤ 11.63 dB (16:9) / 11.65 dB (9:16) | valley ≤ speech−12 dB, no sustained rise | stricter than approved (REFERENCE_v2f: output fades to −87 dB at 9.52, next word 9.60) → DEC-1 |
| G5 true peak | 9:16 | −1.3 dBFS | ≤ −2.0 | stricter (REFERENCE: "9:16 peak −1.3 dB, approved as reviewed") → DEC-1 |
| G8 sharpness floor | 16:9 / 9:16 | worst segment medians 27.56 (hook) / 10.84 (clip_03) | ≥ 60 | stricter (soft source cameras, approved) → DEC-1 |
| G9 tail luma | 16:9 / 9:16 | 14.3357 / 14.7715 | > 20 | stricter (locked PBX outro ends on black, approved) → DEC-1 |
| G16 sentence boundary | both | hook lead 40 ms genuine, no pad; clip_01 in 238.55 is 80 ms after the pause before 'The', out has no ≥80 ms pause before 'So'; clip_02 no pause before 'One'; clip_03 starts mid-sentence ('of \| a prison'), out 20 ms after 'have.' | sentence law (2026-11-11) | approved video SHOWS the defects the new law prohibits → not calibrated (OD-2) |
| G17a onset/tail | — | leads 40/40/0/190 ms, tails 150/40/190/0 ms | ≥ 80 ms | same → not calibrated (OD-2) |
| G17b edge words | both | PASS (render faithful) | ≥ 85 % | — |
| G1-G2, G3, G3b, G4, G6, G10-G15 | both | PASS | unchanged | — |

## Rule → check → proof

| PBX rule | Enforcing check (code) | Must-fail proof | State |
|---|---|---|---|
| Clip starts on the first word of a sentence | G16 SENTENCE_BOUNDARY IN edge (pipeline/sentence_law.py gate_g16, pre-render stage `sentence_law` + final gate row) | T pulse_20261110: D3a clip_01 '81', D3b clip_02 'days' | enforced (99add647) |
| Clip ends on the last word of a sentence | G16 OUT edge | T pulse_20261110: D2 clip_01 runs into "All right…" | enforced (99add647) |
| Expected words fixed at selection, never recomputed | G16 selection-lock check (sha-sealed lock in edl.json vs cuts_final expected words) | T pulse_20261110: TestTautology | enforced (99add647) |
| A sentence boundary needs evidence: punctuation from the audio, never a model's opinion of one gap | sentence_law.boundary (an unpunctuated stretch has no boundary, fail closed); pipeline/punctuation.py (marks from a second, prompted ASR decode of the same audio onto aligned verbatim words) | T pulse_20261110: TestUnpunctuatedTranscript (the 19/19 'sentence ends' of the removed adjudicator, 'the | Wolf' etc., are rejected), TestPunctuationLayer | enforced (1b fix) |
| A cut never adds/drops a word; snapping only inside the gap | sentence_law.write_lock_cut_table (cuts placed only inside the locked sentence's heard gap, DEC-10; cut_accept unchanged on every edge not cut at the envelope minimum); ±2 s snap + recompute removed | T: test_run_fresh_has_no_recompute_sync_or_wide_snap | enforced (99add647) |
| No clipped onset at the start of playback (file head / hook: ≥ 80 ms genuine lead-in or the room-tone pad; D1, unchanged by DEC-10) | G17a hook lead (HEAD_LEAD_MIN_S); G16 file-head pad rule | T pulse_20261110: D1 hook (60 ms genuine lead-in) | enforced (99add647) |
| Edge timing inside the video calibrated to the approved v2f, not a silence quota (DEC-10 a-b) | LEAD_MIN_S / TAIL_MIN_S / PAUSE_MIN_S / GUARD_S = 0 ms (v2f's measured worst, DEC-10a table); G16 legal range = the heard gap | T test_dec10_edges: every v2f edge passes (3 recorded by measurement must fail) | enforced (ae965c95) |
| No audible part of the neighbouring word (DEC-10 c-ii); a short gap is cut at the envelope minimum with a 2-frame fade (DEC-10 d) | sentence_law.neighbour_clear in accepted_cut and in G16 with the cut's own fades; run_fresh.stage_cut defers an edge cut at the minimum to G16 instead of cut_accept's M19 quota | T test_dec10_edges: a cut inside a word is audible; v2f clip_01 OUT / clip_02 IN fail; valley fixture; stage_cut deferral; T pulse_20261110 D2 (Natalie run-in) fails | enforced (ae965c95, 29299ea5) |
| Edge words keep ≥ 85 % in the render | G17b on both finals | T: TestG17bRenderedEdges (muted onset fails, 20 ms fade passes) | enforced (99add647) |
| Round credit avatars of the channels actually used | G12 (count), G15 (ring aspect, continuity), R6 (credits == EDL channels, unique avatar hashes), shoutout.validate_avatar + registry-only avatars | T: TestD4Credits (yesterday's card fails G12/G15; thumbnail refused; v2f passes) | enforced (3641440f) |
| On-brand transitions between channels only | pipeline/pulse_transitions.plan (different channels only, never at the open, overlap only inside measured non-speech) + concat (frame-locked xfade/acrossfade); G14/G11/loudness gates on the final | T: test_transitions (planner rules; dissolve over silence only; picture and sound of the dissolved-into clip start together; C insert 8 frames < 0.35 s, red line on black) | enforced (Phase 3) |
| Speaker-centred vertical; safe frame only for screen / unidentifiable speaker, flagged | stage `layout` (vertical_layout.classify: SCRFD-10G, sha-pinned; per-shot classes) -> render_vertical.reframe_auto; G4s LAYOUT TRUTH (each shot label = the re-measured majority class; a 9:16 shot is the safe frame iff labelled screen/uncertain, band correlation >= 0.90); G4 per shot (unchanged gate_g4 rules); EDL `vertical_layout`; caption `vertical_layout.layout_note` | T: TestSafeFrameTruth (D5: Yahoo's talking head as safe frame fails), TestLayoutTruth (talking head mislabelled as screen fails, DEC-2), TestCaptionNote, TestStackGeometry, test_pinned auto for every channel status | enforced (Phase 2); caption wired in 4a |
| Sparse VO with 1 s lead-in | G6 pre-roll (onset ≥ 0.95 s), R4 VO ≤ 25 %, M20 editorial gate | existing tests (test_round2_mustfail, test_editorial_gate) | enforced (pre-existing) |
| No brand sting at the open | pulse_transitions.plan never adds anything before the first segment; C is an insert BETWEEN channels only | T: test_transitions TestConcat C timeline starts with the hook at 0.0 | enforced (Phase 3) |
| 1080p (1920x1080 / 1080x1920) | G5 tech (dims, SAR, fps), clip_contract | test_round2_mustfail G5 | enforced (pre-existing) |
| Transcript of the final == intended sentences, word for word | G18 (pipeline/word_diff.py): each clip's first/last two words == its lock's, and its words == the source span's (same ASR, canonicalised numbers/repeats); full diff vs the lock reported | T: test_word_diff (yesterday's clip_01 fails edges + identity, clip_02 fails the start edge) | enforced (4a) |
| The finished video LOOKS right: credits avatars round and the channels used; speakers centred or layout=screen flagged; no letterbox on talking heads; no frozen/black/duplicate frames at joins; watermark present; nothing of the next shot before a transition | verify stage: qa/contact_sheet_<fmt>.jpg (2 s stills, +-3 frames at every boundary, full-resolution credits and 9:16 first frames) + the fixed checklist answered FROM the sheet by the Heimdall vision panel (qwen3.8-27b + nemotron-3.5-super-vl; any no or missing = V1_visual_checklist FAIL = HOLD); supervised sessions also read the sheet themselves (REPORT.md) | T: test_visual_check (verdict rules, sheet contents, live must-fail on yesterday's vertical sheet) | enforced (orchestrator note 06:20) |

## Findings recorded so far (evidence, 2026-11-11)

- **The 1b per-gap model adjudicator was a rubber stamp** (found 2026-11-11 while enumerating the Nov 10 recut windows): gemma3:27b called 19 of 19 Yahoo Finance gaps sentence ends ('the | Wolf', 'of | all', 'is | up'), each with a real 90-770 ms pause, so G16 would have passed mid-sentence cuts in any unpunctuated source. Removed; punctuation now comes from the ASR (E-FAIL-013). With it, Yahoo's window has exactly two cuttable sentence ends ('hack.' 770 ms, 'times.' 350 ms), and the Nov 10 clip_02 start ('of course' | 'of course') is not a sentence start at all.
- D3's third edge (clip_02 out 34.36) is **not** a defect: pause 34.08-34.43 (75 dB deep), the 'I' onset
  is at 34.44; whisper on the prepared clip ends "...many times." The transcript word 'i' 33.92-34.46 is
  a whisper timestamp error. 4 of 6 edges broke the sentence law, not 5.
- D1 is a **source lead-in** problem, not the render: the 'B' onset sits at 85-90 ms in every stage,
  level-identical to the source; the source has 33 ms of codec zero then ~50 ms of room tone.
- D2/D3 root causes: (1) `_download_window` requested `*54-100` but recorded offset 53.57 (and 23 vs
  23.38): every canonical->file time was shifted 0.38-0.52 s; (2) `_find_word_boundaries` picked the
  nearest word, not a sentence start; (3) the ±2 s snap + edge-word recompute (ad7295ea/4cf5a31a)
  validated whatever the moved cut contained; (4) R9/R10 never ran in production (validate_edl was
  called without transcripts; R10 is advisory and always returns True).
- D4 root cause: shoutout._fetch_avatar_on_demand fell back to the 1280x720 VIDEO thumbnail; the frozen
  renderer resizes every avatar to a square. G12/G15 caught it; the QA_GATE_HOLD reclassification was
  wrong. 70 of 75 registry channels had no verified avatar.
- cut_accept (unchanged) uses a fixed speech-25 dB quiet line: on music-bedded sources (DataDash, bed
  ~24 dB under speech) it reads the bed as speech, so the Nov 10 hook's out edge can satisfy either the
  80 ms tail rule or cut_accept, never both -> that window is rejected (fail closed), not forced.

## Decisions (orchestrator, delegated by PBX 2026-11-11)

Received 02:50 ET. Recorded verbatim in substance; implementation status tracked above and below.

- **DEC-1 Reference calibration.** PBX's approved v2f (16:9 and 9:16) is by definition passing (Law 22).
  For any gate the frozen v2f reference outputs FAIL today: show measured vs threshold on the reference,
  then set that gate's threshold to exactly the reference's measured worst value (no extra margin), in a
  named constant citing the reference file and measurement, plus a test asserting the reference passes
  and a must-fail fixture just beyond it. The ONLY permitted change to gate acceptance; only for gates
  the approved reference fails; audited. Each calibrated gate, old and new value, listed here.
- **DEC-2 Screen-share hooks allowed.** Deterministic layout class "screen" (largest detected face under
  a fixed fraction of frame area across samples, or no face), recorded in the EDL. G4 as written for
  talking-head layouts; for "screen": content is the shared screen, vertical uses the wide safe frame,
  caption/EDL say layout=screen. Must-fail test: a talking-head clip mislabelled as screen.
- **DEC-3 Soft cameras.** Covered by DEC-1 if the reference is equally soft; otherwise prefer the sharper
  window when two legal windows score within 0.5; do not reject a clip for source softness alone when
  render/source sharpness ratio >= 0.85.
- **DEC-4 Transition default.** Sentence-aligned cuts with a 6-frame cross-dissolve and matching audio
  crossfade between segments from different channels (variant B without the thump). Still build A, B
  (soft pulse) and C (red pulse-line wipe) once on the corrected Nov 10 cut; send the three to Telegram
  labelled as options; do not block on the answer.
- **DEC-5 Vertical.** Speaker-centred reframe default; stacked bands for 2-3 person layouts; safe frame
  only for layout=screen or when the speaker cannot be identified, flagged in EDL and caption.
- **DEC-6 Sources.** Approved partner channels only (the pipeline/channels.json registry). No guest
  sources until the radar exists.
- **DEC-7 Credits rings.** The gate was right; fix the render.
- **DEC-8 Done means:** (a) the corrected Nov 10 story passes every gate with no waiver and its transcript
  diff is exact; (b) THREE fresh stories in a row via one command (run_fresh.py, auto mode, no pinned
  file, no hand step) at one identical git HEAD, each passing every gate, each delivered to Telegram as
  "HOLD FOR APPROVAL - all gates passed, no waivers"; (c) docs/RUNBOOK_PULSE_CHECK.md; (d) a cron-ready
  wrapper scripts/pulse_check_run.sh (flock, logging, pipeline_ tmux-safe), NOT installed in cron. A HOLD
  for "no producible story" is valid only with a full rejection ledger; it neither counts nor resets. A
  HOLD from a pipeline defect: fix, audit, the count restarts.
- **DEC-9 Stories.** The engine's own top Bitcoin story each time, runs >= 3 hours apart or on different
  story universes so they are genuinely different stories.
- **DEC-10 Edge timing (orchestrator 10:35 ET).** The sentence law's TIMING constants are calibrated to the
  approved v2f reference and to what a listener hears, not to a silence quota (the 80 ms lead / tail /
  pause minimums of the 01:50 order were picked without evidence). (a) Measure on frozen v2f, both formats,
  every segment edge: the source gap between the kept edge word and its neighbour, the rendered lead before
  the first onset and tail after the last offset, the edge-word duration ratio; table here. (b) PAUSE_MIN_S,
  LEAD_MIN_S, TAIL_MIN_S = the reference's measured worst (named constants citing the measurement), DEC-1
  mechanism + audit; must-pass: every v2f edge. (c) Stays strict: (i) first/last word >= 85 % of its
  transcript duration in the render; (ii) NO audible part of the neighbour word in the kept lead/tail
  (neighbour energy below the valley threshold; the cut at the envelope minimum between the two words);
  (iii) sentence-complete first/last word locked at selection; (iv) G18 word-for-word. Yesterday's three
  defects (half "Bitcoin", Natalie into "All right, you've probably seen people celebrating", a clip
  starting on "81") must still FAIL. (d) A short inter-sentence gap: cut at the envelope minimum with a
  2-frame audio fade in/out instead of rejecting; reject for edges only if (i)-(iii) cannot be met. (e)
  Re-run the Nov 10 lineup: expected hook DataDash 0.00-9.10, clip Natalie "It went from above 81,000 ...
  this week.", clip Yahoo from the true start of the "bitcoin dropped pretty massively" sentence to "...many
  times."; report the exact failing measurement for any that still fails. (f) Render, all gates, sheets,
  Telegram ONLY on a clean pass, plus options A/B/C. TIME BOX 13:00 ET: then write what blocked it and go to
  4b on a fresh story with the same code.

### DEC-10a — v2f edge timing, measured (2026-11-11 10:45, sentence_law's own level/onset functions)

Source (runs/v2f_20261111_103004 sources/transcripts/cuts; valley threshold = local speech - 12 dB):
| segment | edge | kept word / neighbour | acoustic gap | longest quiet run | kept (lead / tail) | cut to neighbour |
|---|---|---|---|---|---|---|
| hook | in (file head) | "The" | - | 70 ms | 70 ms | - |
| hook | out | "Today," / "I'm" | 240 ms | 10 ms | 160 ms | 80 ms |
| clip_01 | in | "The" / "Yeah." | 30 ms | 30 ms | 40 ms | -10 ms (cut inside "Yeah."'s decay) |
| clip_01 | out | "magnitude." / "So" | 60 ms | 10 ms | 20 ms | 40 ms |
| clip_02 | in | "One" / "approximately." | -10 ms (abutting) | 0 ms | 0 ms | -10 ms |
| clip_02 | out | "Now," / "10" | 330 ms | 300 ms | 210 ms | 120 ms |
| clip_03 | in | "prison" / "a" (mid-sentence) | 280 ms | 230 ms | 190 ms | 90 ms |
| clip_03 | out | "have." / "It's" | 440 ms | 360 ms | 10 ms | 430 ms |
Prepared clips (G17a): lead 40 / 40 / 0 / 190 ms, tail 150 / 40 / 190 / 0 ms. Edge-word ratio (G17b): PASS
(>= 0.85) on every edge (1f). => worst: pause 0 ms, lead 0 ms, tail 0-10 ms, gap -10 ms: the timing
minimums calibrate to 0; DEC-10 (c)(i)-(iv) carry the protection.
Conflict recorded: v2f's hook (file head, 70 ms genuine quiet in the source, 40 ms in the prepared clip, no
pad) and yesterday's D1 hook (file head, 60 ms, no pad: "half Bitcoin") are on the same side of any lead
threshold, and G17b passes yesterday's render; so D1 keeps failing on the FILE-HEAD pad rule
(HEAD_LEAD_MIN_S = 80 ms, separate constant; the D1 fix PBX heard) and v2f's hook head is the one approved
edge that rule fails (as recorded in 1f / OD-2). Every other v2f edge must pass.
G5 note for DEC-10e: hook 9.08 s + 0.25 s pad + Natalie (as written: 5 sentences, 16.76 s) + Yahoo 18.70 s
= 44.8 s of content; with the credits card (~9.0 s) and the outro (4.46 s) ~58.3 s < G5's 60 s.

### Calibrated gates (DEC-1)

| gate | constant (segment_v1/qa_gates.py) | old value | new value (= v2f measured worst, per format) | reference measurement | commit |
|---|---|---|---|---|---|
| G3c acoustic tail | G3C_VALLEY_DEPTH_DB | 12.0 dB | 16:9 11.63, 9:16 11.65 | strictest depth at which the v2f hook tail passes: 11.6301 / 11.6543 | DEC-1 commit |
| G5 true peak | G5_TRUE_PEAK_MAX_DBFS | -2.0 dBFS | 16:9 -2.0 (unchanged, passed at -2.2), 9:16 -1.3 | segment_vertical.mp4 ebur128 true peak -1.3 | DEC-1 commit |
| G8 sharpness floor | G8_SHARPNESS_FLOOR | 60 | 16:9 27.56, 9:16 10.84 | worst segment medians: 16:9 hook 27.56, 9:16 clip_03 10.84 | DEC-1 commit |
| G9 tail luma | G9_LUMA_FLOOR | 20 (strict >) | 16:9 14.33, 9:16 14.77 (strict > kept) | 14.3357 / 14.7715 (locked outro ends on black) | DEC-1 commit |

Also in the DEC-1 commit (measurement wiring, not acceptance): G8 was never given source clips in
production, so it ALWAYS failed "no_source" and was waived as FLAG. It now gets the prepared clips
(16:9) and the reframed vertical clips (9:16) - the reference then fails only the floor, which is what
was calibrated. DEC-3 (soft source judged by render/source ratio >= 0.85 alone) is inside gate_g8.
The G8 FLAG and the G9 "approved known exception" rows are gone (DEC-8: no waivers).
