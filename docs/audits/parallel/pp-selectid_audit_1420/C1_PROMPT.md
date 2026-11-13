# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1420
# Branch: pp-selectid
# Generated: 2026-11-13 14:39 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1420/C1_STEP.diff (474 lines)
```
   1 | diff --git a/pipeline/candidates.py b/pipeline/candidates.py
   2 | new file mode 100644
   3 | index 0000000..b1530ae
   4 | --- /dev/null
   5 | +++ b/pipeline/candidates.py
   6 | @@ -0,0 +1,118 @@
   7 | +"""RULING 66 (orchestrator 13:18 Nov 13; its standing part ruled 14:02): A PASSED LINE-UP IS KEPT.
   8 | +
   9 | +"Any line-up that passes the clips-alone verdict is recorded as a CANDIDATE (clips, order, the verdict, the gated
  10 | +takeaway and title if written) and stays a candidate until one of its clips is delivered, ages out, or fails a gate.
  11 | +Every build first tries the open candidates, newest first, before asking for new angles."
  12 | +14:02: "a candidate whose clips still pass but whose LINE fails again (the takeaway, or the title after ruling 65's
  13 | +extra write) is CLOSED for 6 hours, then may be tried once more with fresh writes; it is closed for good when a clip
  14 | +is delivered, ages out or fails a gate. Open candidates are tried newest first inside the 8 judged line-ups, recorded
  15 | +verdicts free, before any angle is asked."
  16 | +
  17 | +The registry ({"records": [build dirs seeded], "candidates": {key: entry}}) is seeded from the build records
  18 | +themselves (each build's package.json: its tried line-ups, their verdicts and writes), so a candidate is exactly a
  19 | +record's tried entry and package.load_candidate rebuilds it. A try's outcome class comes from package.build
  20 | +(out["candidate"]["class"]):
  21 | +  "package": it became a package (its clips go to a pin)        -> closed
  22 | +  "clip":    a clip left the pool or failed a gate, its clips-alone verdict failed now, or it could not be rebuilt
  23 | +             from its record                                     -> closed for good
  24 | +  "line":    its clips passed but a line failed again            -> resting 6 h, then ONE try with fresh writes;
  25 | +                                                                    a line failing that try too -> closed
  26 | +  "budget":  a budget stopped it before an outcome               -> as it was
  27 | +Pure functions; the driver (tests/package/proof_ledger.py) reads and writes the file."""
  28 | +from datetime import datetime, timedelta
  29 | +
  30 | +RESTING_H = 6.0                 # 14:02: "CLOSED for 6 hours, then may be tried once more with fresh writes"
  31 | +FRESH_SEED = 1000               # the writes of that one more try: seeds no recorded write used (package.build)
  32 | +
  33 | +
  34 | +def key(lineup):
  35 | +    return "+".join(lineup)
  36 | +
  37 | +
  38 | +def _at(s):
  39 | +    return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
  40 | +
  41 | +
  42 | +def new_registry():
  43 | +    return {"records": [], "candidates": {}}
  44 | +
  45 | +
  46 | +def outcome(entry, cls, at, build, why=""):
  47 | +    """Record one try of a candidate and apply ruling 66's rule for its class."""
  48 | +    entry["history"].append({"build": build, "at": at, "class": cls, "fresh": bool(entry.get("trying_fresh")),
  49 | +                             "why": str(why or "")[:300]})
  50 | +    entry.pop("trying_fresh", None)
  51 | +    if cls in ("package", "clip"):
  52 | +        entry["state"], entry["until"] = "closed", None
  53 | +    elif cls == "line":
  54 | +        if entry.get("fresh_used"):
  55 | +            entry["state"], entry["until"] = "closed", None
  56 | +        else:
  57 | +            entry["state"], entry["until"] = "resting", (_at(at) + timedelta(hours=RESTING_H)).isoformat()
  58 | +    elif cls != "budget":
  59 | +        raise ValueError(f"unknown outcome class {cls!r}")
  60 | +
  61 | +
  62 | +def seed(reg, record, source):
  63 | +    """Seed the registry from one build record, once per record (reg["records"]). Every tried line-up that passed the
  64 | +    clips-alone verdict and is not itself a candidate's try becomes a candidate (one per line-up, the earliest record
  65 | +    that passed it). A line-up the record packaged is closed. A record written before the registry existed applies
  66 | +    the outcome of the candidate it tried (its out["candidate"]). -> the keys added."""
  67 | +    if source in reg["records"]:
  68 | +        return []
  69 | +    reg["records"].append(source)
  70 | +    added, at = [], record.get("now")
  71 | +    pk = record.get("package") or {}
  72 | +    packaged = [s.get("moment_id") for s in pk.get("segments") or []]
  73 | +    for i, t in enumerate(record.get("tried") or []):
  74 | +        lu = t.get("lineup")
  75 | +        if t.get("medley_ok") is not True or not isinstance(lu, list) or not lu or t.get("candidate") is not None:
  76 | +            continue
  77 | +        k = key(lu)
  78 | +        if k not in reg["candidates"]:
  79 | +            reg["candidates"][k] = {"lineup": list(lu), "source": source, "index": i, "found_at": at,
  80 | +                                    "state": "open", "until": None, "fresh_used": False, "history": []}
  81 | +            added.append(k)
  82 | +        if lu == packaged and reg["candidates"][k]["state"] != "closed":
  83 | +            outcome(reg["candidates"][k], "package", at, source, "packaged by the build that passed it")
  84 | +    c = record.get("candidate")
  85 | +    if c and not record.get("registry"):                # a try made before the registry: its outcome, once
  86 | +        k = key(c.get("lineup") or [])
  87 | +        if k in reg["candidates"] and reg["candidates"][k]["state"] != "closed":
  88 | +            res = str(c.get("result") or "")
  89 | +            cls = c.get("class") or ("package" if res.startswith("PACKAGE") else "clip")
  90 | +            outcome(reg["candidates"][k], cls, at, source, res or c.get("closed"))
  91 | +    return added
  92 | +
  93 | +
  94 | +def due(reg, now):
  95 | +    """The candidates to try now, newest first (by the time their line-up passed): every open one (its recorded
  96 | +    verdicts and writes, free), and every resting one whose 6 h are over (fresh writes). -> [(key, entry, fresh)]."""
  97 | +    out = []
  98 | +    for k, e in reg["candidates"].items():
  99 | +        if e["state"] == "open":
 100 | +            out.append((k, e, False))
 101 | +        elif e["state"] == "resting" and e.get("until") and _at(e["until"]) <= now:
 102 | +            out.append((k, e, True))
 103 | +    return sorted(out, key=lambda x: (str(x[1].get("found_at") or ""), x[1]["source"], x[1]["index"]), reverse=True)
 104 | +
 105 | +
 106 | +def run_due(reg, now, try_one, lineups, build=""):
 107 | +    """RULING 66: try the due candidates newest first, inside `lineups` judged line-ups (a recorded verdict is free), and
 108 | +    stop at the first package. try_one(entry, fresh, lineups_left) -> (out, cls, why, judged).
 109 | +    -> (the package's out or None, [one summary per try], the judged line-ups left)."""
 110 | +    tries = []
 111 | +    for k, e, fresh in due(reg, now):
 112 | +        if lineups <= 0:
 113 | +            break
 114 | +        if fresh:
 115 | +            e["fresh_used"], e["trying_fresh"] = True, True
 116 | +        out, cls, why, judged = try_one(e, fresh, lineups)
 117 | +        lineups -= int(judged or 0)
 118 | +        outcome(e, cls, now.isoformat(), build, why)
 119 | +        tries.append({"key": k, "source": e["source"], "index": e["index"], "fresh": fresh, "class": cls,
 120 | +                      "why": str(why or "")[:300], "judged": int(judged or 0), "state": e["state"],
 121 | +                      "until": e["until"]})
 122 | +        if cls == "package":
 123 | +            return out, tries, lineups
 124 | +    return None, tries, lineups
 125 | diff --git a/pipeline/package.py b/pipeline/package.py
 126 | index 5f5b4b8..978628c 100644
 127 | --- a/pipeline/package.py
 128 | +++ b/pipeline/package.py
 129 | @@ -2042,7 +2042,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 130 |      RULING 66, A PASSED LINE-UP IS KEPT: candidate (load_candidate) tries ONLY that line-up, after the same pool stages:
 131 |      no angle is asked for (its own angle and back-end), its clips must still form it (candidate_lineup), and it is
 132 |      judged and written with its own seeds, so its recorded calls are served from their recordings; it is never
 133 | -    re-lined or swapped (a failing gate closes it: out["candidate"]).
 134 | +    re-lined or swapped (a failing gate closes it: out["candidate"]). Its outcome class (candidates.outcome) is
 135 | +    out["candidate"]["class"]: "package", "clip" (closed for good), "line" (its clips passed, a line failed) or
 136 | +    "budget". candidate["write_seed"] (ruling 66 at 14:02: a candidate's one more try "with fresh writes") is added to
 137 | +    every write's seed, so no recorded write is served again; 0 (the default) keeps the recorded ones.
 138 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 139 |      t0 = time.time()
 140 |      usd0 = _spent(spend)
 141 | @@ -2177,8 +2180,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 142 |      if candidate is not None:                         # RULING 66 (13:18): A PASSED LINE-UP IS KEPT: its own angle and
 143 |          cand_segs, why_c = candidate_lineup(router, candidate, cleared, ctx.now)   # line-up; no angle is asked for
 144 |          out["candidate"] = {"source": candidate.get("source"), "index": candidate.get("index"),
 145 | -                            "lineup": list(candidate["lineup"]), "closed": why_c}
 146 | +                            "lineup": list(candidate["lineup"]), "closed": why_c,
 147 | +                            "fresh": bool(candidate.get("write_seed"))}
 148 |          if why_c is not None:
 149 | +            out["candidate"].update(result=why_c, **{"class": "clip"})
 150 |              out["why_none"] = f"ruling 66: the candidate is closed: {why_c}"
 151 |              log(f"  {out['why_none']}")
 152 |              return out
 153 | @@ -2374,6 +2379,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 154 |              f"{sum(m['duration_s'] for m in order):.1f} s, added {added}) ({time.time() - t0:.0f} s)")
 155 |          return pk
 156 |  
 157 | +    wseed = int((candidate or {}).get("write_seed") or 0)  # ruling 66 (14:02): a candidate's fresh writes
 158 |      total = 0                                             # ruling 41: line-ups judged in this build, over every angle
 159 |      judged, bad_pairs, spins = {}, set(), 0               # 12:00: verdicts by line-up; ruling 63's unfollowable pairs
 160 |      with ThreadPoolExecutor(max_workers=8) as pool:
 161 | @@ -2491,12 +2497,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 162 |                          break
 163 |                      w_over = package_over(line)
 164 |                      if w_over:
 165 | -                        rec["why"] = w_over
 166 | +                        rec["why"], rec["budget"] = w_over, True      # ruling 66: a budget, not an outcome
 167 |                          break
 168 |                      w_used += 1
 169 |                      try:
 170 |                          wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 171 | -                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup,
 172 | +                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup + wseed,
 173 |                                                      avoid_vendor=writer_avoid or None, other=written)
 174 |                      except NoBridgeFits as e:                  # the seconds rule it out: re-line, no write is paid
 175 |                          if join is not None:
 176 | @@ -2602,7 +2608,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 177 |                          pk, fid, cx, cheap_t, rw = rewrite_alone(
 178 |                              router, slot, pk, fields, fid, [v for v in cheap + fid["violations"]], angle, segs, cleared,
 179 |                              ctx, a_by, sources, levels, writers_v, writers_f, writer_avoid or None,
 180 | -                            seed=7 + w_used + 10 * ai + 100 * n_lineup)
 181 | +                            seed=7 + w_used + 10 * ai + 100 * n_lineup + wseed)
 182 |                          att["rewrite"] = rw
 183 |                          cheap, det, dup, rt_ok, r4_res = cheap_t
 184 |                          log(f"    the {slot} alone (ruling 65): " + ("PASS" if rw.get("passed") else
 185 | @@ -2669,6 +2675,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 186 |                      out["packages"].append(pk)
 187 |                      rec["result"] = "PACKAGE"
 188 |                      break
 189 | +                rec["relined"] = relined                    # ruling 66: a clip was dropped (or a line-up rule)
 190 |                  if not out["packages"] and not relined and ok_m and not med["flagged"] and \
 191 |                          take_failed >= NO_VOICE_AFTER and last_fields is not None and not out.get("budget_stop"):
 192 |                      nv = no_voice(angle, segs, med, last_fields, exception, dropped, rec, ai, n_lineup)
 193 | @@ -2687,6 +2694,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 194 |      if candidate is not None:                             # RULING 66: what became of the candidate
 195 |          t_ = next((t for t in out["tried"] if t.get("candidate") is not None), {})
 196 |          out["candidate"]["result"] = t_.get("result") or t_.get("why") or out.get("why_none") or "not tried"
 197 | +        out["candidate"]["class"] = (                     # candidates.outcome reads it
 198 | +            "package" if out["packages"] else
 199 | +            "budget" if not t_ or out.get("budget_stop") or t_.get("budget") else
 200 | +            "line" if t_.get("medley_ok") and t_.get("attempts") and not t_.get("relined") else "clip")
 201 |      s_est, s_rep = (a - b for a, b in zip(_spent(spend), usd0))
 202 |      out["search"] = {"lineups": total, "limit": lineups, "usd_reported": round(s_rep, 4),
 203 |                       "usd_estimate": round(s_est, 4), "seconds": round(time.time() - t0, 1)}
 204 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 205 | index ed6cbba..2a87046 100644
 206 | --- a/tests/package/proof_ledger.py
 207 | +++ b/tests/package/proof_ledger.py
 208 | @@ -20,7 +20,11 @@
 209 |  Writes tests/package/proof/ledger_<UTC stamp, to the second>/ (a run never writes into an existing one): inputs.json,
 210 |  package.json, package.log, step_a.json and, on a package, MOMENTS_PIN_LEDGER.json.
 211 |  
 212 | -RULING 66 (13:18), A PASSED LINE-UP IS KEPT: --from-candidate BUILD_DIR[:N] tries ONLY the line-up that passed the
 213 | +RULING 66 (13:18; its standing part ruled 14:02), A PASSED LINE-UP IS KEPT: every build first tries the due
 214 | +candidates of the registry (tests/package/proof/CANDIDATES.json, seeded from the build records; pipeline/candidates.py),
 215 | +newest first, inside the 8 judged line-ups (a recorded verdict is free), each as package.build(candidate=...); only when
 216 | +none gives a package are angles asked, with the judged line-ups left. The registry is read (and seeded) before anything
 217 | +is written and saved after the record. --from-candidate BUILD_DIR[:N] tries ONLY the line-up that passed the
 218 |  clips-alone verdict in that earlier build's record (its tried[N]; default the first that passed), after the same pool
 219 |  stages: its own angle, play order and seeds (package.load_candidate), so its recorded calls are served from their
 220 |  recordings and only what is missing is paid for; never re-lined, swapped or a new angle.
 221 | @@ -31,6 +35,7 @@ Usage: python3 tests/package/proof_ledger.py --delivered PIN [PIN ...] [--since
 222 |                         tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json
 223 |  """
 224 |  import argparse
 225 | +import glob
 226 |  import json
 227 |  import os
 228 |  import sys
 229 | @@ -44,6 +49,7 @@ sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
 230 |  sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
 231 |  sys.path.insert(0, HERE)
 232 |  import eligibility as E  # noqa: E402
 233 | +import candidates as CA  # noqa: E402
 234 |  import ledger_build as LB  # noqa: E402
 235 |  import moments as M  # noqa: E402
 236 |  import package as PK  # noqa: E402
 237 | @@ -53,6 +59,9 @@ import proof_saved_runs as PS  # noqa: E402
 238 |  import providers as P  # noqa: E402
 239 |  import speakers as SP  # noqa: E402
 240 |  
 241 | +REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
 242 | +
 243 | +
 244 |  def delivered_pins(paths):
 245 |      """The pins already delivered -> (every clip span {video_id, start, end, pin} for package.usable's overlap check,
 246 |      the newest approved_at, [{path, story_id, approved_at, clips}]). Raises ValueError (or OSError / KeyError /
 247 | @@ -108,9 +117,16 @@ def main(argv=None):
 248 |              with open(os.path.join(cdir, "package.json")) as f:
 249 |                  cand = PK.load_candidate(json.load(f), int(idx) if idx else None,
 250 |                                           source=os.path.relpath(os.path.abspath(cdir), REPO))
 251 | +        reg = CA.new_registry()                          # RULING 66: the candidates, seeded from every build record
 252 | +        if os.path.exists(REGISTRY):
 253 | +            with open(REGISTRY) as f:
 254 | +                reg = json.load(f)
 255 | +        for p in sorted(glob.glob(os.path.join(HERE, "proof", "ledger_*", "package.json"))):
 256 | +            with open(p) as f:
 257 | +                CA.seed(reg, json.load(f), os.path.relpath(os.path.dirname(p), REPO))
 258 |      except (OSError, ValueError, KeyError, TypeError) as e:
 259 | -        print(f"REFUSED: the delivered pins, 'since' or the candidate cannot be read ({type(e).__name__}: {e})",
 260 | -              file=sys.stderr)
 261 | +        print(f"REFUSED: the delivered pins, 'since', the candidate or the candidate registry cannot be read "
 262 | +              f"({type(e).__name__}: {e})", file=sys.stderr)
 263 |          return 2
 264 |      out_dir = os.path.join(HERE, "proof", f"ledger_{now.strftime('%Y%m%d_%H%M%S')}")
 265 |      try:
 266 | @@ -150,14 +166,46 @@ def main(argv=None):
 267 |          f"starts at ${PL.LY_STOP_USD:.2f})")
 268 |      own, used = PL.meter(router), PL.reply_meter(router)
 269 |      t0 = time.time()
 270 | -    res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
 271 | -                   work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 272 | -                   spend=lambda: (own["est"], own["best"]),
 273 | -                   step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 274 | -                   hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
 275 | -                   scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 276 | -                   scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
 277 | -                   candidate=cand)                                                     # ruling 66
 278 | +    kw = dict(delivered=delivered, optout=M.optout_ids(), log=say,
 279 | +              work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 280 | +              spend=lambda: (own["est"], own["best"]),
 281 | +              step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 282 | +              hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
 283 | +              scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 284 | +              scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir))
 285 | +    name, at = os.path.relpath(out_dir, REPO), now.isoformat()
 286 | +    if cand is not None:                                 # --from-candidate: that candidate alone (ruling 66, 13:18)
 287 | +        res = PK.build(router, moments, sources, ctx, candidate=cand, **kw)
 288 | +        k = CA.key(cand["lineup"])
 289 | +        if k in reg["candidates"]:
 290 | +            CA.outcome(reg["candidates"][k], res["candidate"]["class"], at, name, res["candidate"].get("result"))
 291 | +    else:                                                # RULING 66 (14:02): the due candidates first, newest first
 292 | +        last = {}
 293 | +
 294 | +        def try_one(e, fresh, left):
 295 | +            try:
 296 | +                with open(os.path.join(REPO, e["source"], "package.json")) as f:
 297 | +                    c = PK.load_candidate(json.load(f), e["index"], source=e["source"])
 298 | +            except (OSError, ValueError, KeyError, TypeError) as ex:
 299 | +                return None, "clip", f"it cannot be rebuilt from its record ({type(ex).__name__}: {ex})", 0
 300 | +            if fresh:
 301 | +                c["write_seed"] = CA.FRESH_SEED          # "then may be tried once more with fresh writes"
 302 | +            say(f"  RULING 66: the candidate {e['source']} tried[{e['index']}] {e['lineup']}" +
 303 | +                (" with fresh writes" if fresh else "") + f", {left} judged line-up(s) left")
 304 | +            o = PK.build(router, moments, sources, ctx, candidate=c, lineups=left, **kw)
 305 | +            last["out"] = o
 306 | +            return o, o["candidate"]["class"], o["candidate"].get("result"), (o.get("search") or {}).get("lineups", 0)
 307 | +        res, tries, left = CA.run_due(reg, now, try_one, PK.LINEUPS_PER_BUILD, build=name)
 308 | +        say(f"  RULING 66: {len(tries)} candidate(s) tried: " + "; ".join(
 309 | +            f"{t['source']}[{t['index']}] {t['class']} -> {t['state']}" for t in tries) if tries else
 310 | +            "  RULING 66: no candidate is due")
 311 | +        if res is None and left > 0:
 312 | +            res = PK.build(router, moments, sources, ctx, lineups=left, **kw)
 313 | +        elif res is None:                                # every judged line-up went to candidates: no angle asked
 314 | +            res = dict(last["out"], package=None, packages=[],
 315 | +                       why_none="ruling 66: the 8 judged line-ups were spent on candidates; no angle asked")
 316 | +        res["candidate_tries"] = tries
 317 | +    res["registry"] = True                               # its outcomes are in the registry already (CA.seed)
 318 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 319 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 320 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
 321 | @@ -185,6 +233,10 @@ def main(argv=None):
 322 |          f"vendor-reported after this build (before it: ${spent0:.2f})")
 323 |      with open(os.path.join(out_dir, "package.json"), "w") as f:
 324 |          json.dump(res, f, indent=1, default=str)
 325 | +    CA.seed(reg, json.loads(json.dumps(res, default=str)), name)   # this build's passed line-ups join the registry
 326 | +    with open(REGISTRY + ".tmp", "w") as f:
 327 | +        json.dump(reg, f, indent=1)
 328 | +    os.replace(REGISTRY + ".tmp", REGISTRY)
 329 |      logf.close()
 330 |      return 0
 331 |  
 332 | diff --git a/tests/package/test_candidates.py b/tests/package/test_candidates.py
 333 | new file mode 100644
 334 | index 0000000..ae023f5
 335 | --- /dev/null
 336 | +++ b/tests/package/test_candidates.py
 337 | @@ -0,0 +1,105 @@
 338 | +#!/usr/bin/env python3
 339 | +"""RULING 66's standing part (orchestrator 14:02 Nov 13): the candidate registry (pipeline/candidates.py)."""
 340 | +import os
 341 | +import sys
 342 | +import unittest
 343 | +from datetime import datetime, timedelta, timezone
 344 | +
 345 | +HERE = os.path.dirname(os.path.abspath(__file__))
 346 | +REPO = os.path.dirname(os.path.dirname(HERE))
 347 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 348 | +import candidates as CA  # noqa: E402
 349 | +
 350 | +T0 = datetime(2026, 11, 13, 19, 0, tzinfo=timezone.utc)
 351 | +
 352 | +
 353 | +def record(now, tried, package=None, candidate=None, registry=False):
 354 | +    return {"now": now.isoformat(), "tried": tried, "package": package, "candidate": candidate,
 355 | +            **({"registry": True} if registry else {})}
 356 | +
 357 | +
 358 | +def t(lineup, ok=True, cand=None):
 359 | +    return {"lineup": lineup, "medley_ok": ok, **({"candidate": cand} if cand else {})}
 360 | +
 361 | +
 362 | +class TestRegistry(unittest.TestCase):
 363 | +    def test_a_passed_line_up_is_a_candidate_once_and_a_packaged_one_is_closed(self):
 364 | +        reg = CA.new_registry()
 365 | +        self.assertEqual(CA.seed(reg, record(T0, [t(["a", "b", "c"], ok=False), t(["a", "b", "d"])]), "r1"),
 366 | +                         ["a+b+d"])
 367 | +        self.assertEqual(CA.seed(reg, record(T0, [t(["a", "b", "d"])]), "r1"), [])          # a record seeds once
 368 | +        self.assertEqual(CA.seed(reg, record(T0 + timedelta(hours=1), [t(["a", "b", "d"])]), "r2"), [])   # one entry
 369 | +        self.assertEqual((reg["candidates"]["a+b+d"]["source"], reg["candidates"]["a+b+d"]["index"]), ("r1", 1))
 370 | +        CA.seed(reg, record(T0, [t(["x", "y", "z"])], package={"segments": [{"moment_id": m} for m in "xyz"]}), "r3")
 371 | +        self.assertEqual(reg["candidates"]["x+y+z"]["state"], "closed")                  # its own build packaged it
 372 | +        CA.seed(reg, record(T0, [t(["a", "b", "d"], cand="r1")]), "r4")                  # a candidate's own try
 373 | +        self.assertEqual(set(reg["candidates"]), {"a+b+d", "x+y+z"})                     # is never a new candidate
 374 | +
 375 | +    def test_a_try_made_before_the_registry_counts_once(self):
 376 | +        reg = CA.new_registry()
 377 | +        CA.seed(reg, record(T0, [t(["a", "b", "d"])]), "r1")
 378 | +        legacy = record(T0, [t(["a", "b", "d"], cand="r1")],
 379 | +                        candidate={"source": "r1", "index": 0, "lineup": ["a", "b", "d"], "result": "PACKAGE"})
 380 | +        CA.seed(reg, legacy, "r2")
 381 | +        self.assertEqual(reg["candidates"]["a+b+d"]["state"], "closed")
 382 | +        reg2 = CA.new_registry()
 383 | +        CA.seed(reg2, record(T0, [t(["a", "b", "d"])]), "r1")
 384 | +        CA.seed(reg2, dict(legacy, registry=True), "r2")                                # a registry build: no again
 385 | +        self.assertEqual(reg2["candidates"]["a+b+d"]["state"], "open")
 386 | +
 387 | +    def test_the_14_02_rules(self):
 388 | +        e = {"history": [], "state": "open", "until": None, "fresh_used": False}
 389 | +        CA.outcome(e, "budget", T0.isoformat(), "b1")
 390 | +        self.assertEqual(e["state"], "open")                                              # a budget is no outcome
 391 | +        CA.outcome(e, "line", T0.isoformat(), "b2")                                       # a line failed again
 392 | +        self.assertEqual((e["state"], e["until"]), ("resting", (T0 + timedelta(hours=6)).isoformat()))
 393 | +        e["fresh_used"] = True                                                            # its one more try
 394 | +        CA.outcome(e, "line", (T0 + timedelta(hours=7)).isoformat(), "b3")
 395 | +        self.assertEqual(e["state"], "closed")
 396 | +        for cls in ("clip", "package"):
 397 | +            e2 = {"history": [], "state": "open", "until": None, "fresh_used": False}
 398 | +            CA.outcome(e2, cls, T0.isoformat(), "b")
 399 | +            self.assertEqual(e2["state"], "closed", cls)
 400 | +        with self.assertRaises(ValueError):
 401 | +            CA.outcome(e2, "maybe", T0.isoformat(), "b")
 402 | +
 403 | +    def test_due_is_newest_first_and_a_rested_one_gets_fresh_writes(self):
 404 | +        reg = CA.new_registry()
 405 | +        CA.seed(reg, record(T0, [t(["a", "b", "c"])]), "old")
 406 | +        CA.seed(reg, record(T0 + timedelta(hours=2), [t(["d", "e", "f"])]), "new")
 407 | +        CA.seed(reg, record(T0 + timedelta(hours=1), [t(["g", "h", "i"])]), "mid")
 408 | +        CA.outcome(reg["candidates"]["g+h+i"], "line", T0.isoformat(), "b")              # resting until T0 + 6 h
 409 | +        self.assertEqual([(k, f) for k, _, f in CA.due(reg, T0 + timedelta(hours=3))],
 410 | +                         [("d+e+f", False), ("a+b+c", False)])
 411 | +        self.assertEqual([(k, f) for k, _, f in CA.due(reg, T0 + timedelta(hours=6))],
 412 | +                         [("d+e+f", False), ("g+h+i", True), ("a+b+c", False)])
 413 | +
 414 | +    def test_run_due_stops_at_a_package_inside_the_judged_line_ups(self):
 415 | +        reg = CA.new_registry()
 416 | +        for h, lu in enumerate((["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"])):
 417 | +            CA.seed(reg, record(T0 + timedelta(hours=h), [t(lu)]), f"r{h}")
 418 | +        seen = []
 419 | +
 420 | +        def try_one(e, fresh, left):
 421 | +            seen.append((CA.key(e["lineup"]), fresh, left))
 422 | +            return ({"package": "pk"} if e["lineup"][0] == "d" else None,
 423 | +                    {"g": "clip", "d": "package"}[e["lineup"][0]], "why", 1)
 424 | +        out, tries, left = CA.run_due(reg, T0 + timedelta(hours=3), try_one, 8, build="b")
 425 | +        self.assertEqual(out, {"package": "pk"})
 426 | +        self.assertEqual(seen, [("g+h+i", False, 8), ("d+e+f", False, 7)])                # newest first; then stop
 427 | +        self.assertEqual((left, [x["class"] for x in tries]), (6, ["clip", "package"]))
 428 | +        self.assertEqual(reg["candidates"]["a+b+c"]["state"], "open")                    # never reached: still open
 429 | +        out, tries, left = CA.run_due(reg, T0 + timedelta(hours=3), lambda e, f, l: (None, "budget", "", 0), 0)
 430 | +        self.assertEqual((out, tries, left), (None, [], 0))                              # no line-up left: no try
 431 | +
 432 | +    def test_the_fresh_try_is_marked_and_a_line_failing_it_closes(self):
 433 | +        reg = CA.new_registry()
 434 | +        CA.seed(reg, record(T0, [t(["a", "b", "c"])]), "r")
 435 | +        CA.outcome(reg["candidates"]["a+b+c"], "line", T0.isoformat(), "b1")
 436 | +        out, tries, _ = CA.run_due(reg, T0 + timedelta(hours=6, minutes=1), lambda e, f, l: (None, "line", "w", 1), 8)
 437 | +        self.assertEqual((tries[0]["fresh"], tries[0]["state"]), (True, "closed"))
 438 | +        self.assertTrue(reg["candidates"]["a+b+c"]["history"][-1]["fresh"])
 439 | +
 440 | +
 441 | +if __name__ == "__main__":
 442 | +    unittest.main()
 443 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 444 | index b590b0f..33c7418 100644
 445 | --- a/tests/package/test_medley.py
 446 | +++ b/tests/package/test_medley.py
 447 | @@ -1670,6 +1670,26 @@ class TestRuling66Candidate(unittest.TestCase):
 448 |          self.assertEqual(out["tried"][0]["why"], "ruling 66: the candidate fails its clips-alone verdict now: closed")
 449 |          self.assertEqual(out["candidate"]["result"], out["tried"][0]["why"])
 450 |  
 451 | +    def test_the_outcome_class_and_the_fresh_writes(self):
 452 | +        """14:02: the class candidates.outcome reads: "package"; "clip" (closed before any call, or its clips-alone
 453 | +        verdict fails now); "line" (its clips pass, its writes fail). write_seed shifts every write's seed."""
 454 | +        c = PK.load_candidate(self.record(), source="r")
 455 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c).run()
 456 | +        self.assertEqual(out["candidate"]["class"], "package")
 457 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], uncuttable={"y"}, candidate=c).run()
 458 | +        self.assertEqual((out["candidate"]["class"], out["candidate"]["result"][:16]), ("clip", "no longer cleare"))
 459 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], {"clip_02": 2}, Rig.LINE)], [], candidate=c).run()
 460 | +        self.assertEqual(out["candidate"]["class"], "clip")
 461 | +        bad = dict(TestRuling65Caption.OK, ok=False, violations=[{"slot": "takeaway", "rule": "VERDICT_NO",
 462 | +                                                                    "detail": "x"}])
 463 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None, None], fids=[bad, bad],
 464 | +                  candidate=dict(c, write_seed=1000))
 465 | +        out = rig.run()
 466 | +        self.assertIsNone(out["package"])
 467 | +        self.assertEqual((out["candidate"]["class"], out["candidate"]["fresh"]), ("line", True))
 468 | +        self.assertEqual(rig.seeds, [("medley", 8), ("write", 1108), ("write", 1109)])   # fresh writes, the verdict
 469 | +                                                                                          # still its recorded seed
 470 | +
 471 |      def test_exactly_its_clips_never_a_subset(self):
 472 |          ms = [pm("h", "A", 13.0), pm("x", "B", 13.0), pm("y", "C", 13.0), pm("z", "D", 11.0)]
 473 |          rec = self.record(tried=[{"angle": 1, "text": self.TEXT, "lineup": ["h", "x", "y", "z"],
 474 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder of medley packages and sealed pins).
Your role: a strict reviewer of the build driver's selection logic. Only state what you can verify from the diff; if
uncertain, say so; do not guess.

Background (static):
- package.build() screens the pool (cached step A, the clip scorer's verdicts, L-v 2 and CUTTABLE, G17a, hook ratings,
  the second vendor), then asks a writer model for ANGLES. It judges line-ups on the clips ALONE (medley(); a budget of
  8 JUDGED line-ups per build, where a verdict served from its recording is free), writes and gates the passing ones,
  and returns a package or why none.
- The router serves a recorded reply to byte-identical bytes (role, back-end, prompt, max_tokens, seed) as
  cached=True, free and deliverable.
- Ruling 66's first part (audited and committed, 912370bf):
  - package.load_candidate(record, index) rebuilds a tried line-up that passed the clips-alone verdict from an
    earlier build's record (package.json): its angle and the angle's back-end, its clips in order, and its seeds
    (ai, n_lineup).
  - build(candidate=...) then tries ONLY that line-up, after the same pool stages, with its own seeds, so its recorded
    calls are served. It closes the candidate (out["candidate"]) when a clip left the pool, the hook no longer opens,
    exactly its clips no longer form a line-up, or its clips-alone verdict fails now.
  - proof_ledger --from-candidate BUILD_DIR[:N] runs it.

The ruling this diff implements (ORCHESTRATOR, verbatim):
13:18: "66. A PASSED LINE-UP IS KEPT. Any line-up that passes the clips-alone verdict is recorded as a CANDIDATE
(clips, order, the verdict, the gated takeaway and title if written) and stays a candidate until one of its clips is
delivered, ages out, or fails a gate. Every build first tries the open candidates, newest first, before asking for new
angles."
14:02, answering my question: "66, YOUR QUESTION: a candidate whose clips still pass but whose LINE fails again (the
takeaway, or the title after ruling 65's extra write) is CLOSED for 6 hours, then may be tried once more with fresh
writes; it is closed for good when a clip is delivered, ages out or fails a gate. Open candidates are tried newest
first inside the 8 judged line-ups, recorded verdicts free, before any angle is asked. Build it after the re-seal is
out."

The change:
1. pipeline/candidates.py (new, pure functions; the driver does the file I/O). The registry is {"records": [build
   dirs seeded], "candidates": {"id+id+id": entry}}.
   - seed(reg, record, source), once per record:
     - every tried entry with medley_ok True, a list line-up, and no "candidate" flag (not itself a candidate's try)
       becomes a candidate: one per line-up, from the earliest record;
     - a line-up the record packaged is closed;
     - a record written BEFORE the registry (no "registry" flag) applies the outcome of the candidate it tried
       (out["candidate"]): "package" for a PACKAGE result, else its class, else "clip".
   - outcome(entry, cls, at, build, why):
     - "package" and "clip" -> closed;
     - "line" -> resting until at + 6 h, or closed if its fresh try was already used;
     - "budget" -> unchanged;
     - any other class raises.
   - due(reg, now), newest first by found_at: every open entry (fresh False), and every resting one whose 6 h are
     over (fresh True).
   - run_due(reg, now, try_one, lineups, build): tries the due candidates in that order while judged line-ups are
     left (lineups -= judged), applies each outcome, and stops at the first "package". A fresh try sets fresh_used
     first.
2. package.build():
   - out["candidate"]["class"] is "package" | "clip" (closed before any call, the verdict fails now, a clip dropped
     or re-lined) | "line" (its clips passed, at least one write, not re-lined, no package) | "budget" (not tried,
     budget_stop, or ruling 5's per-package budget, now marked rec["budget"]).
   - rec["relined"] is recorded after the writes.
   - candidate["write_seed"] (default 0) is added to every write's seed (write_takeaway, and ruling 65's
     rewrite_alone): "fresh writes" seeds no recorded write used. The clips-alone verdict keeps its recorded seed.
   - out["candidate"]["fresh"] records it.
3. tests/package/proof_ledger.py:
   - BEFORE anything is written (in the existing refusal block, exit 2 on failure), the registry
     tests/package/proof/CANDIDATES.json is read (or started empty) and seeded from every
     tests/package/proof/ledger_*/package.json.
   - Then, without --from-candidate: CA.run_due with try_one = load_candidate from the entry's record. A record that
     cannot rebuild it gives class "clip", with the reason and no build call. Otherwise
     build(candidate=..., lineups=left), with write_seed = 1000 on a fresh try.
   - If no candidate packages: the normal build (angles) with the judged line-ups left. With none left, no angle is
     asked (why_none says so).
   - With --from-candidate: that candidate alone, and its outcome is applied to the registry.
   - The record gets candidate_tries and "registry": True.
   - After package.json is written, the record is seeded (its new passed line-ups join), and the registry is saved
     atomically (tmp + os.replace).
4. Tests: test_candidates.py (6, new) and test_medley (+1: the class for package / clip / clip / line, and the fresh
   seeds 1108 / 1109 with the verdict's seed 8). All 13 suites OK.

Real data (read only): seeding the 38 build records gives 6 candidates.
- Closed as packaged: 07:37's (pin d2657bbe) and 12:22's (the 18:33 PACKAGE, now rendering as 0c68b589).
- Open: 10:48's, 09:22's, 08:39's and 04:05's.
- load_candidate refuses all four open ones ("does not open on its angle's hook (ruling 59 c)": records made before
  ruling 59), so a build closes them as "clip", with that reason, before any pool stage or paid call.

Stated readings (say so if you read the ruling differently):
- K1: "recorded as a CANDIDATE": the build record already holds everything (clips, order, verdict, writes).
  - The registry indexes records and keeps each candidate's state.
  - Seeding from all records makes every line-up that ever passed a candidate, including those from before the
    registry.
- K2: "fails a gate" closes it for good. That covers: a clip left the pool; its hook, line-up rules or clips-alone
  verdict fail now; a clip is dropped (exclusion, L-v 2, CUTTABLE, step A re-screen); and it cannot be rebuilt as
  judged (e.g. it does not open on its angle's own rated hook, ruling 59 c).
- K3: "a LINE fails again": its clips passed now, and at least one write was made and failed its gates without a
  re-line. The first try replays its recorded writes (free; ruling 65 may still rescue a caption or title). Its
  6-hour retry writes with fresh seeds (write_seed 1000), and the clips-alone verdict keeps its recorded seed.
- K4: "inside the 8 judged line-ups": the candidates and the angle build share one budget of 8 JUDGED line-ups.
  Ruling 41's per-build $3 search budget applies inside each build() call; candidate tries are mostly served from
  recordings.
- K5: a candidate never reached (the budget ran out, or a package came first) stays as it was.

Check in particular:
- the 6-hour / one-fresh-try / closed-for-good state machine against the 14:02 text;
- that no candidate is tried twice in one build, and none is re-added after closing;
- that "line" can never be assigned to a clip-level failure, nor "clip" to a pure line failure;
- the budget accounting across candidates and the angle build;
- the driver's read-before-write and the atomic registry save;
- that nothing changes for a build with no due candidate (the normal build, 8 line-ups, write_seed 0).

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

