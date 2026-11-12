# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-12 02:55 UTC
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
- L-n DELIVERY IS THE MEASURE (orchestrator 2026-11-12 '01:50'; PBX 01:43: "pls lock these changes into law"): the pipeline exists to deliver publishable videos, and the one number reported to PBX is videos delivered per day. A HOLD on a day when a line-up that passes our rules existed in the sources is a DEFECT of the selector (a miss), not a safe outcome.
  Check: every HOLD at editorial (or, under L-q, at mining / packaging) runs the blind oracle + judge on that run's universe (pipeline/oracle, branch pp-backtest, once merged); when it finds an accepted line-up the miss is logged with the first stage that lost it (MISS record in the run dir) and goes to the bible. Not yet wired. Tonight's instance: fresh_20261112_050611 HELD at editorial while the oracle's line-up 1 was judged to pass our rules (ORACLE.json sha256 e923e91fa3d05621844449244100ded681c916bf8d06d0aa4a7ec3f9e64bc77a): a miss (E-FAIL-043 family).
- L-o INTEGRITY IS HARD, TASTE BENDS (orchestrator 2026-11-12 '01:50', amended '01:55' with L-q): two classes of rule, never mixed. INTEGRITY (hard, fail closed, never relaxed to ship): (1) every clip is verbatim whole sentences, what is spoken matching the locked sentences word for word (G16 / G18); (2) intact edges: no clipped or faded edge word (G17, L-b); (3) each clip stands alone, or is made to stand by the VO line before it WITHOUT changing its meaning; (4) Bitcoin-only; (5) >= 2 channels per video; (6) recent content (currentness); (7) credits card = EDL set = spoken sign-off set (G12 / G15 / G20, L-a); (8) release authorisation bound to the exact bytes (L-j); (9) nothing measured is never a pass (L-m, branch hardening-redteam); (10) the partner / guest source rule; (11) VO FIDELITY (new, '01:55'): the VO never puts words in a speaker's mouth: it may not attribute to a speaker a claim, stance or number that is not in that speaker's clip, may not imply two speakers were answering each other when they were not, and every fact the VO itself asserts is supported by a clip in the video or a verified source in PROVENANCE; a VO-fidelity check with must-fail fixtures must exist before any moments-first video is labelled a pass. REMOVED from integrity by the '01:55' amendment: 'same development from >= 2 channels' (now one packaging style among several, L-q). TASTE (targets that RANK candidates, never reject one when nothing better exists): the 8-12 s hook and 12-20 s clip duration windows; the hook / clip score floors; a sentence opening on a conjunction ('And', 'So', 'But') when it still stands alone in context. A whole sentence always beats a duration window: selection prefers passages inside the targets, and when no line-up fits inside them it takes the best line-up that passes our rules outside them and records each deviation and its size in PROVENANCE and in the Telegram caption. The only hard duration rule is the format: total runtime 60-70 s (PBX's format).
  Check: EVIDENCE asked by the '01:50' order (no number invented): CLOCK: the windows are measured on SENTENCE-LOCKED WHISPER WORD timing, never caption timing (editorial_select.py:49-50 define them, :1180 applies them; the words come from transcript_store.acquire(prefer_words=True), editorial_select.py:880, and only a sentence_ready record, whisper_words / whisper_words_punct, transcript_store.py:404-410, counts); the blind oracle's durations are caption-line timing, another clock, which a pinned run re-measures on locked words. APPROVED PASSAGES (locked word span): Nov 11 preview hook 9.08 s, clips 12.34 / 18.70 / 16.66 s; v2f hook 9.02 s, clips 10.70 / 11.54 / 14.44 s: PBX approved every length from 9.02 to 18.70 s, two clips under today's 12 s minimum among them; tonight's near-misses missed a window by 0.10-1.86 s (hooks 12.12, 12.74, 7.88, 7.0, 6.14 s; clips 11.9, 11.14, 11.02, 8.74 s). FORMAT: the approved preview's finals run 71.08 s (both formats), 1.08 s over 70; its four passages fill 58.17 s of the final, leaving 12.91 s of VO, cards and transitions. PROPOSAL: no fixed per-passage outer bound (no evidence supports one: nothing was ever rejected for a passage's length, and the approved range already spans 9.02-18.70 s); the one hard bound is the line-up total, checked BEFORE render where the line-up is chosen (selector / packager): passages + VO + fixed cards inside the 60-70 s format, i.e. at the preview's measured 12.91 s of non-passage time, passages totalling about 47-57 s; any per-passage limit is then arithmetic (70 s minus the fixed time minus the other passages), never a constant. For PBX: the approved preview itself ran 71.08 s; whether the format is checked on the final's runtime with a tolerance is PBX's call. WIRING (code change; two audit cycles; must-fail tests proving every INTEGRITY rule still rejects): into the moments-first miner / packager (L-q) and the shared validation (sentence lock, pinned validation); the story-first selector is retired ('01:58'). Until wired, the existing code still applies the windows and floors as hard filters.
- L-p CADENCE (orchestrator 2026-11-12 '01:50'; PBX 01:43: "i need one new video every few hrs once this thing is live and operational. ideally every 3-5 hrs"): once operational the target is one NEW video every 3-5 hours; it supersedes the daily target as the goal, and the daily rate remains the first milestone. No schedule is installed without PBX.
  Check: design consequences, requests and notes, no code yet: (1) NOVELTY: a video is NEW when its development differs from every video delivered in the previous 24 h, or it carries a materially new fact on the same development; the story ledger enforces it (integrity class). Under L-q the proposed reading is: none of its sentence ids was delivered in the previous 24 h and its angle differs from every delivered video's, or it carries a materially new fact (open for the orchestrator). (2) SUPPLY: the 72 h universe barely moves in 3-5 h, so each cycle ingests what was published since the last one and the channel universe must be wide enough; pipeline_pp_backtest is asked (its REQUESTS file) for the DISTINCT developments per day with a line-up that passes our rules, as the oracle finds them in the saved universes. (3) RUN TIME: a full cycle must fit comfortably inside 3 h on GPU0 alone. Measured: tonight's editorial stage took 70.2 min (fresh_20261112_050611, 4213 s): about 50 min of gemma3:27b calls (397 calls, 230 cache hits; reply-cache writes from +1.4 to +70.2 min), about 19 min in three Whisper word passes, each a GPU0 swap (48 h pool +20 to +29 min, 72 h pool +33 to +39, wire pool +64 to +67), under 1 min universe + embeddings (cached). The last complete render path (pinned_20261111_172202) took 51.3 min after selection: render 17.9, gates 15.6, verify 13.4, prepare 1.6, layout 1.2, cut + sentence law + voice 1.1, review 0.6 min. A cycle is about 2 h: inside 3 h, not comfortably (no room for a second candidate after a HOLD). The time goes to model calls (~50 min), render + gates + verify (~47 min) and Whisper swaps (~19 min).
- L-q MOMENTS FIRST, THEN PACKAGE (orchestrator 2026-11-12 '01:55'; PBX 01:48: "i want you to start looking for the stuff that is most social media and engagement friendly. not all segments you clip need to be 100% same exact topic so long as any PBX MAX VO can stitch the two in a logical clever way that actually allows for points to be made etc. perhaps we analyze best of moments across every few hrs new content first.. then decide how to package it and how to optimzie for views etc. now THIS is the strategy"; '01:58': "pls drop the old video and start this new process"): moments-first selection is the product; story-first selection is retired, and the DEC-13 clusters (L-f) become one input, not the gate. STEP 1 MINE: each cycle, over the content published since the last cycle (plus the recent window), find the best MOMENTS: whole stand-alone sentences from partner / guest sources, scored for social engagement (a strong opinion, a surprising number, a quotable line, a named figure, stakes, emotion, a clean hook in the first 2 s), by sentence id, never rewritten. STEP 2 PACKAGE: choose the set of moments that makes the best video and the angle that ties them; the moments need not be the same development: the PBX MAX voiceover stitches them with bridges that make a point, logically and cleverly. STEP 3 OPTIMISE: hook choice, order, title / caption for views. Integrity is L-o's amended class, VO fidelity included.
  Check: a moments-first run replaces the gates that assumed one development (any same-event / topic check on the line-up) with the VO-fidelity gate, ONLY for moments-first runs and only once that gate exists with its must-fail corpus passing; every other integrity gate is unchanged ('01:58'). Build: pipeline_pp_selectid builds the miner and packager (pipeline/moments.py, package.py, trend_brief.py, the VO-fidelity checker) on its ids-only contract (pipeline/select_by_id.py, eligibility.py); pipeline_pp_backtest measures supply under this rule; the integrator wires and audits them when they report DONE. The first delivery goes to Telegram as REVIEW ONLY ('first moments-first package; selection + VO by the new path, not yet merged/audited') with its duration deviations listed per L-o. Not yet built.
- L-r GPU0 NEVER SURPRISES A RUN (orchestrator 2026-11-12 '01:55' B; PBX on the pinned run's out-of-memory: "let's make sure that never happens again. what can we do rn to fix this??"): (1) ONE OWNER: every code path that loads anything on GPU0 (gemma via Ollama, Whisper, the face detector / vision gates, NVENC, the preflight's own model checks, GPU test sessions, the backtest) takes the gpu0.py lease first: no lease, no load; (2) ONE MODEL AT A TIME by construction: one function swap_to(model) unloads whatever is resident (Ollama keep_alive=0 confirmed via the GPU0 listener, torch empty_cache, the Whisper object deleted), then VERIFIES by nvidia-smi that GPU0's free memory is at least the incoming model's known requirement plus margin before loading; every stage calls it, nothing calls a loader directly; the preflight leaves GPU0 as empty as it found it and asserts that; (3) BOUNDED SELF-HEAL, not a silent retry: on CUDA out-of-memory, release everything this run owns, wait until nvidia-smi shows the memory free (timeout), retry the SAME step ONCE, both attempts in PROVENANCE; a second failure is a HOLD naming every process on GPU0 (pid, name, MiB); an out-of-memory never surfaces as a different error: the HOLD reason carries the real cause; (4) FOREIGN PROCESSES: at run start and before every swap, a process using GPU0 memory without the lease HOLDs the run at once, named; nothing is killed that the run did not start; GPU1 stays quarantined and untouched; (5) TESTS: a must-fail that loads a dummy allocation on GPU0 before each stage and proves the stage refuses or recovers as specified, and a test that runs env -> pinned -> render -> gates back to back twice and shows peak GPU0 memory per stage in a table, which every REPORT.md carries from now on.
  Check: in progress; it outranks hardening batches 18 / 19 and must be in place before the first moments-first render ('01:58'). Done so far: stage_pinned releases GPU0 before Whisper (456a440f, E-FAIL-052). The GPU0 paths are enumerated in the DoD (file:line, wired or not). It supersedes branch hardening-redteam's uncommitted GPU0 lease draft (batch 20), which is rebuilt to this law.
- L-s CONTEXT INTEGRITY (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md; a new HARD gate, separate from VO fidelity; the reviewers' unanimous #1 blind spot): a verbatim whole sentence can still misrepresent its speaker once lifted. For every selected moment the inputs are the source's speaker-turn-aware transcript from at least 90 s before (back to the start of the question / turn) to 60 s after, the video's title and description, the selected sentence ids, and the finished package (order, adjacent clips, VO, title, caption). STEP A (context only, the package hidden): a model from a different vendor than the writer states who is speaking; whose view it is (own sincere / attributed to someone else / hypothetical / conditional / sarcastic / question / reading aloud / ad read); the referent of every pronoun and of 'this / that / today'; any governing condition or time frame; any retraction or qualification in the window. STEP B (the package only): what an ordinary viewer concludes the speaker asserts. PASS only if: the speaker's own sincere assertion; every referent inside the clip; no unmet condition and no reversal; the in-context proposition entails the viewer takeaway with the same polarity and no stronger certainty; no implied relation (agreeing / answering / rebutting) between speakers who were not in the same source video, whether by sequence, bridge or title, not only by banned words. Any 'uncertain' is a FAIL. Repair is ONLY extending the clip by whole locked sentences and re-checking, or dropping the MOMENT and repacking; never writing the missing context into the VO.
  Check: must-fail corpus >= 40 (steelman, quoting an opponent, sarcasm, a conditional split across sentences, an unresolved pronoun, 'some people say', a stale 'today / just', an answer without its question, a later retraction, false dialogue by sequence, the wrong speaker) AND a must-pass corpus >= 20 with the false-reject rate reported (a checker that rejects everything is a broken selector). Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-t ALL AUDIENCE-FACING TEXT IS UNDER THE GATES (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md): the title, the caption and any on-screen text are free text exactly like the VO: every number, name and claim is audible in a clip of this video; quotes are verbatim; no stronger certainty; the framing verbs destroys / slams / exposes / admits / confirms / caught are banned unless they are the source's own word; no name of a person who does not appear; no second-person financial imperative. ONE title and ONE caption go through VO fidelity and context integrity (L-s) with the video, and are bound into the release authorisation (L-j) with BOTH files: one manifest holds both renders, the title, the caption, the source intervals, the credits and the gate results; any change after the gates re-runs them.
  Check: release_auth's attested set grows by the title, caption and manifest; telegram.deliver_run sends that one title and caption. Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-u HARD EXCLUSIONS AND SCORING (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md; engagement scoring otherwise selects exactly what burns partners): never auto-selected: accusations of crime / fraud / insolvency / dishonesty against a named person or company; one partner attacking another; buy / sell / leverage imperatives and guaranteed-return claims; single-source 'breaking' factual claims; ad reads and sponsor segments; third-party media played inside a partner's video. Down-weighted and capped: price predictions (at most one per video, always framed as that speaker's prediction, never as fact in the title), doom, politics not about Bitcoin policy. 'Named figure' stops being a positive axis on its own; contempt / outrage is a penalty, not a boost. Per-channel fairness: at most ONE clip per channel per video, at most 20 s per source video, per-channel daily and weekly appearance caps (numbers proposed from the saved universes), topic and speaker cooldowns beyond the 24 h moment rule.
  Check: exclusions in code, before any score (a rank weight is not an exclusion); the cap numbers come from the saved universes (pp-backtest). Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-v SPEAKER AND TRANSCRIPT TRUTH (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md): (1) WHO IS SPEAKING: a moment may not span a speaker change; a person is NAMED in VO / title only when verified (title / description metadata, or diarisation above a stated confidence), otherwise the show is credited. (2) every gate today trusts one Whisper transcript: for the selected sentences only, a second independent recognition pass (a different model / settings) runs against the SOURCE audio; any disagreement on a number, a name or a negation makes that token unusable in VO / title or drops the moment. (3) time-sensitive language ('just', 'today', price levels) requires the source's original publish time inside the window; re-uploads are excluded.
  Check: the second pass is a GPU0 load (law L-r: through gpu0.swap_to); diarisation confidence threshold stated with its evidence. Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-w OPERATING RULES (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md): (1) DIVISION OF LABOUR: the local gemma mines and scores by id; CODE does the duration packing (VO length and the credits absorb the slack, so 60-70 s is met by arithmetic, not by the model); a FRONTIER model picks the angle and writes VO / title / caption; a different vendor rules fidelity and context; measured dollars per video are reported. (2) NO ZERO-VIDEO NIGHTS FROM THE CHECKER: on a VO reject, regenerate once, then fall back to a plain factual VO ('Next, <show> on <topic>.') rather than dropping the package; a package is dropped only for a context-integrity or exclusion failure, and then repacked from the next moments. (3) STORY-FIRST IS KEPT as a preferred package TYPE when >= 2 channels cover one development (the safest format); the packager chooses the type. (4) the trend brief runs in SHADOW first (logged, zero weight) next to a free baseline signal from our own corpus (topic frequency across partner channels, last 24 h); when enabled its weight is capped at ~10-15% of the score, its output forced into a closed Bitcoin topic taxonomy, raw post text never enters any prompt, and a person-trend may boost only moments where that person is the speaker. (5) the Telegram approval message carries, per clip, a link to the source video ~30 s before the clip, the flagged risks, both file hashes, the one title and caption. (6) REPORTED NUMBERS: generated, delivered, approved-without-edit, published, rejected with reason, corrected / challenged; not delivered alone. A hold is a selector defect only when the blind oracle's witness package ALSO passes context integrity, exclusions and fidelity; the oracle runs on selector holds only (not ingestion / GPU holds). No integrity rule is ever demoted to ranking without PBX in writing.
  Check: amends L-n (the reported numbers; the oracle on selector holds only, its witness under L-s / L-u / VO fidelity) and L-q (story-first kept as a package type). The backtest session is asked separately to compare, on the same saved universes, story-first with bent taste rules vs moments-first vs frontier packaging, blind-judged for publishability. Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-x NO SINGLE MODEL, ULTRON FIRST (orchestrator note 2026-11-12 '02:45'; PBX: "work this video pipeline to get us off of any one llm and onto ultron and to be fully autonomous and top notch"): every model role (mining, scoring, packaging / angle, VO / title writing, fidelity verdict, context verdict, trend brief) sits behind ONE provider interface with at least two interchangeable back-ends, and the run continues when any one vendor is down or out of credit (OpenAI ran dry mid-run on Nov 12). The DEFAULT back-end of each role is the local model on Ultron wherever it meets the quality bar; a frontier model or Heimdall is used only where a measured comparison shows local is not good enough, and that comparison is re-run so roles migrate to local as it improves. No role hard-codes a vendor or a model name outside the provider config. Generator and blind judge are always different models.
  Check: per role, a blind A/B on saved data: local gemma3:27b (run by the integrator under the GPU0 lease, law L-r; the builders provide the harness and prompts) vs frontier vs Heimdall: quality verdict, failures, latency, dollars. Heimdall spend: the 90% tripwire is a NOTIFY ('HEIMDALL SPEND AT 90%' at the top of the session's STATE) and the role falls back to its other back-ends; work never halts for the cap. Not yet built (pp-selectid phase 2 and pp-ingest build behind the interface; the integrator runs the local legs).
- AMENDMENTS 2026-11-12 '02:30': L-n by L-w (6) (reported numbers: generated / delivered / approved-without-edit / published / rejected with reason / corrected or challenged; the blind oracle runs on selector holds only, and a hold is a selector defect only when its witness package also passes L-s, L-u and VO fidelity); L-o by L-s and L-t (context integrity and all audience-facing text join the integrity class; an integrity rule is never demoted to ranking without PBX in writing, L-w (6)); L-q by L-w (3) (story-first is kept as a preferred package type when >= 2 channels cover one development; the packager chooses the type).
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

### File: docs/audits/pulse-sentence-law/CURRENT.diff (2830 lines)
```
   1 | diff --git a/pipeline/backtest.py b/pipeline/backtest.py
   2 | index 5ba6215b..066c177d 100644
   3 | --- a/pipeline/backtest.py
   4 | +++ b/pipeline/backtest.py
   5 | @@ -201,17 +201,9 @@ def table(rows):
   6 |      return "\n".join(lines)
   7 |  
   8 |  
   9 | -def main(argv=None):
  10 | -    ap = argparse.ArgumentParser()
  11 | -    ap.add_argument("--runs", nargs="*", help="run dir names (default: every saved universe)")
  12 | -    ap.add_argument("--out", default=os.path.join(RUNS_DIR, "backtest_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")))
  13 | -    a = ap.parse_args(argv)
  14 | -    import story_semantics as sm
  15 | -    days = saved_days()
  16 | -    if a.runs:
  17 | -        days = [d for d in days if os.path.basename(d) in set(a.runs)]
  18 | -    os.makedirs(a.out, exist_ok=True)
  19 | -    registry = json.load(open(os.path.join(PIPELINE_DIR, "channels.json")))
  20 | +
  21 | +def _backtest_days(days, a, registry, sm):
  22 | +    """The GPU0 part of main, run under the lease."""
  23 |      E, L = sm.Embedder(), sm.LocalLLM().start()
  24 |      rows, t0 = [], time.time()
  25 |      try:
  26 | @@ -227,6 +219,23 @@ def main(argv=None):
  27 |      finally:
  28 |          L.stop()
  29 |          E.close()
  30 | +    return rows, t0
  31 | +
  32 | +
  33 | +def main(argv=None):
  34 | +    ap = argparse.ArgumentParser()
  35 | +    ap.add_argument("--runs", nargs="*", help="run dir names (default: every saved universe)")
  36 | +    ap.add_argument("--out", default=os.path.join(RUNS_DIR, "backtest_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")))
  37 | +    a = ap.parse_args(argv)
  38 | +    import story_semantics as sm
  39 | +    days = saved_days()
  40 | +    if a.runs:
  41 | +        days = [d for d in days if os.path.basename(d) in set(a.runs)]
  42 | +    os.makedirs(a.out, exist_ok=True)
  43 | +    registry = json.load(open(os.path.join(PIPELINE_DIR, "channels.json")))
  44 | +    import gpu0
  45 | +    with gpu0.lease(f"backtest {os.path.basename(a.out)} (pid {os.getpid()})"):     # L-r: a GPU0 job holds the lease
  46 | +        rows, t0 = _backtest_days(days, a, registry, sm)
  47 |      print(table(rows))
  48 |      print(f"total {round(time.time() - t0)} s -> {a.out}")
  49 |      return 0
  50 | diff --git a/pipeline/config.py b/pipeline/config.py
  51 | index e87c7dc6..4f9e6482 100644
  52 | --- a/pipeline/config.py
  53 | +++ b/pipeline/config.py
  54 | @@ -135,6 +135,8 @@ def conform_outro(aspect="16x9"):
  55 |      Content-keyed cache: only re-conforms if master hash changes.
  56 |      Returns path to conformed file, or raises FileNotFoundError.
  57 |      """
  58 | +    import gpu0
  59 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
  60 |      if aspect == "16x9":
  61 |          master = OUTRO_MASTER_16x9
  62 |          w, h = WIDTH, HEIGHT
  63 | diff --git a/pipeline/cut_accept.py b/pipeline/cut_accept.py
  64 | index 1a6e31c8..6fd8015a 100644
  65 | --- a/pipeline/cut_accept.py
  66 | +++ b/pipeline/cut_accept.py
  67 | @@ -152,15 +152,10 @@ def spoken_tokens(words):
  68 |      return canon.canon_tokens(" ".join(words))
  69 |  
  70 |  
  71 | -_MODEL = None
  72 | -
  73 | -
  74 |  def _model():
  75 | -    global _MODEL
  76 | -    if _MODEL is None:
  77 | -        from faster_whisper import WhisperModel
  78 | -        _MODEL = WhisperModel("large-v3", device="cuda", compute_type="float16")
  79 | -    return _MODEL
  80 | +    """The process's one large-v3 (L-r: gpu0.whisper loads it through swap_to; any later swap deletes it)."""
  81 | +    import gpu0
  82 | +    return gpu0.whisper("large-v3")
  83 |  
  84 |  
  85 |  def _whisper_words(wav_path):
  86 | diff --git a/pipeline/preflight.py b/pipeline/preflight.py
  87 | index 1009b9ee..847fc8d2 100644
  88 | --- a/pipeline/preflight.py
  89 | +++ b/pipeline/preflight.py
  90 | @@ -20,12 +20,15 @@ import os
  91 |  import shutil
  92 |  import subprocess
  93 |  import sys
  94 | +import time
  95 | +import urllib.error
  96 |  import urllib.request
  97 |  
  98 |  PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
  99 |  REPO = os.path.dirname(PIPELINE_DIR)
 100 |  sys.path.insert(0, PIPELINE_DIR)
 101 |  sys.path.insert(1, os.path.join(REPO, "video_pipeline_v3"))     # relay.get_key (the pipeline's key loader)
 102 | +import gpu0  # noqa: E402  (law L-r)
 103 |  
 104 |  GPU0_FREE_MIB = 20000             # editorial model ~19 GB + Whisper; counted with our own Ollama model released
 105 |  DISK_FREE_GB = 25
 106 | @@ -43,21 +46,15 @@ def _get_json(url, headers=None, timeout=15, data=None):
 107 |  
 108 |  
 109 |  def check_gpu0():
 110 | -    import story_semantics as sm
 111 | -    gpus = dict(l.split(", ") for l in _run(["nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader"])
 112 | -                .stdout.strip().splitlines())
 113 | -    apps = [l.split(", ") for l in _run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_memory",
 114 | -                                         "--format=csv,noheader,nounits"]).stdout.strip().splitlines() if l]
 115 | -    serve = sm.LocalLLM()._listener_pid()
 116 | -    ours = set(_run(["pgrep", "-P", str(serve)]).stdout.split()) | {str(serve)} if serve else set()
 117 | -    others = [(p, m) for p, u, m in apps if u == gpus.get("0") and p not in ours]
 118 | -    if others:
 119 | -        return False, "other job(s) on GPU0: " + ", ".join(
 120 | -            f"pid {p} ({m} MiB) {_run(['ps', '-o', 'args=', '-p', p]).stdout.strip()[:60]}" for p, m in others)
 121 | -    used, total = sm.gpu0_memory()
 122 | -    held = sum(int(m) for p, u, m in apps if u == gpus.get("0") and p in ours)
 123 | -    free = total - used + held
 124 | -    return free >= GPU0_FREE_MIB, f"{free} MiB available with our model released (need {GPU0_FREE_MIB})"
 125 | +    """L-r: no foreign process on GPU0 (gpu0.foreign: anything but this run's processes and the GPU0 Ollama's), and
 126 | +    room for the largest single model swap_to will load (its measured need + margin) once the Ollama's models, ours
 127 | +    to unload, are released."""
 128 | +    foreign = gpu0.foreign()
 129 | +    if foreign:
 130 | +        return False, f"GPU0 is used by something that is not this run's: {gpu0.describe(foreign)}"
 131 | +    used, total = gpu0.memory()
 132 | +    need = max(GPU0_FREE_MIB, max(gpu0.REQUIREMENT_MIB.values()) + gpu0.MARGIN_MIB)
 133 | +    return total - used >= need, f"{total - used} MiB free (need {need}: the largest single model + margin)"
 134 |  
 135 |  
 136 |  def check_ollama():
 137 | @@ -65,9 +62,16 @@ def check_ollama():
 138 |      digest = sm.model_digest(sm.LLM_HOST, sm.LLM_MODEL)
 139 |      if not digest:
 140 |          return False, f"{sm.LLM_MODEL} not installed on {sm.LLM_HOST}"
 141 | -    body = json.dumps({"model": sm.LLM_MODEL, "prompt": "ok", "stream": False,
 142 | -                       "options": {"num_predict": 1}}).encode()
 143 | -    r = _get_json(f"http://{sm.LLM_HOST}/api/generate", {"Content-Type": "application/json"}, timeout=180, data=body)
 144 | +    gpu0.swap_to(f"ollama:{sm.LLM_MODEL}")           # L-r: the model reaches GPU0 only through swap_to
 145 | +    body = json.dumps({"model": sm.LLM_MODEL, "prompt": "ok", "stream": False, "keep_alive": 0,   # unloaded after
 146 | +                       "options": {"num_predict": 1}}).encode()                                  # its answer (L-r)
 147 | +    try:
 148 | +        r = _get_json(f"http://{sm.LLM_HOST}/api/generate", {"Content-Type": "application/json"}, timeout=180, data=body)
 149 | +    except urllib.error.HTTPError as e:
 150 | +        text = e.read().decode(errors="replace")
 151 | +        if gpu0.is_oom(RuntimeError(text)):                # named as what it is, never 'HTTPError (raised)'
 152 | +            raise gpu0.GpuOOM(f"{sm.LLM_MODEL}: CUDA out of memory (HTTP {e.code}: {text[-300:]})") from None
 153 | +        raise
 154 |      return "response" in r, f"{sm.LLM_MODEL} {digest[:12]} answered"
 155 |  
 156 |  
 157 | @@ -149,6 +153,8 @@ def run_checks(checks=None):
 158 |      for name, fn in (CHECKS if checks is None else checks):
 159 |          try:
 160 |              ok, detail = fn()
 161 | +        except gpu0.Gpu0Stop as e:                    # a GPU0 refusal names its cause (pids, MiB; never a secret)
 162 | +            ok, detail = False, f"GPU0 {type(e).__name__}: {e}"
 163 |          except Exception as e:                        # an exception is a failed check, never a pass; reported by
 164 |              ok, detail = False, f"{type(e).__name__} (raised)"   # TYPE only: a network error's text can carry a
 165 |                                                                    # key or token in its URL (claude-fable audit #6)
 166 | @@ -156,8 +162,37 @@ def run_checks(checks=None):
 167 |      return out
 168 |  
 169 |  
 170 | +def left_as_found(found_used, found_models, wait_s=60, slack_mib=256):
 171 | +    """L-r item 2: (ok, detail): GPU0 holds no more than the preflight found (memory within slack_mib of it, no Ollama
 172 | +    model that was not resident before), waiting up to wait_s for an unload to land."""
 173 | +    t0 = time.time()
 174 | +    while True:
 175 | +        used, _ = gpu0.memory()
 176 | +        resident = gpu0.ollama_loaded()
 177 | +        extra = sorted(set(resident) - set(found_models))
 178 | +        if used <= found_used + slack_mib and not extra:
 179 | +            return True, f"GPU0 at {used} MiB (found at {found_used} MiB); Ollama resident now {resident or 'none'}"
 180 | +        if time.time() - t0 > wait_s:
 181 | +            return False, f"the preflight left GPU0 at {used} MiB (found at {found_used} MiB), added {extra}"
 182 | +        time.sleep(1)
 183 | +
 184 | +
 185 |  def main():
 186 | -    res = run_checks()
 187 | +    try:
 188 | +        with gpu0.lease(f"preflight (pid {os.getpid()})"):   # L-r: custody of the wrapper's fd 8, else its own
 189 | +            found_used, found_models = gpu0.memory()[0], gpu0.ollama_loaded()
 190 | +            res = run_checks()
 191 | +            try:
 192 | +                mine = [n for n in gpu0.ollama_loaded() if n in gpu0._ollama_ours]     # what the checks loaded
 193 | +                if mine:                                    # keep_alive 0 did not land (e.g. the request failed)
 194 | +                    gpu0._ollama_unload(mine)
 195 | +                ok, detail = left_as_found(found_used, found_models)
 196 | +            except gpu0.Gpu0Stop as e:
 197 | +                ok, detail = False, f"GPU0 {type(e).__name__}: {e}"
 198 | +            res.append({"check": "gpu0_left", "ok": ok, "detail": detail})
 199 | +    except gpu0.Gpu0Stop as e:
 200 | +        print(f"HOLD (preflight): GPU0 {type(e).__name__}: {e}", flush=True)
 201 | +        return 3
 202 |      for r in res:
 203 |          print(f"  preflight {r['check']:13s} [{'PASS' if r['ok'] else 'FAIL'}] {r['detail']}", flush=True)
 204 |      bad = [r for r in res if not r["ok"]]
 205 | diff --git a/pipeline/pulse_transitions.py b/pipeline/pulse_transitions.py
 206 | index ea2c8141..2d4bbcf2 100644
 207 | --- a/pipeline/pulse_transitions.py
 208 | +++ b/pipeline/pulse_transitions.py
 209 | @@ -151,6 +151,8 @@ def wipe_frames(w, h, n=WIPE_FRAMES):
 210 |  
 211 |  
 212 |  def render_wipe(path, w, h, qp):
 213 | +    import gpu0
 214 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 215 |      import tempfile
 216 |      tmp = tempfile.mkdtemp(prefix="wipe_")
 217 |      for k, f in enumerate(wipe_frames(w, h)):
 218 | @@ -181,6 +183,8 @@ def concat(segments, junctions, out_path, qp, w, h, work_dir):
 219 |      """Concatenate (label, path, type) segments with the planned junctions. Every input is normalised
 220 |      to its exact video frame count (audio padded/trimmed to it) so picture and sound stay locked.
 221 |      Returns the timeline [{"label","type","start","end"}] (overlapping entries at dissolves)."""
 222 | +    import gpu0
 223 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 224 |      style_c = [j for j in junctions if j["kind"] == "insert"]
 225 |      segs = list(segments)
 226 |      if style_c:
 227 | diff --git a/pipeline/render16.py b/pipeline/render16.py
 228 | index 18962aa2..cc4f68ae 100644
 229 | --- a/pipeline/render16.py
 230 | +++ b/pipeline/render16.py
 231 | @@ -21,7 +21,8 @@ import wave
 232 |  import numpy as np
 233 |  from PIL import Image, ImageDraw, ImageFilter
 234 |  
 235 | -os.environ["CUDA_VISIBLE_DEVICES"] = "0"
 236 | +if os.environ.get("CUDA_VISIBLE_DEVICES") not in ("", "-1"):   # L-r: an explicit CPU request stays CPU (this line
 237 | +    os.environ["CUDA_VISIBLE_DEVICES"] = "0"                    # forced GPU0 into CPU test sessions); else GPU0 only
 238 |  
 239 |  PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
 240 |  sys.path.insert(0, PIPELINE_DIR)
 241 | @@ -54,6 +55,8 @@ def ease_in_out(t):
 242 |  def render_vo_visual(vo_wav, preceding_src, preceding_cut_out, output_mp4, label, qa_dir):
 243 |      """R5 VO visual: freeze last frame, blur sigma 6, 1.0x->1.08x zoom, waveform bottom 22%, pre-roll.
 244 |      Returns the path to the assembled VO WAV (silence + stem) for G6 measurement."""
 245 | +    import gpu0
 246 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 247 |      print(f"  Rendering R5 VO visual: {os.path.basename(output_mp4)}")
 248 |  
 249 |      vo_dur = get_duration(vo_wav)
 250 | @@ -170,7 +173,7 @@ def render_vo_visual(vo_wav, preceding_src, preceding_cut_out, output_mp4, label
 251 |          "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", combined_wav,
 252 |      ], capture_output=True, timeout=30, check=True)
 253 |  
 254 | -    subprocess.run([
 255 | +    gpu0.raise_if_oom(subprocess.run([
 256 |          "ffmpeg", "-y",
 257 |          "-framerate", str(FPS),
 258 |          "-i", os.path.join(frames_dir, "frame_%05d.png"),
 259 | @@ -179,7 +182,7 @@ def render_vo_visual(vo_wav, preceding_src, preceding_cut_out, output_mp4, label
 260 |          "-pix_fmt", "yuv420p",
 261 |          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 262 |          "-shortest", "-movflags", "+faststart", output_mp4,
 263 | -    ], capture_output=True, timeout=120)
 264 | +    ], capture_output=True, timeout=120), "render16 nvenc")
 265 |  
 266 |      if os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000:
 267 |          dur = get_duration(output_mp4)
 268 | @@ -193,6 +196,8 @@ def render_vo_visual(vo_wav, preceding_src, preceding_cut_out, output_mp4, label
 269 |  def apply_watermark_alpha(input_mp4, output_mp4, mark_path, mark_px, margin,
 270 |                            opacity, fade_in_dur, shoutout_start):
 271 |      """Overlay alpha watermark on final concat. No black box -- alpha PNG."""
 272 | +    import gpu0
 273 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 274 |      overlay_expr = (
 275 |          f"[1:v]scale={mark_px}:-1,format=rgba,"
 276 |          f"colorchannelmixer=aa={opacity},"
 277 | @@ -213,6 +218,7 @@ def apply_watermark_alpha(input_mp4, output_mp4, mark_path, mark_px, margin,
 278 |          "-c:a", "copy",
 279 |          "-movflags", "+faststart", output_mp4,
 280 |      ], capture_output=True, timeout=600)
 281 | +    gpu0.raise_if_oom(r, "render16 nvenc")      # L-r: never a later "render failed"
 282 |  
 283 |      if r.returncode != 0:
 284 |          print(f"    ffmpeg watermark stderr: {r.stderr.decode()[-500:]}")
 285 | @@ -223,6 +229,8 @@ def apply_watermark_alpha(input_mp4, output_mp4, mark_path, mark_px, margin,
 286 |  def render_16x9(segment_dir, qa_version=None, output_name="segment.mp4",
 287 |                  alimiter_dbfs=-3.0):
 288 |      """Full 16:9 render pipeline. Returns (final_path, manifest_path, vo_assembled_tracks) or raises."""
 289 | +    import gpu0
 290 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 291 |      t0 = time.time()
 292 |      print("=== RENDER 16:9 ===\n")
 293 |  
 294 | @@ -611,6 +619,9 @@ def _find_outro(qa_dir, segment_dir=None):
 295 |      try:
 296 |          return conform_outro("16x9")
 297 |      except (FileNotFoundError, subprocess.CalledProcessError) as e:
 298 | +        import gpu0
 299 | +        if gpu0.is_oom(e):           # L-r: an NVENC out-of-memory is never a fallback (E-FAIL-052)
 300 | +            raise gpu0.GpuOOM(f"outro conform: CUDA/NVENC out of memory ({e})") from e
 301 |          print(f"  PBX outro conform failed ({e}), falling back to qa_dir")
 302 |      for name in ["final_outro.mp4", "outro.mp4"]:
 303 |          candidate = os.path.join(qa_dir, name)
 304 | diff --git a/pipeline/render_vertical.py b/pipeline/render_vertical.py
 305 | index 418fd124..654202a2 100644
 306 | --- a/pipeline/render_vertical.py
 307 | +++ b/pipeline/render_vertical.py
 308 | @@ -64,6 +64,8 @@ def reframe_fixed_crop(seg_path, output_path, seg_label):
 309 |      """Fixed 9:16 crop per clip. Detect faces via mediapipe, use median centre X.
 310 |      Falls back to centre crop if no faces detected.
 311 |      Returns (success: bool, crop_rect: str)."""
 312 | +    import gpu0
 313 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 314 |      import cv2
 315 |      import mediapipe as mp_lib
 316 |      from mediapipe.tasks.python import vision
 317 | @@ -115,6 +117,7 @@ def reframe_fixed_crop(seg_path, output_path, seg_label):
 318 |          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 319 |          "-movflags", "+faststart", output_path,
 320 |      ], capture_output=True, timeout=300)
 321 | +    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"
 322 |  
 323 |      if r.returncode != 0:
 324 |          print(f"      ffmpeg error: {r.stderr.decode()[-300:]}")
 325 | @@ -135,6 +138,8 @@ def reframe_stack2(seg_path, output_path, seg_label, layout_cfg):
 326 |      """Stack2: speaker rect on TOP, other person rect on BOTTOM.
 327 |      Each rect cropped from source, scaled to 1080 wide, placed in 1080x960 slot.
 328 |      layout_cfg keys: speaker_rect (x,y,w,h), other_rect (x,y,w,h)."""
 329 | +    import gpu0
 330 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 331 |      import cv2
 332 |      print(f"    Reframe stack2: {seg_label}")
 333 |  
 334 | @@ -183,6 +188,7 @@ def reframe_stack2(seg_path, output_path, seg_label, layout_cfg):
 335 |          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 336 |          "-movflags", "+faststart", output_path,
 337 |      ], capture_output=True, timeout=300)
 338 | +    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"
 339 |  
 340 |      if r.returncode != 0:
 341 |          print(f"      ffmpeg error: {r.stderr.decode()[-400:]}")
 342 | @@ -203,6 +209,8 @@ def reframe_grid(seg_path, output_path, seg_label, layout_cfg):
 343 |      """Grid: face rect on TOP slot, chart rect on BOTTOM slot.
 344 |      layout_cfg keys: face_rect (x,y,w,h), chart_rect (x,y,w,h),
 345 |                       top_slot_h (default 810), bottom_slot_h (default 1110)."""
 346 | +    import gpu0
 347 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 348 |      import cv2
 349 |      print(f"    Reframe grid: {seg_label}")
 350 |  
 351 | @@ -252,6 +260,7 @@ def reframe_grid(seg_path, output_path, seg_label, layout_cfg):
 352 |          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 353 |          "-movflags", "+faststart", output_path,
 354 |      ], capture_output=True, timeout=300)
 355 | +    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"
 356 |  
 357 |      if r.returncode != 0:
 358 |          print(f"      ffmpeg error: {r.stderr.decode()[-400:]}")
 359 | @@ -270,6 +279,8 @@ def reframe_grid(seg_path, output_path, seg_label, layout_cfg):
 360 |  
 361 |  def reframe_single(seg_path, output_path, seg_label, layout_cfg):
 362 |      """Single: crop one rect from source, scale to 1080 wide, pad to 1920 tall (centred)."""
 363 | +    import gpu0
 364 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 365 |      print(f"    Reframe single: {seg_label}")
 366 |  
 367 |      rect = layout_cfg["rect"]  # [x, y, w, h]
 368 | @@ -289,6 +300,7 @@ def reframe_single(seg_path, output_path, seg_label, layout_cfg):
 369 |          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 370 |          "-movflags", "+faststart", output_path,
 371 |      ], capture_output=True, timeout=300)
 372 | +    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"
 373 |  
 374 |      if r.returncode != 0:
 375 |          print(f"      ffmpeg error: {r.stderr.decode()[-400:]}")
 376 | @@ -310,6 +322,8 @@ def reframe_letterbox(seg_path, output_path, seg_label, layout_cfg=None):
 377 |      darkened (-35%), 1.25x zoomed copy of the same frame. No crop.
 378 |  
 379 |      Returns (success: bool, layout_name: str)."""
 380 | +    import gpu0
 381 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 382 |      print(f"    Reframe letterbox: {seg_label}")
 383 |  
 384 |      # Full 16:9 frame scaled to 1080 wide = 1080x608 (at 16:9 ratio)
 385 | @@ -340,6 +354,7 @@ def reframe_letterbox(seg_path, output_path, seg_label, layout_cfg=None):
 386 |          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 387 |          "-movflags", "+faststart", output_path,
 388 |      ], capture_output=True, timeout=300)
 389 | +    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"
 390 |  
 391 |      if r.returncode != 0:
 392 |          print(f"      ffmpeg error: {r.stderr.decode()[-400:]}")
 393 | @@ -395,6 +410,8 @@ def _shot_vf(shot, src_w, src_h):
 394 |  def reframe_auto(seg_path, output_path, seg_label, plan):
 395 |      """Per-shot 9:16 from the PREPARED clip (lead-in pad and fades identical to 16:9). Video only is
 396 |      re-composed; the clip's audio is copied unchanged. Returns (ok, layout_summary)."""
 397 | +    import gpu0
 398 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 399 |      fps = plan["fps"]
 400 |      graph, labels = [], []
 401 |      matrix = _input_matrix(seg_path)
 402 | @@ -413,6 +430,7 @@ def reframe_auto(seg_path, output_path, seg_label, plan):
 403 |          "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
 404 |          "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", output_path,
 405 |      ], capture_output=True, timeout=600)
 406 | +    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"
 407 |      if r.returncode != 0:
 408 |          print(f"      ffmpeg error: {r.stderr.decode()[-400:]}")
 409 |          return False, "auto"
 410 | @@ -428,6 +446,8 @@ def reframe_auto(seg_path, output_path, seg_label, plan):
 411 |  def render_vo_visual_vert(vo_wav, preceding_src, preceding_cut_out, output_mp4, label, qa_dir):
 412 |      """R5 native 9:16 VO visual: face-crop BG, blur, 1.0x->1.08x zoom, waveform.
 413 |      Returns the path to the assembled VO WAV (silence + stem) for G6 measurement."""
 414 | +    import gpu0
 415 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 416 |      import cv2
 417 |      import mediapipe as mp_lib
 418 |      from mediapipe.tasks.python import vision
 419 | @@ -595,7 +615,7 @@ def render_vo_visual_vert(vo_wav, preceding_src, preceding_cut_out, output_mp4,
 420 |      ], capture_output=True, timeout=30, check=True)
 421 |  
 422 |      # Encode frames + audio
 423 | -    subprocess.run([
 424 | +    gpu0.raise_if_oom(subprocess.run([
 425 |          "ffmpeg", "-y",
 426 |          "-framerate", str(FPS),
 427 |          "-i", os.path.join(frames_dir, "frame_%05d.png"),
 428 | @@ -605,7 +625,7 @@ def render_vo_visual_vert(vo_wav, preceding_src, preceding_cut_out, output_mp4,
 429 |          "-pix_fmt", "yuv420p",
 430 |          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 431 |          "-shortest", "-movflags", "+faststart", output_mp4,
 432 | -    ], capture_output=True, timeout=120)
 433 | +    ], capture_output=True, timeout=120), "render_vertical nvenc")
 434 |  
 435 |      if os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000:
 436 |          dur = get_duration(output_mp4)
 437 | @@ -623,6 +643,8 @@ def render_vo_visual_vert(vo_wav, preceding_src, preceding_cut_out, output_mp4,
 438 |  def apply_watermark_alpha_vert(input_mp4, output_mp4, mark_path, mark_px, margin,
 439 |                                 opacity, fade_in_dur, shoutout_start):
 440 |      """Overlay alpha watermark on vertical concat. Bottom-right, smaller for 9:16."""
 441 | +    import gpu0
 442 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 443 |      overlay_expr = (
 444 |          f"[1:v]scale={mark_px}:-1,format=rgba,"
 445 |          f"colorchannelmixer=aa={opacity},"
 446 | @@ -643,6 +665,7 @@ def apply_watermark_alpha_vert(input_mp4, output_mp4, mark_path, mark_px, margin
 447 |          "-c:a", "copy",
 448 |          "-movflags", "+faststart", output_mp4,
 449 |      ], capture_output=True, timeout=600)
 450 | +    gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"
 451 |  
 452 |      if r.returncode != 0:
 453 |          print(f"    ffmpeg watermark stderr: {r.stderr.decode()[-500:]}")
 454 | @@ -658,6 +681,8 @@ def render_9x16(segment_dir, qa_version=None, output_name="segment_vertical.mp4"
 455 |                  alimiter_dbfs=-3.0):
 456 |      """Full 9:16 vertical render pipeline.
 457 |      Returns (final_path, manifest_path, vo_assembled_tracks) or raises."""
 458 | +    import gpu0
 459 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 460 |      t0 = time.time()
 461 |      print("=== RENDER 9:16 ===\n")
 462 |  
 463 | @@ -714,13 +739,13 @@ def render_9x16(segment_dir, qa_version=None, output_name="segment_vertical.mp4"
 464 |                  s_start = shot["source_start"]
 465 |                  s_end = shot["source_end"]
 466 |                  s_dur = s_end - s_start
 467 | -                subprocess.run([
 468 | +                gpu0.raise_if_oom(subprocess.run([
 469 |                      "ffmpeg", "-y", "-ss", str(s_start), "-i", raw_src, "-t", str(s_dur),
 470 |                      "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
 471 |                      "-pix_fmt", "yuv420p", "-r", str(FPS),
 472 |                      "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 473 |                      "-movflags", "+faststart", shot_trimmed,
 474 | -                ], capture_output=True, timeout=300)
 475 | +                ], capture_output=True, timeout=300), "render_vertical nvenc")
 476 |                  s_layout = shot.get("layout", "crop")
 477 |                  if s_layout == "stack2":
 478 |                      s_ok, _ = reframe_stack2(shot_trimmed, shot_out, f"{clip_id}_shot{si}", shot)
 479 | @@ -740,13 +765,13 @@ def render_9x16(segment_dir, qa_version=None, output_name="segment_vertical.mp4"
 480 |                  with open(concat_list, "w") as clf:
 481 |                      for sp in shot_parts:
 482 |                          clf.write(f"file '{sp}'\n")
 483 | -                subprocess.run([
 484 | +                gpu0.raise_if_oom(subprocess.run([
 485 |                      "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
 486 |                      "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
 487 |                      "-pix_fmt", "yuv420p", "-r", str(FPS),
 488 |                      "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 489 |                      "-movflags", "+faststart", vert_path,
 490 | -                ], capture_output=True, timeout=300)
 491 | +                ], capture_output=True, timeout=300), "render_vertical nvenc")
 492 |                  ok = os.path.exists(vert_path) and os.path.getsize(vert_path) > 1000
 493 |                  crop_rect = "shots"
 494 |              elif all_shots_ok and len(shot_parts) == 1:
 495 | @@ -766,13 +791,13 @@ def render_9x16(segment_dir, qa_version=None, output_name="segment_vertical.mp4"
 496 |                  cut_in = cut.get("cut_in", 0)
 497 |                  cut_dur = cut.get("cut_duration", 15)
 498 |                  trimmed = os.path.join(qa_dir, f"raw_{clip_id}.mp4")
 499 | -                subprocess.run([
 500 | +                gpu0.raise_if_oom(subprocess.run([
 501 |                      "ffmpeg", "-y", "-ss", str(cut_in), "-i", raw_src, "-t", str(cut_dur),
 502 |                      "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
 503 |                      "-pix_fmt", "yuv420p", "-r", str(FPS),
 504 |                      "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 505 |                      "-movflags", "+faststart", trimmed,
 506 | -                ], capture_output=True, timeout=300)
 507 | +                ], capture_output=True, timeout=300), "render_vertical nvenc")
 508 |                  if layout == "stack2":
 509 |                      ok, crop_rect = reframe_stack2(trimmed, vert_path, clip_id, override)
 510 |                  elif layout == "grid":
 511 | @@ -936,6 +961,7 @@ def render_9x16(segment_dir, qa_version=None, output_name="segment_vertical.mp4"
 512 |              "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 513 |              "-movflags", "+faststart", concat_raw,
 514 |          ], capture_output=True, timeout=600)
 515 | +        gpu0.raise_if_oom(r, "render_vertical nvenc")      # L-r: never a later "render failed"
 516 |          if r.returncode != 0:
 517 |              print(f"  ffmpeg stderr: {r.stderr.decode()[-500:]}")
 518 |      concat_dur = get_duration(concat_raw)
 519 | @@ -1160,6 +1186,9 @@ def _find_outro_vert(qa_dir, segment_dir=None):
 520 |      try:
 521 |          return conform_outro("9x16")
 522 |      except (FileNotFoundError, subprocess.CalledProcessError) as e:
 523 | +        import gpu0
 524 | +        if gpu0.is_oom(e):           # L-r: an NVENC out-of-memory is never a fallback (E-FAIL-052)
 525 | +            raise gpu0.GpuOOM(f"outro conform: CUDA/NVENC out of memory ({e})") from e
 526 |          print(f"  PBX 9:16 outro conform failed ({e}), falling back to qa_dir")
 527 |  
 528 |      # Fallback: pre-rendered vertical outro in qa_dir
 529 | diff --git a/pipeline/replay.py b/pipeline/replay.py
 530 | index b7522fab..fc871e29 100644
 531 | --- a/pipeline/replay.py
 532 | +++ b/pipeline/replay.py
 533 | @@ -75,7 +75,13 @@ def replay(run_dir, start="prepare", vision=True, stamp=None):
 534 |          cuts = json.load(f)
 535 |      t0 = time.time()
 536 |      try:
 537 | +        # L-r: a replay is a GPU0 job like a run: the lease to its end (custody when a wrapper holds it), the sampler
 538 | +        run.gpu0_stack.enter_context(rf.gpu0.lease(f"replay {os.path.basename(dst)} (pid {os.getpid()})"))
 539 | +        run.sampler = rf.gpu0.PeakSampler().start()
 540 |          rf.run_tail(run, cuts, start=start, vision=vision)
 541 | +    except rf.gpu0.Gpu0Stop as e:                       # the lease is busy: a HOLD carrying the real cause
 542 | +        run.status["verdict"] = rf.VERDICT_HOLD
 543 | +        run.status["holds"].append(f"replay: infrastructure: GPU0 {type(e).__name__}: {e}")
 544 |      except rf.Hold:
 545 |          run.status["verdict"] = rf.VERDICT_HOLD
 546 |      except Exception as e:                              # as run_fresh.main: anything unexpected is a HOLD
 547 | @@ -86,6 +92,9 @@ def replay(run_dir, start="prepare", vision=True, stamp=None):
 548 |      finally:
 549 |          run.status["elapsed_s"] = round(time.time() - t0, 1)
 550 |          run.status["ended"] = rf.now_iso()
 551 | +        if run.sampler:
 552 | +            run.prov.setdefault("gpu0", {})["peaks_mib"] = run.sampler.stop()
 553 | +        run.prov.setdefault("gpu0", {})["swaps"] = rf.gpu0.events()
 554 |          try:                                            # attested for its verdict, never deliverable
 555 |              rf.attest_run(run, deliverable=False, why_not="replay: diagnostic, deliver only a full run",
 556 |                            code_checked=False)
 557 | @@ -96,6 +105,7 @@ def replay(run_dir, start="prepare", vision=True, stamp=None):
 558 |          rf.write_report(run)
 559 |          with open(os.path.join(dst, "VERDICT.txt"), "w") as f:
 560 |              f.write(str(run.status["verdict"]) + "\n")
 561 | +        run.gpu0_stack.close()                          # the GPU0 lease is held to here
 562 |      print(f"\n=== REPLAY {dst} (from {start}, vision {'on' if vision else 'OFF'}): {run.status['verdict']} ===")
 563 |      for h in run.status["holds"]:
 564 |          print(f"  HOLD: {h}")
 565 | diff --git a/pipeline/run_fresh.py b/pipeline/run_fresh.py
 566 | index 4b93da2c..567bdb3c 100644
 567 | --- a/pipeline/run_fresh.py
 568 | +++ b/pipeline/run_fresh.py
 569 | @@ -39,6 +39,7 @@ Usage:
 570 |    cd ~/protocol_pulse/pipeline && CUDA_VISIBLE_DEVICES=0 python3 run_fresh.py --pinned PIN.json
 571 |  """
 572 |  import argparse
 573 | +import contextlib
 574 |  import datetime
 575 |  import hashlib
 576 |  import io
 577 | @@ -87,6 +88,9 @@ class Hold(Exception):
 578 |      """Fail-closed stop. The run ends in HOLD with the reason recorded."""
 579 |  
 580 |  
 581 | +import gpu0  # noqa: E402  (law L-r: the one owner of GPU0; pipeline/ is this file's directory)
 582 | +
 583 | +
 584 |  # ── utilities ──
 585 |  
 586 |  def sha256(path):
 587 | @@ -168,6 +172,68 @@ class Run:
 588 |          self.mode = "auto"                  # "auto" | "pinned"
 589 |          self.machine_cuts = False          # True only for machine-built PINs (enables snap)
 590 |          self.allow_v2f_material = False     # True only for a pin declaring reuses_v2f_material
 591 | +        self.sampler = None                 # L-r: gpu0.PeakSampler, started in stage_env
 592 | +        self.gpu0_stack = contextlib.ExitStack()   # L-r: holds the GPU0 lease from stage_env to the end of main
 593 | +
 594 | +    def _attempts(self, name, fn):
 595 | +        """Law L-r item 3. A CUDA out-of-memory gets ONE retry of the same step: everything this run owns is released
 596 | +        (outside the except clause, the exception chain's frames broken first, so the model that failed can be freed)
 597 | +        and nvidia-smi must show GPU0 free; both attempts go to PROVENANCE (gpu0_oom); a second out-of-memory is a HOLD
 598 | +        naming every GPU0 process, and any other failure of the retry still carries the first out-of-memory. Every other
 599 | +        GPU0 stop is a HOLD carrying its real cause, never another error."""
 600 | +        first = None                                      # the first attempt's out-of-memory record, once there is one
 601 | +        for attempt in (1, 2):
 602 | +            if self.sampler:
 603 | +                self.sampler.set(name)
 604 | +            oom = None
 605 | +            try:
 606 | +                out = fn()
 607 | +                if first is not None:
 608 | +                    self.prov["gpu0_oom"][name].append({"attempt": 2, "at": now_iso(), "outcome": "passed"})
 609 | +                    self.save()
 610 | +                return out
 611 | +            except gpu0.Gpu0Stop as e:
 612 | +                if not isinstance(e, gpu0.GpuOOM):
 613 | +                    why = f"GPU0 {type(e).__name__}: {e}"
 614 | +                    raise Hold(f"infrastructure: {name}: {why}" if first is None else
 615 | +                               f"infrastructure: {name}: CUDA out of memory on attempt 1 ({first['error'][:200]}); "
 616 | +                               f"the retry then stopped: {why}") from None
 617 | +                oom = f"{type(e).__name__}: {str(e)[:400]}"
 618 | +                gpu0.drop_traceback(e)
 619 | +            except Hold as h:
 620 | +                if first is None:
 621 | +                    raise
 622 | +                raise Hold(f"infrastructure: {name}: CUDA out of memory on attempt 1 ({first['error'][:200]}); the "
 623 | +                           f"retry then held: {h}") from None
 624 | +            except Exception as e:
 625 | +                if not gpu0.is_oom(e):
 626 | +                    if first is None:
 627 | +                        raise
 628 | +                    raise Hold(f"infrastructure: {name}: CUDA out of memory on attempt 1 ({first['error'][:200]}); the "
 629 | +                               f"retry then failed: {type(e).__name__}: {e}") from None
 630 | +                oom = f"{type(e).__name__}: {str(e)[:400]}"
 631 | +                gpu0.drop_traceback(e)
 632 | +            # here, outside the except clause: the failed call's frames are no longer pinned by a live exception
 633 | +            entry = {"attempt": attempt, "at": now_iso(), "error": oom}
 634 | +            try:
 635 | +                entry["gpu0_memory"], entry["gpu0_processes"] = gpu0.memory(), gpu0.processes()
 636 | +                on = gpu0.describe(entry["gpu0_processes"])
 637 | +            except gpu0.Gpu0Stop as e2:
 638 | +                entry["gpu0_unreadable"] = str(e2)
 639 | +                on = f"GPU0 unreadable ({e2})"
 640 | +            self.prov.setdefault("gpu0_oom", {}).setdefault(name, []).append(entry)
 641 | +            self.save()
 642 | +            if attempt == 2:
 643 | +                raise Hold(f"infrastructure: {name}: CUDA out of memory twice ({oom[:240]}); on GPU0: {on}")
 644 | +            first = entry
 645 | +            print(f"  GPU0 OUT OF MEMORY in stage {name}: {oom[:200]}; releasing everything this run owns, retrying "
 646 | +                  f"once", flush=True)
 647 | +            try:
 648 | +                entry["release"] = gpu0.release_all()
 649 | +            except gpu0.Gpu0Stop as e2:
 650 | +                raise Hold(f"infrastructure: {name}: CUDA out of memory ({oom[:200]}) and GPU0 did not come free: "
 651 | +                           f"{type(e2).__name__}: {e2}") from None
 652 | +            self.save()
 653 |  
 654 |      def stage(self, name, fn):
 655 |          rec = {"name": name, "started": now_iso(), "status": "running"}
 656 | @@ -176,7 +242,7 @@ class Run:
 657 |          print(f"\n######## STAGE {name} ########", flush=True)
 658 |          t0 = time.time()
 659 |          try:
 660 | -            out = fn()
 661 | +            out = self._attempts(name, fn)
 662 |              rec["status"] = "passed"
 663 |              return out
 664 |          except Hold as h:
 665 | @@ -198,6 +264,9 @@ class Run:
 666 |          finally:
 667 |              rec["ended"] = now_iso()
 668 |              rec["seconds"] = round(time.time() - t0, 1)
 669 | +            if self.sampler:
 670 | +                self.sampler.set(None)
 671 | +                rec["gpu0_peak_mib"] = self.sampler.peaks.get(name)
 672 |              self.save()
 673 |  
 674 |      def save(self):
 675 | @@ -235,6 +304,15 @@ def stage_env(run):
 676 |                         "ffmpeg": ffv, "yt_dlp": ytv, "nvidia_smi": gpu.split("\n")}
 677 |      if "telegram" in sys.modules or "telegram_drop" in sys.modules:
 678 |          raise Hold("telegram module loaded — publishing path must not be importable here")
 679 | +    # L-r: the run holds the GPU0 lease to the end of main (custody of scripts/pulse_check_run.sh's fd 8, else its
 680 | +    # own), nothing foreign may hold GPU0 memory at its start, and GPU0 memory is sampled per stage from here on
 681 | +    run.gpu0_stack.enter_context(gpu0.lease(f"run_fresh {os.path.basename(run.dir)} (pid {os.getpid()})"))
 682 | +    foreign = gpu0.foreign()
 683 | +    if foreign:
 684 | +        raise Hold(f"infrastructure: env: GPU0 memory is held by a process that is not this run's: "
 685 | +                   f"{gpu0.describe(foreign)}")
 686 | +    run.prov["gpu0"] = {"at_start": {"memory_mib": gpu0.memory(), "processes": gpu0.processes(),
 687 | +                                     "ollama_resident": gpu0.ollama_resident(), "holder": gpu0.holder()}}
 688 |  
 689 |  
 690 |  # ── stage 1: topic ──
 691 | @@ -508,7 +586,9 @@ def free_gpu0_for_whisper(run, stage, need_free_mib=6000):
 692 |      """GPU0 is shared (other sessions load Ollama models on :11434, e.g. a 22 GB qwen3-coder at 06:02 on
 693 |      Nov 11, which OOM'd the recut's prepare). Before a Whisper stage, unload the GPU0 Ollama models and
 694 |      wait for room, exactly as the editorial stage does (story_semantics.release_gpu0_for_whisper); a
 695 | -    release that cannot be proven is an infrastructure HOLD, never an OOM mid-stage."""
 696 | +    release that cannot be proven is an infrastructure HOLD, never an OOM mid-stage. L-r: through
 697 | +    gpu0.swap_to (every other GPU0 model unloaded, a foreign process refused, the measured need proven free);
 698 | +    a refusal is a Gpu0Stop that Run.stage turns into a HOLD carrying the real cause."""
 699 |      import story_semantics as sm
 700 |      try:
 701 |          ev = sm.release_gpu0_for_whisper(sm.LocalLLM(), need_free_mib=need_free_mib, wait_s=180)
 702 | @@ -1231,6 +1311,15 @@ def write_report(run):
 703 |      L += ["## Stages", "| stage | status | s | reason |", "|---|---|---|---|"]
 704 |      L += [f"| {r['name']} | {r['status']} | {r.get('seconds')} | {r.get('reason', '')[:200]} |"
 705 |            for r in s["stages"]]
 706 | +    g0 = p.get("gpu0") or {}
 707 | +    total = ((g0.get("at_start") or {}).get("memory_mib") or [None, None])[1]
 708 | +    L += ["", f"## GPU0 peak memory per stage (law L-r; nvidia-smi memory.used sampled every 1 s, a lower bound; GPU0 "
 709 | +              f"total {total} MiB)", "| stage | peak MiB | out-of-memory attempts | retry |", "|---|---|---|---|"]
 710 | +    for r in s["stages"]:
 711 | +        oom = (p.get("gpu0_oom") or {}).get(r["name"], [])
 712 | +        fails = [e for e in oom if e.get("error")]
 713 | +        retry = "-" if not fails else ("passed" if any(e.get("outcome") == "passed" for e in oom) else "held")
 714 | +        L.append(f"| {r['name']} | {r.get('gpu0_peak_mib', 'not sampled')} | {len(fails)} | {retry} |")
 715 |      vc = p.get("visual_checklist") or {}
 716 |      if vc:
 717 |          L += ["", "## Visual checklist (answered FROM the contact sheets qa/contact_sheet_<fmt>.jpg; any no = HOLD)"]
 718 | @@ -1344,6 +1433,7 @@ def main():
 719 |      run.status["release_state"] = RELEASE_STATE
 720 |      run.save()
 721 |      t0 = time.time()
 722 | +    run.sampler = gpu0.PeakSampler().start()        # L-r item 5: every stage sampled, env included
 723 |      try:
 724 |          run.stage("env", lambda: stage_env(run))
 725 |          if run.mode == "pinned":
 726 | @@ -1359,6 +1449,9 @@ def main():
 727 |          run_tail(run, cuts)
 728 |      except Hold:
 729 |          run.status["verdict"] = VERDICT_HOLD
 730 | +    except gpu0.Gpu0Stop as e:  # L-r: a GPU0 stop outside any stage is a HOLD carrying its real cause
 731 | +        run.status["verdict"] = VERDICT_HOLD
 732 | +        run.status["holds"].append(f"orchestrator: infrastructure: GPU0 {type(e).__name__}: {e}")
 733 |      except Exception as e:  # defensive: anything unexpected is HOLD
 734 |          run.status["verdict"] = VERDICT_HOLD
 735 |          run.status["holds"].append(f"orchestrator: {type(e).__name__}: {e}")
 736 | @@ -1370,6 +1463,10 @@ def main():
 737 |              run.status["holds"].append(f"provenance: {type(e).__name__}: {e}")
 738 |          run.status["ended"] = now_iso()
 739 |          run.status["elapsed_s"] = round(time.time() - t0, 1)
 740 | +        if run.sampler:                        # L-r item 5: peak GPU0 memory per stage, in PROVENANCE and REPORT.md
 741 | +            run.prov.setdefault("gpu0", {})["peaks_mib"] = run.sampler.stop()
 742 | +            run.prov["gpu0"]["sampler_errors"] = run.sampler.errors
 743 | +        run.prov.setdefault("gpu0", {})["swaps"] = gpu0.events()
 744 |          try:                                   # LAST: the terminal state, any hold included (release_auth)
 745 |              attest_run(run)
 746 |          except Exception as e:
 747 | @@ -1383,6 +1480,7 @@ def main():
 748 |          for h in run.status["holds"]:
 749 |              print(f"  HOLD: {h}")
 750 |          print(f"  report: {os.path.join(run_dir, 'REPORT.md')}  (no publishing)")
 751 | +        run.gpu0_stack.close()                 # the GPU0 lease (law L-r) is held to here
 752 |      sys.exit(0 if run.status["verdict"] == VERDICT_CANDIDATE else 3)
 753 |  
 754 |  
 755 | diff --git a/pipeline/run_isolated.py b/pipeline/run_isolated.py
 756 | index 5ac15517..595fd2c5 100644
 757 | --- a/pipeline/run_isolated.py
 758 | +++ b/pipeline/run_isolated.py
 759 | @@ -321,6 +321,8 @@ def prerender_clips(run_dir, cuts_table):
 760 |      (cut["fade_in_ms"], cut["fade_out_ms"]; absent = 20 in / 30 out, the M19 defaults). DEC-10: a cut at an
 761 |      envelope minimum declares 83 ms (2 video frames); v2f's table declares 20 / 30, so its render is unchanged.
 762 |      """
 763 | +    import gpu0
 764 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 765 |      qa_dir = os.path.join(run_dir, "qa")
 766 |      sources_dir = os.path.join(run_dir, "sources")
 767 |  
 768 | diff --git a/pipeline/select_passages.py b/pipeline/select_passages.py
 769 | index e1dcb327..82a54fc1 100644
 770 | --- a/pipeline/select_passages.py
 771 | +++ b/pipeline/select_passages.py
 772 | @@ -87,8 +87,8 @@ def _whisper_transcribe(source_path, video_id, run_dir):
 773 |              if result.get("punctuation") or not punctuation.needs_restoration(result.get("words", [])):
 774 |                  return result
 775 |  
 776 | -        from faster_whisper import WhisperModel
 777 | -        model = WhisperModel("large-v3", device="cuda", compute_type="float16")
 778 | +        import gpu0
 779 | +        model = gpu0.whisper("large-v3")      # L-r: loaded through swap_to; a GPU0 stop passes the except below
 780 |          if result is None:
 781 |              segments, info = model.transcribe(
 782 |                  source_path, language="en", beam_size=5,
 783 | @@ -112,6 +112,9 @@ def _whisper_transcribe(source_path, video_id, run_dir):
 784 |          return result
 785 |  
 786 |      except Exception as e:
 787 | +        import gpu0
 788 | +        if gpu0.is_oom(e):           # L-r: an out-of-memory is never 'transcription failed' (E-FAIL-052)
 789 | +            raise gpu0.GpuOOM(f"{video_id}: Whisper: CUDA out of memory ({type(e).__name__}: {str(e)[:200]})") from e
 790 |          print(f"    WARN: whisper failed for {video_id}: {e}")
 791 |          return None
 792 |  
 793 | diff --git a/pipeline/sentence_law.py b/pipeline/sentence_law.py
 794 | index b283500d..b0c9d836 100644
 795 | --- a/pipeline/sentence_law.py
 796 | +++ b/pipeline/sentence_law.py
 797 | @@ -813,6 +813,8 @@ def room_tone(src_path, t0, t1, seconds, sr=48000):
 798 |  def apply_lead_in_pad(run_dir, cut, fps, qp):
 799 |      """Prepend cut['lead_in_pad_s'] of room tone + the held first frame to qa/final_<clip>.mp4
 800 |      (atomic replace). The pad is declared in cuts_final.json, so every gate knows it is there."""
 801 | +    import gpu0
 802 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 803 |      import wave
 804 |      pad = float(cut["lead_in_pad_s"])
 805 |      clip = os.path.join(run_dir, "qa", f"final_{cut['clip_id']}.mp4")
 806 | diff --git a/pipeline/shot_snap.py b/pipeline/shot_snap.py
 807 | index 8898b9b4..e98db5c5 100644
 808 | --- a/pipeline/shot_snap.py
 809 | +++ b/pipeline/shot_snap.py
 810 | @@ -48,6 +48,8 @@ def plan(changes, n_frames, fps, speech_on_s, speech_off_s):
 811 |  def apply(clip, cut, fps, qp):
 812 |      """Snap qa/final_<clip>.mp4 in place when a neighbouring shot shows outside the speech. Returns a record
 813 |      (always), {"snapped": False, ...} when nothing changed."""
 814 | +    import gpu0
 815 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 816 |      pad = float(cut.get("lead_in_pad_s") or 0.0)
 817 |      pin, pout = cut.get("pause_in") or {}, cut.get("pause_out") or {}
 818 |      on = (pin["end"] - cut["cut_in"] + pad) if "end" in pin else None
 819 | @@ -62,9 +64,13 @@ def apply(clip, cut, fps, qp):
 820 |      vf = f"trim=start_frame={head}:end_frame={tail},setpts=PTS-STARTPTS,tpad=start_mode=clone:start={head}:" \
 821 |           f"stop_mode=clone:stop={n - tail}"
 822 |      part = clip + ".snap.mp4"
 823 | -    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-map", "0:v:0", "-map", "0:a:0", "-vf", vf,
 824 | -                    "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(qp), "-pix_fmt", "yuv420p",
 825 | -                    "-r", str(fps), "-c:a", "copy", "-movflags", "+faststart", part], check=True, timeout=600)
 826 | +    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-map", "0:v:0", "-map", "0:a:0", "-vf", vf,
 827 | +                        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(qp), "-pix_fmt", "yuv420p",
 828 | +                        "-r", str(fps), "-c:a", "copy", "-movflags", "+faststart", part], capture_output=True, timeout=600)
 829 | +    if r.returncode != 0:                      # L-r: stderr captured so an NVENC out-of-memory is named, not renamed
 830 | +        gpu0.raise_if_oom(r, "shot_snap nvenc")
 831 | +        print(r.stderr.decode(errors="replace")[-2000:], flush=True)
 832 | +        raise subprocess.CalledProcessError(r.returncode, r.args, r.stdout, r.stderr)
 833 |      if frame_count(part) != n:
 834 |          os.remove(part)
 835 |          raise RuntimeError(f"shot snap changed the frame count of {clip}")
 836 | diff --git a/pipeline/story_semantics.py b/pipeline/story_semantics.py
 837 | index f6cbdc63..7cb984c9 100644
 838 | --- a/pipeline/story_semantics.py
 839 | +++ b/pipeline/story_semantics.py
 840 | @@ -27,6 +27,7 @@ import os
 841 |  import re
 842 |  import subprocess
 843 |  import time
 844 | +import urllib.error
 845 |  import urllib.request
 846 |  from datetime import datetime, timedelta, timezone
 847 |  
 848 | @@ -70,11 +71,14 @@ class Embedder:
 849 |      def __init__(self):
 850 |          _gpu_guard()
 851 |          import torch
 852 | +        import gpu0
 853 |          from transformers import AutoModel, AutoTokenizer
 854 |          from huggingface_hub import snapshot_download
 855 |          path = snapshot_download(EMBED_MODEL, revision=EMBED_REVISION, local_files_only=True)
 856 |          self.tok = AutoTokenizer.from_pretrained(path)
 857 | -        self.model = AutoModel.from_pretrained(path, dtype=torch.float16).to("cuda:0").eval()
 858 | +        # L-r: the weights reach GPU0 only through gpu0.swap_to("embedder") (Model.get), and any later swap deletes them
 859 | +        self.model = gpu0.model("embedder", lambda: AutoModel.from_pretrained(path, dtype=torch.float16).to("cuda:0").eval())
 860 | +        self.gpu0 = gpu0
 861 |          self.torch = torch
 862 |          self.model_id = f"{EMBED_MODEL}@{EMBED_REVISION[:12]}"
 863 |  
 864 | @@ -83,10 +87,12 @@ class Embedder:
 865 |          with self.torch.no_grad():
 866 |              for i in range(0, len(texts), batch):
 867 |                  bt = [(EMBED_QUERY_PREFIX + t) if query else t for t in texts[i:i + batch]]
 868 | -                enc = self.tok(bt, padding=True, truncation=True, max_length=512,
 869 | -                               return_tensors="pt").to("cuda:0")
 870 | -                cls = self.model(**enc).last_hidden_state[:, 0].float()
 871 | -                out.append(self.torch.nn.functional.normalize(cls, dim=-1).cpu().numpy())
 872 | +                self.model.get()                                  # resident before any tensor goes to GPU0
 873 | +                with self.gpu0.guard("embedder: encode"):
 874 | +                    enc = self.tok(bt, padding=True, truncation=True, max_length=512,
 875 | +                                   return_tensors="pt").to("cuda:0")
 876 | +                    cls = self.model(**enc).last_hidden_state[:, 0].float()
 877 | +                    out.append(self.torch.nn.functional.normalize(cls, dim=-1).cpu().numpy())
 878 |          return np.vstack(out) if out else np.zeros((0, 768), np.float32)
 879 |  
 880 |      def chunk_vectors(self, rec, chunks):
 881 | @@ -104,7 +110,7 @@ class Embedder:
 882 |          return ids, vecs
 883 |  
 884 |      def close(self):
 885 | -        del self.model
 886 | +        self.model.unload()
 887 |          self.torch.cuda.empty_cache()
 888 |  
 889 |  
 890 | @@ -187,13 +193,28 @@ class LocalLLM:
 891 |          return sorted(gpus.get(u, u) for u in mine)
 892 |  
 893 |      def _post(self, prompt, max_tokens, seed):
 894 | +        import gpu0
 895 | +        gpu0.require(f"ollama:{self.model}")          # L-r: every request under the lease, not only the first
 896 | +        if getattr(self, "_gpu0_gen", None) != gpu0.generation() or self.model not in gpu0.ollama_loaded():
 897 | +            gpu0.swap_to(f"ollama:{self.model}")        # L-r: nothing else resident, the memory proven free
 898 | +            self._gpu0_gen = gpu0.generation()
 899 |          body = json.dumps({"model": self.model, "stream": False, "format": "json",
 900 |                             "messages": [{"role": "user", "content": prompt}],
 901 |                             "options": {"temperature": 0, "seed": seed, "num_ctx": LLM_CTX,
 902 |                                         "num_predict": max_tokens}}).encode()
 903 |          req = urllib.request.Request(f"http://{self.host}/api/chat", data=body,
 904 |                                       headers={"Content-Type": "application/json"})
 905 | -        resp = json.loads(urllib.request.urlopen(req, timeout=600).read())
 906 | +        try:
 907 | +            resp = json.loads(urllib.request.urlopen(req, timeout=600).read())
 908 | +        except urllib.error.HTTPError as e:
 909 | +            text = e.read().decode(errors="replace")             # classified whole, reported truncated
 910 | +            if gpu0.is_oom(RuntimeError(text)):
 911 | +                raise gpu0.GpuOOM(f"ollama {self.model}: CUDA out of memory (HTTP {e.code}: {text[-400:]})") from None
 912 | +            raise RuntimeError(f"Ollama HTTP {e.code}: {text[:400]}") from None
 913 | +        except (urllib.error.URLError, ConnectionError) as e:   # a runner that died mid-request
 914 | +            if gpu0.is_oom(e):
 915 | +                raise gpu0.GpuOOM(f"ollama {self.model}: CUDA out of memory ({e})") from None
 916 | +            raise
 917 |          self.calls += 1
 918 |          if not self.placement_checked:
 919 |              placement = self.gpu_placement()
 920 | @@ -297,7 +318,11 @@ def loaded_models(host=LLM_HOST):
 921 |  
 922 |  def release_gpu0_for_whisper(llm, need_free_mib=7000, wait_s=180, log=print):
 923 |      """Unload every model on the GPU0 Ollama, wait until GPU0 has need_free_mib free.
 924 | -    Returns an evidence dict; raises RuntimeError (infrastructure) if release can't be proven."""
 925 | +    Returns an evidence dict; raises RuntimeError (infrastructure) if release can't be proven.
 926 | +    L-r: first gpu0.swap_to (every other GPU0 model unloaded, a foreign process refused, the batched word-pass model's
 927 | +    measured need proven free; a refusal is a Gpu0Stop that no caller can rename), then this function's own proof."""
 928 | +    import gpu0
 929 | +    gpu0.swap_to("whisper:large-v3:batched", wait_s=wait_s)
 930 |      ev = {"before": gpu0_memory(), "unloaded": []}
 931 |      deadline = time.time() + wait_s
 932 |      while True:
 933 | diff --git a/pipeline/test_acoustic.py b/pipeline/test_acoustic.py
 934 | index bdda05e4..38d76722 100644
 935 | --- a/pipeline/test_acoustic.py
 936 | +++ b/pipeline/test_acoustic.py
 937 | @@ -67,6 +67,9 @@ def test_magnitude_whisper():
 938 |      if not os.path.exists(source):
 939 |          print("  [SKIP] Real source not found — test_magnitude_whisper")
 940 |          return
 941 | +    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":       # law L-r: Whisper is a GPU0 load, refused in a CPU session
 942 | +        print("  [SKIP] CPU session: Whisper is a GPU0 load — test_magnitude_whisper")
 943 | +        return
 944 |  
 945 |      print("\n--- Test 2: Whisper last 1.0s contains 'magnitude' ---")
 946 |      result = compute_acoustic_cut_out(source, 249.22)
 947 | @@ -82,7 +85,8 @@ def test_magnitude_whisper():
 948 |              "ffmpeg", "-y", "-ss", str(cut_out - 1.0), "-t", "1.0",
 949 |              "-i", source, "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmp_wav,
 950 |          ], capture_output=True, timeout=10, check=True)
 951 | -        model = WhisperModel("medium", device="cuda", compute_type="float16")
 952 | +        import gpu0
 953 | +        model = gpu0.whisper("medium")          # L-r: through swap_to, under the session's GPU0 lease
 954 |          segments, _ = model.transcribe(tmp_wav, language="en", beam_size=5)
 955 |          text = " ".join(seg.text.strip() for seg in segments).lower()
 956 |          os.unlink(tmp_wav)
 957 | diff --git a/pipeline/test_pinned.py b/pipeline/test_pinned.py
 958 | index ff16fc2f..8c962ed0 100644
 959 | --- a/pipeline/test_pinned.py
 960 | +++ b/pipeline/test_pinned.py
 961 | @@ -289,8 +289,9 @@ class TestPinnedStageFreesGpu0First(Fixture):
 962 |              self.assertEqual(events, [("release", "pinned"), "prepare"])
 963 |              events.clear()
 964 |              rf.free_gpu0_for_whisper = refuse
 965 | -            with self.assertRaisesRegex(rf.Hold, "infrastructure: pinned"):
 966 | +            with self.assertRaisesRegex(rf.Hold, "^infrastructure: pinned") as cm:    # anchored (fable audit of 456a440f)
 967 |                  rf.stage_pinned(run, self.write(self.pin()))
 968 | +            self.assertNotIn("pinned decision rejected", str(cm.exception))
 969 |              self.assertEqual(events, [("release", "pinned")])        # nothing downloaded or transcribed after it
 970 |          finally:
 971 |              rf.free_gpu0_for_whisper, pinned.prepare = orig_free, orig_prep
 972 | diff --git a/pipeline/test_preflight.py b/pipeline/test_preflight.py
 973 | index 3d92f72a..c6ed1029 100644
 974 | --- a/pipeline/test_preflight.py
 975 | +++ b/pipeline/test_preflight.py
 976 | @@ -53,35 +53,35 @@ class TestChecks(unittest.TestCase):
 977 |          P._run = self.saved_run
 978 |  
 979 |      def test_a_foreign_job_on_gpu0_fails_and_our_ollama_runner_does_not(self):
 980 | -        import story_semantics as sm
 981 | -        saved = (sm.LocalLLM._listener_pid, sm.gpu0_memory, os.environ.get("CUDA_VISIBLE_DEVICES"))
 982 | -        os.environ["CUDA_VISIBLE_DEVICES"] = "0"                       # as the wrapper exports it
 983 | -        sm.LocalLLM._listener_pid = lambda self: 100
 984 | -        sm.gpu0_memory = lambda: (19000, 24564)
 985 | -
 986 | -        def run(cmd, timeout=30):
 987 | -            if "--query-gpu=index,uuid" in cmd:
 988 | -                return R("0, GPU-A\n1, GPU-B\n")
 989 | -            if "--query-compute-apps=pid,gpu_uuid,used_memory" in cmd:
 990 | -                return R(self.apps)
 991 | -            if cmd[0] == "pgrep":
 992 | -                return R("101\n")
 993 | -            return R("python3 something\n")
 994 | -        P._run = run
 995 | +        """Law L-r: a foreign compute process on GPU0 fails the check, named; so does a model resident on the shared
 996 | +        Ollama that this run did not request (cycle 1 of its audit: the Ollama server is not a lease-free door); the
 997 | +        Ollama listener and runners themselves are not foreign; enough room = the largest single model + margin."""
 998 | +        from unittest import mock
 999 | +        import gpu0
1000 | +        state = {"procs": [], "used": 600, "ollama": []}
1001 | +        patches = [mock.patch.object(gpu0, "processes", side_effect=lambda: list(state["procs"])),
1002 | +                   mock.patch.object(gpu0, "memory", side_effect=lambda: (state["used"], 24564)),
1003 | +                   mock.patch.object(gpu0, "ollama_resident", side_effect=lambda: list(state["ollama"])),
1004 | +                   mock.patch.object(gpu0, "_ollama_pids", return_value={100, 101})]
1005 | +        for x in patches:
1006 | +            x.start()
1007 |          try:
1008 | -            self.apps = "101, GPU-A, 18900\n555, GPU-B, 21000\n"          # our runner on GPU0, GPU1 busy
1009 | +            state["procs"] = [(101, "ollama", 500)]                    # the runner, idle: ours, nothing resident
1010 |              ok, d = P.check_gpu0()
1011 |              self.assertTrue(ok, d)
1012 | -            self.apps = "101, GPU-A, 18900\n777, GPU-A, 1962\n"          # a foreign job on GPU0
1013 | +            state["procs"] = [(101, "ollama", 500), (777, "python3", 1962)]   # a foreign job on GPU0
1014 | +            state["used"] = 2562
1015 |              ok, d = P.check_gpu0()
1016 |              self.assertFalse(ok)
1017 | -            self.assertIn("pid 777", d)
1018 | +            self.assertIn("pid 777 python3 1962 MiB", d)
1019 | +            state["procs"], state["used"] = [(101, "ollama", 18900)], 19000
1020 | +            state["ollama"] = [("gemma3:27b", 18900)]                 # resident, not requested by this run
1021 | +            ok, d = P.check_gpu0()
1022 | +            self.assertFalse(ok)
1023 | +            self.assertIn("ollama model gemma3:27b (not requested by this run)", d)
1024 |          finally:
1025 | -            sm.LocalLLM._listener_pid, sm.gpu0_memory, cvd = saved
1026 | -            if cvd is None:
1027 | -                os.environ.pop("CUDA_VISIBLE_DEVICES", None)
1028 | -            else:
1029 | -                os.environ["CUDA_VISIBLE_DEVICES"] = cvd
1030 | +            for x in reversed(patches):
1031 | +                x.stop()
1032 |  
1033 |      def test_a_dirty_or_unpushed_tree_fails(self):
1034 |          replies = {"status": R(" M pipeline/editorial_select.py\n")}
1035 | diff --git a/pipeline/test_pulse_20261110_mustfail.py b/pipeline/test_pulse_20261110_mustfail.py
1036 | index 61d5335a..90e3c888 100644
1037 | --- a/pipeline/test_pulse_20261110_mustfail.py
1038 | +++ b/pipeline/test_pulse_20261110_mustfail.py
1039 | @@ -294,8 +294,9 @@ class TestPunctuationLayer(unittest.TestCase):
1040 |          from faster_whisper import WhisperModel
1041 |          raw = json.load(open(os.path.join(FIX, "run", "transcripts", "36HPi9UZPOc.json")))
1042 |          want = json.load(open(os.path.join(FIX, "selection", "transcripts_punctuated", "36HPi9UZPOc.json")))
1043 | +        import gpu0
1044 |          got = P.ensure(raw, os.path.join(FIX, "audio", "src_36HPi9UZPOc.flac"),
1045 | -                       WhisperModel("large-v3", device="cuda", compute_type="float16"))
1046 | +                       gpu0.whisper("large-v3"))         # L-r: through swap_to, under the session's GPU0 lease
1047 |          self.assertEqual([w["word"] for w in got["words"]], [w["word"] for w in want["words"]])
1048 |  
1049 |  
1050 | diff --git a/pipeline/test_punct_word_pass.py b/pipeline/test_punct_word_pass.py
1051 | index 33ecee49..f1b8c06f 100644
1052 | --- a/pipeline/test_punct_word_pass.py
1053 | +++ b/pipeline/test_punct_word_pass.py
1054 | @@ -157,34 +157,67 @@ class TestAcquireUpgrade(unittest.TestCase):
1055 |  
1056 |      def test_a_failed_restoration_is_not_sentence_ready(self):
1057 |          def boom():
1058 | -            raise RuntimeError("CUDA out of memory (simulated)")
1059 | +            raise RuntimeError("reference decode failed (simulated)")
1060 |          ts._reference = boom
1061 |          r, st = ts.acquire(self.vid, prefer_words=True)
1062 |          self.assertEqual((st, r["transcript_method"]), ("punctuation_failed", "whisper_words"))
1063 |          self.assertFalse(ts.sentence_ready(r))                 # editorial_select treats it as a failure
1064 | -        self.assertIn("out of memory", ts.LAST_ERROR[self.vid])
1065 | +        self.assertIn("reference decode failed", ts.LAST_ERROR[self.vid])
1066 | +
1067 | +    def test_an_out_of_memory_is_never_a_failure_status(self):
1068 | +        """Law L-r (E-FAIL-052): until Nov 12 a simulated out-of-memory here became 'punctuation_failed' (a video's
1069 | +        failure). It now leaves acquire as gpu0.GpuOOM for the stage's one bounded retry."""
1070 | +        import gpu0
1071 | +        def boom():
1072 | +            raise RuntimeError("CUDA out of memory (simulated)")
1073 | +        ts._reference = boom
1074 | +        saved = ts.release_whisper
1075 | +        ts.release_whisper = lambda: None
1076 | +        try:
1077 | +            with self.assertRaisesRegex(gpu0.GpuOOM, "punctuation: CUDA out of memory"):
1078 | +                ts.acquire(self.vid, prefer_words=True)
1079 | +        finally:
1080 | +            ts.release_whisper = saved
1081 |  
1082 |  
1083 |  class TestOneWhisperModelAtATime(unittest.TestCase):
1084 |      """Heimdall batch13: the word pass's GPU0 arbitration proves 7 GB free, so distil-large-v3 and the large-v3
1085 | -    reference are never resident together (stubbed models, no GPU)."""
1086 | +    reference are never resident together (stubbed models, no GPU). Law L-r makes it so by construction: both are
1087 | +    gpu0 Models, and loading one through swap_to deletes the other."""
1088 |      def test_loading_one_drops_the_other(self):
1089 |          import types
1090 | +        import tempfile
1091 | +        from unittest import mock
1092 | +        import gpu0
1093 |          fw = types.ModuleType("faster_whisper")
1094 |          fw.WhisperModel = type("WM", (), {"__init__": lambda self, name, **kw: setattr(self, "name", name)})
1095 |          fw.BatchedInferencePipeline = type("BP", (), {"__init__": lambda self, model: setattr(self, "model", model)})
1096 |          saved = (sys.modules.get("faster_whisper"), os.environ.get("CUDA_VISIBLE_DEVICES"), ts._WHISPER, ts._REFERENCE)
1097 |          sys.modules["faster_whisper"], os.environ["CUDA_VISIBLE_DEVICES"] = fw, "0"
1098 |          ts._WHISPER = ts._REFERENCE = None
1099 | +        fake = [mock.patch.object(gpu0, "memory", return_value=(100, 24564)),
1100 | +                mock.patch.object(gpu0, "processes", return_value=[]),
1101 | +                mock.patch.object(gpu0, "ollama_resident", return_value=[]),
1102 | +                mock.patch.object(gpu0, "_ollama_unload", return_value=[]),
1103 | +                mock.patch.dict(os.environ, {"PP_GPU0_LEASE": os.path.join(tempfile.mkdtemp(), "lease")})]
1104 | +        for f in fake:
1105 | +            f.start()
1106 |          try:
1107 | -            a = ts._whisper()
1108 | -            self.assertEqual((a.model.name, ts._REFERENCE), (ts.WHISPER_MODEL, None))
1109 | -            self.assertIs(ts._whisper(), a)
1110 | -            b = ts._reference()
1111 | -            self.assertEqual((b.model.name, ts._WHISPER), (ts.REFERENCE_MODEL, None))
1112 | -            ts._whisper()
1113 | -            self.assertIsNone(ts._REFERENCE)
1114 | +            with gpu0.lease("test"):
1115 | +                a = ts._whisper()
1116 | +                self.assertEqual((a.get().model.name, ts._REFERENCE), (ts.WHISPER_MODEL, None))
1117 | +                self.assertIs(ts._whisper(), a)
1118 | +                b = ts._reference()
1119 | +                self.assertEqual((b.get().model.name, ts._WHISPER), (ts.REFERENCE_MODEL, None))
1120 | +                self.assertFalse(a.loaded)                            # deleted by the swap to the reference
1121 | +                ts._whisper().get()                                    # loads on first use (lazy)
1122 | +                self.assertIsNone(ts._REFERENCE)
1123 | +                self.assertFalse(b.loaded)
1124 |          finally:
1125 | +            for f in reversed(fake):
1126 | +                f.stop()
1127 | +            for m in (gpu0.whisper(ts.WHISPER_MODEL, batched=True), gpu0.whisper(ts.REFERENCE_MODEL, batched=True)):
1128 | +                m.unload()
1129 |              mod, cvd, ts._WHISPER, ts._REFERENCE = saved
1130 |              if mod is None:
1131 |                  sys.modules.pop("faster_whisper", None)
1132 | diff --git a/pipeline/transcript_store.py b/pipeline/transcript_store.py
1133 | index 4a9ac39c..9be07e13 100644
1134 | --- a/pipeline/transcript_store.py
1135 | +++ b/pipeline/transcript_store.py
1136 | @@ -292,6 +292,9 @@ def release_whisper():
1137 |      """Drop the Whisper models and free their GPU memory (E5). Returns GPU0 used MiB after."""
1138 |      global _WHISPER, _REFERENCE
1139 |      _WHISPER = _REFERENCE = None
1140 | +    import gpu0
1141 | +    for name in (WHISPER_MODEL, REFERENCE_MODEL):
1142 | +        gpu0.whisper(name, batched=True).unload()
1143 |      import gc
1144 |      gc.collect()
1145 |      try:
1146 | @@ -304,21 +307,18 @@ def release_whisper():
1147 |  
1148 |  def _load(name):
1149 |      """One Whisper model on GPU0 at a time (the word pass's arbitration proves 7 GB free, not two models' worth;
1150 | -    Heimdall batch13): loading one drops the other first."""
1151 | +    Heimdall batch13): L-r makes it so by construction: gpu0.whisper loads through swap_to, which deletes every
1152 | +    other GPU0 model first, and the model reloads through swap_to after any later swap."""
1153 |      global _WHISPER, _REFERENCE
1154 |      if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
1155 |          raise AcquisitionError("Whisper requires CUDA_VISIBLE_DEVICES=0 (GPU1 quarantined)")
1156 | -    if (_WHISPER if name == WHISPER_MODEL else _REFERENCE) is None:
1157 | -        import gc
1158 | -        _WHISPER = _REFERENCE = None
1159 | -        gc.collect()
1160 | -        from faster_whisper import WhisperModel, BatchedInferencePipeline
1161 | -        m = BatchedInferencePipeline(model=WhisperModel(name, device="cuda", compute_type="float16"))
1162 | -        if name == WHISPER_MODEL:
1163 | -            _WHISPER = m
1164 | -        else:
1165 | -            _REFERENCE = m
1166 | -    return _WHISPER if name == WHISPER_MODEL else _REFERENCE
1167 | +    import gpu0
1168 | +    m = gpu0.whisper(name, batched=True)
1169 | +    if name == WHISPER_MODEL:
1170 | +        _WHISPER, _REFERENCE = m, None
1171 | +    else:
1172 | +        _WHISPER, _REFERENCE = None, m
1173 | +    return m
1174 |  
1175 |  
1176 |  def _whisper():
1177 | @@ -478,10 +478,12 @@ def acquire(video_id, rss=None, channel=None, allow_whisper=True, prefer_words=F
1178 |                           marks=prec["punctuation"].get("marks_transferred"))
1179 |              status += "+punctuation"
1180 |      except Exception as e:
1181 | +        import gpu0
1182 | +        if gpu0.is_oom(e):             # L-r: an out-of-memory is never this video's error; it leaves as GpuOOM for
1183 | +            _log_attempt(video_id, step=step, status="gpu0_out_of_memory", error=str(e)[-300:])   # the one retry
1184 | +            raise gpu0.GpuOOM(f"{video_id}: {step}: CUDA out of memory ({type(e).__name__}: {str(e)[:200]})") from e
1185 |          LAST_ERROR[video_id] = f"{type(e).__name__}: {e}"[-400:]
1186 |          _log_attempt(video_id, step=step, status="error", error=str(e)[-300:])
1187 | -        if "out of memory" in str(e).lower():
1188 | -            release_whisper()          # never keep a half-initialised model around
1189 |          return canonical_transcript(video_id), f"{step}_failed"
1190 |      return canonical_transcript(video_id), status
1191 |  
1192 | diff --git a/pipeline/word_diff.py b/pipeline/word_diff.py
1193 | index 386cb7a0..8c25e650 100644
1194 | --- a/pipeline/word_diff.py
1195 | +++ b/pipeline/word_diff.py
1196 | @@ -70,8 +70,8 @@ def edges(lock_text, heard, n=EDGE_WORDS):
1197 |  
1198 |  class Transcriber:
1199 |      def __init__(self):
1200 | -        from faster_whisper import WhisperModel
1201 | -        self.model = WhisperModel(ASR["model"], device="cuda", compute_type="float16")
1202 | +        import gpu0
1203 | +        self.model = gpu0.whisper(ASR["model"])      # L-r: loaded through swap_to on first use
1204 |  
1205 |      def span(self, media, t0, t1):
1206 |          if t1 - t0 < 0.05:
1207 | diff --git a/scripts/pulse_check_run.sh b/scripts/pulse_check_run.sh
1208 | index 34183a0f..1161b248 100755
1209 | --- a/scripts/pulse_check_run.sh
1210 | +++ b/scripts/pulse_check_run.sh
1211 | @@ -72,8 +72,19 @@ if ! flock -n 9; then
1212 |    echo "pulse_check_run: another run holds /tmp/pulse_check_run.lock" | tee -a "$LOG" >&2
1213 |    exit 75
1214 |  fi
1215 | +# law L-r ONE OWNER: the GPU0 lease (pipeline/gpu0.py) on fd 8 for the whole run; preflight and run_fresh inherit
1216 | +# the descriptor (custody), nothing else may load onto GPU0 meanwhile; released when this script exits
1217 | +GPU0_LEASE="${PP_GPU0_LEASE:-/tmp/pulse_gpu0.lease}"
1218 | +exec 8>>"$GPU0_LEASE"
1219 | +if ! flock -n 8; then
1220 | +  echo "pulse_check_run: the GPU0 lease is held: $(cat "$GPU0_LEASE" 2>/dev/null)" | tee -a "$LOG" >&2
1221 | +  exit 75
1222 | +fi
1223 | +python3 -c 'import json, sys, time; json.dump({"pid": int(sys.argv[1]), "owner": "pulse_check_run " + sys.argv[2] + " (" + sys.argv[3] + ")", "since": time.time()}, open(sys.argv[4], "w"))' \
1224 | +  "$$" "$STAMP" "${ARGS[*]:-auto}" "$GPU0_LEASE"
1225 |  
1226 |  export CUDA_VISIBLE_DEVICES=0
1227 | +export CUDA_DEVICE_ORDER=PCI_BUS_ID      # law L-r: CUDA device 0 is nvidia-smi GPU 0 (gpu0.require checks it)
1228 |  cd "$REPO/pipeline" || exit 1
1229 |  echo "=== pulse_check_run $STAMP | HEAD $(git -C "$REPO" rev-parse HEAD) | args: ${ARGS[*]:-auto} ===" | tee -a "$LOG"
1230 |  # preflight (orchestrator 2026-11-11 '21:10'): seconds, before any hour is spent; a failure is a HOLD with the reason
1231 | diff --git a/segment_v1/qa_gates.py b/segment_v1/qa_gates.py
1232 | index 19ba78dd..6f4b7f82 100644
1233 | --- a/segment_v1/qa_gates.py
1234 | +++ b/segment_v1/qa_gates.py
1235 | @@ -47,16 +47,21 @@ G9_REENCODE_SPREAD = {"16x9": 0.05, "9x16": 0.04}      # DEC-12a: MEASURED sprea
1236 |      # made a correct render pass or fail by encoder state (OD-4).
1237 |  G9_LUMA_FLOOR = {k: round(G9_V2F_LUMA[k] - G9_REENCODE_SPREAD[k], 4) for k in G9_V2F_LUMA}   # 14.2857 / 14.7315
1238 |  
1239 | -# ── Faster-Whisper singleton (medium, float16, cuda, vad OFF, word timestamps) ──
1240 | -_FW_MODEL = None
1241 | +# ── Faster-Whisper medium (float16, GPU0, vad OFF, word timestamps): law L-r, through pipeline/gpu0.py ──
1242 | +
1243 | +def _gpu0():
1244 | +    """pipeline/gpu0.py (law L-r), importable when this file runs on its own too."""
1245 | +    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline")
1246 | +    if p not in sys.path:
1247 | +        sys.path.insert(0, p)
1248 | +    import gpu0
1249 | +    return gpu0
1250 | +
1251 |  
1252 |  def _get_fw_model():
1253 | -    """Load faster-whisper medium model once per gate run."""
1254 | -    global _FW_MODEL
1255 | -    if _FW_MODEL is None:
1256 | -        from faster_whisper import WhisperModel
1257 | -        _FW_MODEL = WhisperModel("medium", device="cuda", compute_type="float16")
1258 | -    return _FW_MODEL
1259 | +    """The process's one faster-whisper medium: gpu0.whisper loads it through swap_to on first use (every other
1260 | +    GPU0 model unloaded, the memory proven free), any later swap deletes it, and it reloads when used again."""
1261 | +    return _gpu0().whisper("medium")
1262 |  
1263 |  
1264 |  def fw_transcribe(wav_path, word_timestamps=True):
1265 | @@ -146,7 +151,7 @@ def gate_g1(final_mp4, manifest, vo_regions, qa_dir, vo_assembled_tracks=None):
1266 |      from resemblyzer import VoiceEncoder, preprocess_wav
1267 |  
1268 |      print("\n=== G1: VOICE IDENTITY ===")
1269 | -    encoder = VoiceEncoder()
1270 | +    encoder = _gpu0().model("resemblyzer", VoiceEncoder)     # L-r: loaded through swap_to; calls inside guard()
1271 |  
1272 |      if vo_assembled_tracks is None:
1273 |          vo_assembled_tracks = {}
1274 | diff --git a/pipeline/gpu0.py b/pipeline/gpu0.py
1275 | new file mode 100644
1276 | index 00000000..79b81b2f
1277 | --- /dev/null
1278 | +++ b/pipeline/gpu0.py
1279 | @@ -0,0 +1,688 @@
1280 | +#!/usr/bin/env python3
1281 | +"""pipeline/gpu0.py — law L-r GPU0 NEVER SURPRISES A RUN (orchestrator 2026-11-12 '01:55' B; PBX on the pinned run's
1282 | +out-of-memory: "let's make sure that never happens again").
1283 | +
1284 | +ONE OWNER. GPU0 belongs to whoever holds the lease: an exclusive flock on the lease file (/tmp/pulse_gpu0.lease; the
1285 | +environment variable PP_GPU0_LEASE overrides it), the holder recorded in the file. Entry points take it:
1286 | +scripts/pulse_check_run.sh on fd 8 for the whole run (preflight and run_fresh inherit that descriptor), and run_fresh,
1287 | +replay, preflight, backtest and GPU test sessions with lease() when started on their own. held() is a check, never an
1288 | +acquisition: true in a process that took the lease with lease(), or that holds a descriptor whose open file description
1289 | +holds the flock while it is held (a private probe first proves the lock is held at all; a second flock then succeeds
1290 | +only on the holding description). require() runs before every load AND every use of a loaded model: no lease, no load.
1291 | +
1292 | +ONE MODEL AT A TIME. swap_to(key) is the one way anything gets onto GPU0. It refuses a foreign GPU0 user, unloads
1293 | +everything else this run has resident (its Model objects; its models on the GPU0 Ollama via keep_alive=0, confirmed on
1294 | +/api/ps), collects garbage and empties torch's cache, then waits until nvidia-smi shows GPU0 free >= REQUIREMENT_MIB[key]
1295 | ++ MARGIN_MIB (MARGIN_MIB alone for a model already resident), re-checking for a foreign user while it waits. A Model
1296 | +(whisper(), model()) loads through swap_to on first use, is deleted by any later swap, and loads again through swap_to
1297 | +when used again; its calls re-resolve the live object and run inside guard(). The GPU0 work of a run is done from one
1298 | +thread (the PeakSampler only reads nvidia-smi).
1299 | +
1300 | +FOREIGN. Not this run's: a GPU0 compute process other than this process, its descendants and the processes holding the
1301 | +lease file open (the wrapper that holds it); a model resident on the shared GPU0 Ollama that this process did not
1302 | +request; GPU0 memory no listed process accounts for, beyond UNLISTED_MAX_MIB. A foreign user is named and the run HOLDs;
1303 | +nothing of it is unloaded or killed.
1304 | +
1305 | +STOPS. Every refusal is a Gpu0Stop, a BaseException, so no `except Exception` between a load and the stage runner can
1306 | +turn it into another error ('transcription failed' hid an out-of-memory on Nov 12, E-FAIL-052): GpuOOM (a CUDA / NVENC
1307 | +out-of-memory inside guard() or a finished subprocess), Gpu0Foreign, LeaseMissing, LeaseBusy, Gpu0NotFree (the memory
1308 | +did not come free in time), Gpu0Unreadable (nvidia-smi, ss or the Ollama listener cannot be read: never 'nothing
1309 | +there'). run_fresh's stage runner owns the one retry of an out-of-memory and turns every other stop into a HOLD."""
1310 | +import contextlib
1311 | +import fcntl
1312 | +import gc
1313 | +import json
1314 | +import os
1315 | +import re
1316 | +import subprocess
1317 | +import sys
1318 | +import threading
1319 | +import time
1320 | +import urllib.error
1321 | +import urllib.request
1322 | +
1323 | +os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")   # CUDA device 0 = nvidia-smi GPU 0 (before any CUDA init)
1324 | +
1325 | +DEFAULT_LEASE = "/tmp/pulse_gpu0.lease"
1326 | +OLLAMA_HOST = "127.0.0.1:11434"            # the GPU0 Ollama listener (story_semantics.LLM_HOST)
1327 | +MARGIN_MIB = 1024
1328 | +UNLISTED_MAX_MIB = 1024                    # GPU0 memory no listed compute process accounts for, beyond this = foreign
1329 | +# Peak GPU0 memory one load needs (MiB, its process's CUDA context included): the peak measured on this host's 24564 MiB
1330 | +# GPU0 by pipeline/measure_gpu0.py on 2026-11-12 (Whisper keys on 600 s of speech; DoD 'L-r GPU0 requirements'), rounded
1331 | +# up by ~5%; swap_to adds MARGIN_MIB. A key missing here can never be loaded.
1332 | +REQUIREMENT_MIB = {
1333 | +    "ollama:gemma3:27b": 20600,            # resident 20548-20559 (nvidia-smi 01:43 / 01:55 ET); measured peak 19241
1334 | +    "whisper:large-v3": 6000,              # measured 5657 (beam 5, word timestamps, 600 s)
1335 | +    "whisper:large-v3:batched": 9600,      # measured 9145 (batch 16 full: 600 s)
1336 | +    "whisper:distil-large-v3:batched": 5700,   # measured 5401 (batch 16 full: 600 s)
1337 | +    "whisper:medium": 2800,                # measured 2649
1338 | +    "embedder": 1500,                      # measured 1379 (bge-base fp16, 64 x 512 tokens)
1339 | +    "resemblyzer": 850,                    # measured 775
1340 | +    "nvenc": 600,                          # measured 536 (one 1080x1920 h264_nvenc encode at a time)
1341 | +}
1342 | +WAIT_S = 180
1343 | +
1344 | +
1345 | +class Gpu0Stop(BaseException):
1346 | +    """A GPU0 refusal. A BaseException on purpose: it passes every `except Exception` up to the stage runner."""
1347 | +
1348 | +
1349 | +class GpuOOM(Gpu0Stop):
1350 | +    """A CUDA / NVENC out-of-memory (the original exception, when there is one, is its __cause__)."""
1351 | +
1352 | +
1353 | +class Gpu0Foreign(Gpu0Stop):
1354 | +    """GPU0 is used by something that is not this run's."""
1355 | +
1356 | +
1357 | +class LeaseMissing(Gpu0Stop):
1358 | +    """A GPU0 load or use in a process that does not hold the lease (or not on GPU0 only)."""
1359 | +
1360 | +
1361 | +class LeaseBusy(Gpu0Stop):
1362 | +    """Another owner holds the lease."""
1363 | +
1364 | +
1365 | +class Gpu0NotFree(Gpu0Stop):
1366 | +    """The memory a load needs did not come free in time."""
1367 | +
1368 | +
1369 | +class Gpu0Unreadable(Gpu0Stop):
1370 | +    """nvidia-smi, ss or the GPU0 Ollama listener cannot be read."""
1371 | +
1372 | +
1373 | +_lock = threading.RLock()
1374 | +_own = {}           # lease path -> {"file", "pid", "depth"}: this process's own lease() holdings
1375 | +_resident = []      # Model objects loaded on GPU0 by this process
1376 | +_ollama_ours = set()    # models this process asked the GPU0 Ollama for (swap_to('ollama:...'))
1377 | +_events = []        # every swap's evidence (run_fresh copies it into PROVENANCE)
1378 | +_gen = [0]          # bumped whenever the resident set changes (LocalLLM re-swaps only when it moved)
1379 | +
1380 | +
1381 | +# ── the lease ──
1382 | +
1383 | +def lease_path():
1384 | +    return os.path.realpath(os.environ.get("PP_GPU0_LEASE", DEFAULT_LEASE))
1385 | +
1386 | +
1387 | +def _fds_on(target):
1388 | +    out = []
1389 | +    for name in os.listdir("/proc/self/fd"):
1390 | +        try:
1391 | +            if os.path.realpath(os.readlink(f"/proc/self/fd/{name}")) == target:
1392 | +                out.append(int(name))
1393 | +        except (OSError, ValueError):
1394 | +            continue
1395 | +    return out
1396 | +
1397 | +
1398 | +def _locked(target):
1399 | +    """True when some open file description holds the flock (probed on a private one, released at once); an
1400 | +    unopenable lease file counts as held (never 'free')."""
1401 | +    try:
1402 | +        f = open(target, "a+")
1403 | +    except OSError:
1404 | +        return True
1405 | +    with f:
1406 | +        try:
1407 | +            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
1408 | +        except OSError:
1409 | +            return True
1410 | +        fcntl.flock(f, fcntl.LOCK_UN)              # this probe's own private description only
1411 | +        return False
1412 | +
1413 | +
1414 | +def held():
1415 | +    """True when this process holds the lease (see the module docstring). A check, never an acquisition: with the lock
1416 | +    free no descriptor is probed. (Were it released between the two probes, the second could take it on this
1417 | +    process's own descriptor: the process then holds it.)"""
1418 | +    target = lease_path()
1419 | +    with _lock:
1420 | +        h = _own.get(target)
1421 | +        if h and h["pid"] == os.getpid():
1422 | +            return True
1423 | +    fds = _fds_on(target)
1424 | +    if not fds or not _locked(target):
1425 | +        return False
1426 | +    for fd in fds:
1427 | +        try:
1428 | +            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # succeeds only on the holding description
1429 | +            return True
1430 | +        except OSError:
1431 | +            continue
1432 | +    return False
1433 | +
1434 | +
1435 | +def holder():
1436 | +    """The recorded holder {"pid", "owner", "since"} while the lease is held, None when it is free."""
1437 | +    target = lease_path()
1438 | +    if not _locked(target):
1439 | +        return None
1440 | +    try:
1441 | +        with open(target) as f:
1442 | +            return _record(f)
1443 | +    except OSError as e:
1444 | +        return {"pid": None, "owner": f"lease file unreadable ({type(e).__name__})"}
1445 | +
1446 | +
1447 | +def _record(f):
1448 | +    try:
1449 | +        rec = json.loads(os.pread(f.fileno(), 4096, 0).decode(errors="replace") or "{}")
1450 | +    except (OSError, ValueError):
1451 | +        rec = {}
1452 | +    return rec if isinstance(rec, dict) else {}
1453 | +
1454 | +
1455 | +@contextlib.contextmanager
1456 | +def lease(owner, wait_s=0.0, poll_s=0.2):
1457 | +    """Hold the lease for the block. Re-entrant (any thread) where this process took it: the descriptor closes when the
1458 | +    last holder leaves; custody of an inherited descriptor is used as is (its owner releases it); otherwise acquired
1459 | +    within wait_s, or LeaseBusy naming the holder. Released by closing the descriptor (never LOCK_UN)."""
1460 | +    target = lease_path()
1461 | +    with _lock:
1462 | +        h = _own.get(target)
1463 | +        if h is not None and h["pid"] == os.getpid():
1464 | +            h["depth"] += 1
1465 | +        else:
1466 | +            h = None
1467 | +    if h is None and held():
1468 | +        yield
1469 | +        return
1470 | +    if h is None:
1471 | +        f = open(target, "a+")
1472 | +        t0 = time.time()
1473 | +        while True:
1474 | +            try:
1475 | +                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
1476 | +                break
1477 | +            except OSError:
1478 | +                if time.time() - t0 >= wait_s:
1479 | +                    rec = _record(f)
1480 | +                    f.close()
1481 | +                    raise LeaseBusy(f"the GPU0 lease is held by {rec.get('owner', 'an unrecorded owner')} "
1482 | +                                    f"(pid {rec.get('pid')})") from None
1483 | +                time.sleep(poll_s)
1484 | +        f.seek(0)
1485 | +        f.truncate()
1486 | +        json.dump({"pid": os.getpid(), "owner": owner, "since": time.time()}, f)
1487 | +        f.flush()
1488 | +        with _lock:
1489 | +            h = _own[target] = {"file": f, "pid": os.getpid(), "depth": 1}
1490 | +    try:
1491 | +        yield
1492 | +    finally:
1493 | +        with _lock:
1494 | +            h["depth"] -= 1
1495 | +            if h["depth"] == 0:
1496 | +                if _own.get(target) is h:
1497 | +                    _own.pop(target)
1498 | +                h["file"].close()
1499 | +
1500 | +
1501 | +def require(what):
1502 | +    """No lease, no load; GPU0 only (GPU1 is quarantined), CUDA device 0 being nvidia-smi GPU 0."""
1503 | +    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
1504 | +        raise LeaseMissing(f"{what}: GPU0 loads need CUDA_VISIBLE_DEVICES=0 (it is "
1505 | +                           f"{os.environ.get('CUDA_VISIBLE_DEVICES')!r}; GPU1 is quarantined)")
1506 | +    if os.environ.get("CUDA_DEVICE_ORDER") != "PCI_BUS_ID":
1507 | +        raise LeaseMissing(f"{what}: CUDA_DEVICE_ORDER must be PCI_BUS_ID (CUDA device 0 = nvidia-smi GPU 0)")
1508 | +    if not held():
1509 | +        raise LeaseMissing(f"{what}: a GPU0 load without the GPU0 lease (law L-r: no lease, no load); "
1510 | +                           f"holder: {holder()}")
1511 | +
1512 | +
1513 | +# ── what is on GPU0 ──
1514 | +
1515 | +def _smi(args, timeout=15):
1516 | +    try:
1517 | +        r = subprocess.run(["nvidia-smi", *args], capture_output=True, text=True, timeout=timeout)
1518 | +    except (OSError, subprocess.TimeoutExpired) as e:
1519 | +        raise Gpu0Unreadable(f"nvidia-smi: {type(e).__name__}") from None
1520 | +    if r.returncode != 0:
1521 | +        raise Gpu0Unreadable(f"nvidia-smi exit {r.returncode}: {r.stderr.strip()[:200]}")
1522 | +    return r.stdout
1523 | +
1524 | +
1525 | +def memory():
1526 | +    """(used_mib, total_mib) of GPU index 0."""
1527 | +    out = _smi(["-i", "0", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"])
1528 | +    try:
1529 | +        used, total = (int(x) for x in out.strip().split(","))
1530 | +    except ValueError:
1531 | +        raise Gpu0Unreadable(f"nvidia-smi memory line unreadable: {out.strip()[:80]!r}") from None
1532 | +    return used, total
1533 | +
1534 | +
1535 | +def processes():
1536 | +    """[(pid, name, MiB or None)] of every compute process on GPU index 0; an unreadable line is a Gpu0Unreadable."""
1537 | +    uuid = _smi(["-i", "0", "--query-gpu=uuid", "--format=csv,noheader"]).strip()
1538 | +    if not uuid:
1539 | +        raise Gpu0Unreadable("nvidia-smi names no GPU 0")
1540 | +    out = []
1541 | +    for line in _smi(["--query-compute-apps=pid,gpu_uuid,used_memory,process_name",
1542 | +                      "--format=csv,noheader,nounits"]).strip().splitlines():
1543 | +        p = [x.strip() for x in line.split(",", 3)]
1544 | +        if len(p) != 4 or not p[0].isdigit():
1545 | +            raise Gpu0Unreadable(f"nvidia-smi compute-apps line unreadable: {line[:80]!r}")
1546 | +        if p[1] == uuid:
1547 | +            out.append((int(p[0]), os.path.basename(p[3]), int(p[2]) if p[2].isdigit() else None))
1548 | +    return out
1549 | +
1550 | +
1551 | +def describe(procs):
1552 | +    return ", ".join(f"pid {p if p is not None else '?'} {n} {m} MiB" for p, n, m in procs) or "no GPU0 process"
1553 | +
1554 | +
1555 | +def _children(pid):
1556 | +    out = set()
1557 | +    try:
1558 | +        tids = os.listdir(f"/proc/{pid}/task")
1559 | +    except OSError:
1560 | +        return out
1561 | +    for tid in tids:
1562 | +        try:
1563 | +            with open(f"/proc/{pid}/task/{tid}/children") as f:
1564 | +                out |= {int(x) for x in f.read().split()}
1565 | +        except (OSError, ValueError):
1566 | +            continue
1567 | +    return out
1568 | +
1569 | +
1570 | +def _descendants(root=None):
1571 | +    out, todo = set(), [os.getpid() if root is None else root]
1572 | +    while todo:
1573 | +        for k in _children(todo.pop()):
1574 | +            if k not in out:
1575 | +                out.add(k)
1576 | +                todo.append(k)
1577 | +    return out
1578 | +
1579 | +
1580 | +def _lease_holders():
1581 | +    """Pids with the lease file open (the wrapper that holds it on fd 8, a process it handed the descriptor to)."""
1582 | +    target, out = lease_path(), set()
1583 | +    for pid in os.listdir("/proc"):
1584 | +        if not pid.isdigit():
1585 | +            continue
1586 | +        try:
1587 | +            for name in os.listdir(f"/proc/{pid}/fd"):
1588 | +                try:
1589 | +                    if os.path.realpath(os.readlink(f"/proc/{pid}/fd/{name}")) == target:
1590 | +                        out.add(int(pid))
1591 | +                        break
1592 | +                except OSError:
1593 | +                    continue
1594 | +        except OSError:
1595 | +            continue
1596 | +    return out
1597 | +
1598 | +
1599 | +def _ollama_pids():
1600 | +    """The GPU0 Ollama listener (the process on its port) and every process under it."""
1601 | +    port = OLLAMA_HOST.rsplit(":", 1)[1]
1602 | +    try:
1603 | +        r = subprocess.run(["ss", "-ltnpH", f"sport = :{port}"], capture_output=True, text=True, timeout=10)
1604 | +    except (OSError, subprocess.TimeoutExpired) as e:
1605 | +        raise Gpu0Unreadable(f"cannot read the GPU0 Ollama listener: {type(e).__name__}") from None
1606 | +    if r.returncode != 0:
1607 | +        raise Gpu0Unreadable(f"ss exit {r.returncode}: {r.stderr.strip()[:200]}")
1608 | +    serve = {int(p) for p in re.findall(r"pid=(\d+)", r.stdout)}
1609 | +    if r.stdout.strip() and not serve:
1610 | +        raise Gpu0Unreadable("the GPU0 Ollama listener's pid is not visible to this user")
1611 | +    out = set(serve)
1612 | +    for p in serve:
1613 | +        out |= _descendants(p)
1614 | +    return out
1615 | +
1616 | +
1617 | +def foreign():
1618 | +    """[(pid, what, MiB)] using GPU0 that is not this run's (see the module docstring)."""
1619 | +    procs = processes()
1620 | +    ollama = _ollama_pids()
1621 | +    ours = {os.getpid()} | _descendants() | _lease_holders() | ollama
1622 | +    out = [p for p in procs if p[0] not in ours]
1623 | +    for name, mib in ollama_resident():
1624 | +        if name not in _ollama_ours:
1625 | +            out.append((min(ollama) if ollama else None, f"ollama model {name} (not requested by this run)", mib))
1626 | +    used, _ = memory()
1627 | +    unlisted = used - sum(m or 0 for _, _, m in procs)
1628 | +    if unlisted > UNLISTED_MAX_MIB:
1629 | +        out.append((None, "GPU0 memory no listed compute process accounts for", unlisted))
1630 | +    return out
1631 | +
1632 | +
1633 | +# ── the GPU0 Ollama ──
1634 | +
1635 | +def _ollama(path, body=None, timeout=30):
1636 | +    req = urllib.request.Request(f"http://{OLLAMA_HOST}{path}",
1637 | +                                 data=None if body is None else json.dumps(body).encode(),
1638 | +                                 headers={"Content-Type": "application/json"})
1639 | +    return json.loads(urllib.request.urlopen(req, timeout=timeout).read() or b"{}")
1640 | +
1641 | +
1642 | +def ollama_resident():
1643 | +    """[(name, MiB on the GPU)] of the models resident on the GPU0 Ollama ([] when nothing listens there)."""
1644 | +    try:
1645 | +        models = _ollama("/api/ps").get("models", [])
1646 | +        return [(m["name"], int(m.get("size_vram") or 0) // (1024 * 1024)) for m in models]
1647 | +    except urllib.error.URLError as e:
1648 | +        if isinstance(getattr(e, "reason", None), ConnectionRefusedError):
1649 | +            return []
1650 | +        raise Gpu0Unreadable(f"Ollama {OLLAMA_HOST} /api/ps: {e}") from None
1651 | +    except (OSError, ValueError, KeyError, TypeError) as e:
1652 | +        raise Gpu0Unreadable(f"Ollama {OLLAMA_HOST} /api/ps: {type(e).__name__}: {e}") from None
1653 | +
1654 | +
1655 | +def ollama_loaded():
1656 | +    return [n for n, _ in ollama_resident()]
1657 | +
1658 | +
1659 | +def _ollama_unload(names, wait_s=60):
1660 | +    """Unload these models (this run's own: swap_to proved nothing foreign first) and confirm on /api/ps."""
1661 | +    for n in names:
1662 | +        try:
1663 | +            _ollama("/api/generate", {"model": n, "keep_alive": 0}, timeout=120)
1664 | +        except (OSError, ValueError) as e:
1665 | +            raise Gpu0NotFree(f"Ollama would not unload {n}: {type(e).__name__}: {e}") from None
1666 | +    t0 = time.time()
1667 | +    while True:
1668 | +        left = [n for n in ollama_loaded() if n in names]
1669 | +        if not left:
1670 | +            _ollama_ours.difference_update(names)
1671 | +            return list(names)
1672 | +        if time.time() - t0 > wait_s:
1673 | +            raise Gpu0NotFree(f"Ollama still holds {left} {wait_s}s after keep_alive=0")
1674 | +        time.sleep(1)
1675 | +
1676 | +
1677 | +# ── swaps ──
1678 | +
1679 | +def generation():
1680 | +    return _gen[0]
1681 | +
1682 | +
1683 | +def events():
1684 | +    return list(_events)
1685 | +
1686 | +
1687 | +def _empty_caches():
1688 | +    gc.collect()
1689 | +    torch = sys.modules.get("torch")
1690 | +    if torch is not None:
1691 | +        try:
1692 | +            if torch.cuda.is_initialized():
1693 | +                torch.cuda.empty_cache()
1694 | +        except Exception as e:
1695 | +            if is_oom(e):
1696 | +                raise GpuOOM(f"torch empty_cache: {e}") from e
1697 | +
1698 | +
1699 | +def _ollama_key(key):
1700 | +    return key[len("ollama:"):] if key.startswith("ollama:") else None
1701 | +
1702 | +
1703 | +def _refuse_foreign(what):
1704 | +    f = foreign()
1705 | +    if f:
1706 | +        raise Gpu0Foreign(f"{what}: GPU0 is used by something that is not this run's: {describe(f)}")
1707 | +
1708 | +
1709 | +def swap_to(key, wait_s=WAIT_S, poll_s=2.0):
1710 | +    """Make GPU0 ready for `key` and nothing else of this run's (see the module docstring). Returns the evidence it
1711 | +    recorded. Raises a Gpu0Stop."""
1712 | +    require(f"swap_to({key})")
1713 | +    if key not in REQUIREMENT_MIB:
1714 | +        raise Gpu0NotFree(f"{key}: no measured GPU0 requirement (gpu0.REQUIREMENT_MIB): never loaded")
1715 | +    with _lock:
1716 | +        _refuse_foreign(f"swap_to({key})")
1717 | +        ev = {"key": key, "at": time.time(), "before": memory(), "unloaded": []}
1718 | +        for m in [m for m in _resident if m.key != key]:
1719 | +            m.unload()
1720 | +            ev["unloaded"].append(m.key)
1721 | +        name = _ollama_key(key)
1722 | +        drop = [n for n in ollama_loaded() if n != name]          # all this run's: foreign() passed
1723 | +        ev["unloaded"] += [f"ollama:{n}" for n in _ollama_unload(drop)]
1724 | +        if name:
1725 | +            _ollama_ours.add(name)
1726 | +        already = name in ollama_loaded() if name else any(m.key == key for m in _resident)
1727 | +        _empty_caches()
1728 | +        need = MARGIN_MIB if already else REQUIREMENT_MIB[key] + MARGIN_MIB
1729 | +        t0 = time.time()
1730 | +        while True:
1731 | +            used, total = memory()
1732 | +            if total - used >= need:
1733 | +                break
1734 | +            if time.time() - t0 > wait_s:
1735 | +                raise Gpu0NotFree(f"{key}: GPU0 has {total - used} MiB free {wait_s}s after the swap, needs {need} "
1736 | +                                  f"({'already resident: the margin' if already else f'{REQUIREMENT_MIB[key]} + margin {MARGIN_MIB}'}); "
1737 | +                                  f"on GPU0: {describe(processes())}")
1738 | +            time.sleep(poll_s)
1739 | +            _refuse_foreign(f"swap_to({key}) while waiting")
1740 | +        if not already:
1741 | +            _gen[0] += 1
1742 | +        ev.update(after=[used, total], free_mib=total - used, already_resident=already,
1743 | +                  waited_s=round(time.time() - t0, 1))
1744 | +        _events.append(ev)
1745 | +        return ev
1746 | +
1747 | +
1748 | +def release_all(wait_s=WAIT_S, poll_s=2.0):
1749 | +    """Unload everything this run has on GPU0 (its Models, its models on the GPU0 Ollama), then wait until nvidia-smi
1750 | +    shows GPU0 free: room for the largest single model (max REQUIREMENT_MIB + MARGIN_MIB). Under the lease; a foreign
1751 | +    user is refused, never unloaded. Returns evidence; Gpu0NotFree names every GPU0 process when it does not come free."""
1752 | +    require("release_all")
1753 | +    need = max(REQUIREMENT_MIB.values()) + MARGIN_MIB
1754 | +    with _lock:
1755 | +        _refuse_foreign("release_all")
1756 | +        ev = {"at": time.time(), "before": memory(), "unloaded": []}
1757 | +        for m in list(_resident):
1758 | +            m.unload()
1759 | +            ev["unloaded"].append(m.key)
1760 | +        ev["unloaded"] += [f"ollama:{n}" for n in _ollama_unload(ollama_loaded())]
1761 | +        _empty_caches()
1762 | +        _gen[0] += 1
1763 | +        t0 = time.time()
1764 | +        while True:
1765 | +            used, total = memory()
1766 | +            if total - used >= need:
1767 | +                ev.update(after=[used, total], waited_s=round(time.time() - t0, 1))
1768 | +                return ev
1769 | +            if time.time() - t0 > wait_s:
1770 | +                raise Gpu0NotFree(f"GPU0 has {total - used} MiB free {wait_s}s after releasing everything this run "
1771 | +                                  f"owns (free means >= {need}); on GPU0: {describe(processes())}")
1772 | +            time.sleep(poll_s)
1773 | +            _refuse_foreign("release_all while waiting")
1774 | +
1775 | +
1776 | +# ── out of memory ──
1777 | +
1778 | +_OOM = re.compile(r"out of memory|CUDA_ERROR_OUT_OF_MEMORY|cudaErrorMemoryAllocation|CUBLAS_STATUS_ALLOC_FAILED|"
1779 | +                  r"CUDNN_STATUS_ALLOC_FAILED|NV_ENC_ERR_OUT_OF_MEMORY|OutOfMemoryError|cudaMalloc failed|"
1780 | +                  r"unable to allocate (?:a )?(?:CUDA|GPU|CUDA\d+) buffer|failed to allocate (?:CUDA|GPU)", re.I)
1781 | +
1782 | +
1783 | +def is_oom(e):
1784 | +    """True for a CUDA / NVENC / Ollama out-of-memory, read from the exception, its type and any captured stderr."""
1785 | +    if isinstance(e, GpuOOM):
1786 | +        return True
1787 | +    parts = [type(e).__name__, str(e)]
1788 | +    for attr in ("stderr", "output"):
1789 | +        v = getattr(e, attr, None)
1790 | +        if isinstance(v, bytes):
1791 | +            v = v.decode(errors="replace")
1792 | +        if isinstance(v, str):
1793 | +            parts.append(v[-4000:])
1794 | +    return bool(_OOM.search(" ".join(parts)))
1795 | +
1796 | +
1797 | +def raise_if_oom(result, what):
1798 | +    """A finished subprocess (run with capture_output) that failed on a CUDA / NVENC out-of-memory leaves as GpuOOM,
1799 | +    never as the caller's later 'render failed' (law L-r item 3)."""
1800 | +    if getattr(result, "returncode", 0) != 0:
1801 | +        err = result.stderr.decode(errors="replace") if isinstance(result.stderr, bytes) else (result.stderr or "")
1802 | +        if _OOM.search(err):
1803 | +            raise GpuOOM(f"{what}: out of memory ({err.strip()[-300:]})")
1804 | +
1805 | +
1806 | +@contextlib.contextmanager
1807 | +def guard(what):
1808 | +    """A CUDA out-of-memory raised inside the block leaves it as GpuOOM (nothing can rename it on the way up)."""
1809 | +    try:
1810 | +        yield
1811 | +    except Gpu0Stop:
1812 | +        raise
1813 | +    except Exception as e:
1814 | +        if is_oom(e):
1815 | +            raise GpuOOM(f"{what}: CUDA out of memory ({type(e).__name__}: {str(e)[:300]})") from e
1816 | +        raise
1817 | +
1818 | +
1819 | +def guard_iter(it, what):
1820 | +    """Iterate a lazily decoding iterator (faster-whisper segments) with every step inside guard(). The iterator keeps
1821 | +    its model alive until it is exhausted or dropped."""
1822 | +    while True:
1823 | +        with guard(what):
1824 | +            try:
1825 | +                x = next(it)
1826 | +            except StopIteration:
1827 | +                return
1828 | +        yield x
1829 | +
1830 | +
1831 | +def drop_traceback(e):
1832 | +    """Break the frames an exception chain pins (the failed call's model and tensors), so a release can free them."""
1833 | +    seen = set()
1834 | +    while e is not None and id(e) not in seen:
1835 | +        seen.add(id(e))
1836 | +        e.__traceback__ = None
1837 | +        e = e.__cause__ or e.__context__
1838 | +
1839 | +
1840 | +# ── the only GPU0 models ──
1841 | +
1842 | +class Model:
1843 | +    """A GPU0 object loaded only through swap_to (see the module docstring). Every use checks the lease; a call
1844 | +    re-resolves the live object (a later swap deleted it: it loads again through swap_to) and runs inside guard();
1845 | +    only plain values (str, int, float, bool, None) of the object are readable directly."""
1846 | +
1847 | +    def __init__(self, key, build):
1848 | +        self.key, self._build, self._obj = key, build, None
1849 | +
1850 | +    def get(self):
1851 | +        require(self.key)
1852 | +        with _lock:
1853 | +            if self._obj is None:
1854 | +                swap_to(self.key)
1855 | +                with guard(f"{self.key}: load"):
1856 | +                    self._obj = self._build()
1857 | +                _resident.append(self)
1858 | +            return self._obj
1859 | +
1860 | +    def unload(self):
1861 | +        with _lock:
1862 | +            self._obj = None
1863 | +            if self in _resident:
1864 | +                _resident.remove(self)
1865 | +
1866 | +    @property
1867 | +    def loaded(self):
1868 | +        return self._obj is not None
1869 | +
1870 | +    def __getattr__(self, name):
1871 | +        if name.startswith("_"):
1872 | +            raise AttributeError(name)
1873 | +        attr = getattr(self.get(), name)
1874 | +        if callable(attr):
1875 | +            del attr                                     # no stale reference: each call re-resolves the live object
1876 | +            key = self.key
1877 | +
1878 | +            def call(*a, **k):
1879 | +                obj = self.get()
1880 | +                with guard(f"{key}: {name}"):
1881 | +                    return getattr(obj, name)(*a, **k)
1882 | +            return call
1883 | +        if isinstance(attr, (str, int, float, bool, type(None))):
1884 | +            return attr
1885 | +        raise AttributeError(f"gpu0.Model {self.key}: {name!r} is an object inside the model; reach the model only "
1886 | +                             f"through its calls (law L-r: nothing may keep it alive past a swap)")
1887 | +
1888 | +    def __call__(self, *a, **k):
1889 | +        obj = self.get()
1890 | +        with guard(f"{self.key}: call"):
1891 | +            return obj(*a, **k)
1892 | +
1893 | +
1894 | +class Whisper(Model):
1895 | +    def transcribe(self, *a, **k):
1896 | +        obj = self.get()
1897 | +        with guard(f"{self.key}: transcribe"):
1898 | +            segments, info = obj.transcribe(*a, **k)
1899 | +        del obj
1900 | +        return guard_iter(iter(segments), f"{self.key}: decode"), info
1901 | +
1902 | +
1903 | +_models = {}
1904 | +
1905 | +
1906 | +def whisper(name, batched=False):
1907 | +    """The process's one faster-whisper model `name` (float16 on GPU0; batched = a BatchedInferencePipeline)."""
1908 | +    key = f"whisper:{name}" + (":batched" if batched else "")
1909 | +    with _lock:
1910 | +        if key not in _models:
1911 | +            def build():
1912 | +                from faster_whisper import WhisperModel
1913 | +                m = WhisperModel(name, device="cuda", compute_type="float16")
1914 | +                if batched:
1915 | +                    from faster_whisper import BatchedInferencePipeline
1916 | +                    m = BatchedInferencePipeline(model=m)
1917 | +                return m
1918 | +            _models[key] = Whisper(key, build)
1919 | +        return _models[key]
1920 | +
1921 | +
1922 | +def model(key, build):
1923 | +    """The process's one Model for `key` (a torch module, an encoder...): `build` makes the loaded object."""
1924 | +    with _lock:
1925 | +        if key not in _models:
1926 | +            _models[key] = Model(key, build)
1927 | +        return _models[key]
1928 | +
1929 | +
1930 | +# ── evidence ──
1931 | +
1932 | +class PeakSampler:
1933 | +    """GPU0 memory.used sampled every interval_s on a daemon thread; the peak per label (run_fresh: the stage). A sampled
1934 | +    maximum: a lower bound of the true peak (transients shorter than the interval are missed)."""
1935 | +
1936 | +    def __init__(self, interval_s=1.0):
1937 | +        self.interval_s, self.label, self.peaks, self.errors = interval_s, None, {}, 0
1938 | +        self._stop = threading.Event()
1939 | +        self._thread = threading.Thread(target=self._run, daemon=True)
1940 | +
1941 | +    def start(self):
1942 | +        self._thread.start()
1943 | +        return self
1944 | +
1945 | +    def set(self, label):
1946 | +        self.label = label
1947 | +        self._sample()
1948 | +
1949 | +    def _sample(self):
1950 | +        label = self.label                       # read before the measurement: a sample never crosses a stage edge
1951 | +        try:
1952 | +            used, _ = memory()
1953 | +        except Gpu0Stop:
1954 | +            self.errors += 1
1955 | +            return
1956 | +        if label is not None and self.label == label:
1957 | +            self.peaks[label] = max(self.peaks.get(label, 0), used)
1958 | +
1959 | +    def _run(self):
1960 | +        while not self._stop.wait(self.interval_s):
1961 | +            self._sample()
1962 | +
1963 | +    def stop(self):
1964 | +        self._stop.set()
1965 | +        self._thread.join(timeout=5)
1966 | +        self._sample()
1967 | +        return dict(self.peaks)
1968 | diff --git a/pipeline/test_gpu0.py b/pipeline/test_gpu0.py
1969 | new file mode 100644
1970 | index 00000000..8d61f11f
1971 | --- /dev/null
1972 | +++ b/pipeline/test_gpu0.py
1973 | @@ -0,0 +1,450 @@
1974 | +#!/usr/bin/env python3
1975 | +"""Law L-r GPU0 NEVER SURPRISES A RUN (pipeline/gpu0.py): CPU tests with a private lease file and stubbed nvidia-smi /
1976 | +Ollama readings, so they never touch GPU0. The GPU must-fails (a real allocation on GPU0 before a stage) and the
1977 | +back-to-back runs with the per-stage peak table are pipeline/test_gpu0_live.py (GPU0, under the lease)."""
1978 | +import json
1979 | +import os
1980 | +import subprocess
1981 | +import sys
1982 | +import tempfile
1983 | +import textwrap
1984 | +import unittest
1985 | +from unittest import mock
1986 | +
1987 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
1988 | +sys.path.insert(0, PIPELINE)
1989 | +import gpu0  # noqa: E402
1990 | +
1991 | +
1992 | +class Box(unittest.TestCase):
1993 | +    """A private lease file, CUDA_VISIBLE_DEVICES=0, and a fake GPU0: memory / processes / Ollama are stubs."""
1994 | +
1995 | +    def setUp(self):
1996 | +        self.tmp = tempfile.mkdtemp(prefix="gpu0t_")
1997 | +        self.env = mock.patch.dict(os.environ, {"PP_GPU0_LEASE": os.path.join(self.tmp, "lease"),
1998 | +                                                "CUDA_VISIBLE_DEVICES": "0"})
1999 | +        self.env.start()
2000 | +        self.addCleanup(self.env.stop)
2001 | +        self.used = [100]                 # MiB used on the fake GPU0 (a list: tests change it)
2002 | +        self.procs = []                   # fake GPU0 compute processes
2003 | +        self.ollama = []                  # fake resident Ollama models
2004 | +        self.unloaded = []
2005 | +        for name, fn in (("memory", lambda: (self.used[0], 24564)), ("processes", lambda: list(self.procs)),
2006 | +                         ("ollama_resident", lambda: [(n, 0) for n in self.ollama]), ("_ollama_pids", lambda: {999999}),
2007 | +                         ("_ollama_unload", self._unload)):
2008 | +            p = mock.patch.object(gpu0, name, side_effect=fn)
2009 | +            p.start()
2010 | +            self.addCleanup(p.stop)
2011 | +        saved = (list(gpu0._resident), dict(gpu0._models), list(gpu0._events), set(gpu0._ollama_ours))
2012 | +        gpu0._resident.clear()
2013 | +        gpu0._models.clear()
2014 | +        gpu0._ollama_ours.clear()
2015 | +
2016 | +        def restore():
2017 | +            gpu0._resident[:] = saved[0]
2018 | +            gpu0._models.clear()
2019 | +            gpu0._models.update(saved[1])
2020 | +            gpu0._events[:] = saved[2]
2021 | +            gpu0._ollama_ours.clear()
2022 | +            gpu0._ollama_ours.update(saved[3])
2023 | +        self.addCleanup(restore)
2024 | +
2025 | +    def _unload(self, names, wait_s=60):
2026 | +        self.ollama[:] = [n for n in self.ollama if n not in names]
2027 | +        self.unloaded += list(names)
2028 | +        gpu0._ollama_ours.difference_update(names)
2029 | +        return list(names)
2030 | +
2031 | +
2032 | +class TestLease(Box):
2033 | +    def test_no_lease_no_load_and_gpu0_only(self):
2034 | +        with self.assertRaises(gpu0.LeaseMissing):
2035 | +            gpu0.require("a load")
2036 | +        with gpu0.lease("test"):
2037 | +            gpu0.require("a load")
2038 | +            with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0,1"}):
2039 | +                with self.assertRaisesRegex(gpu0.LeaseMissing, "GPU1 is quarantined"):
2040 | +                    gpu0.require("a load")
2041 | +        self.assertFalse(gpu0.held())
2042 | +
2043 | +    def test_held_is_a_check_never_an_acquisition(self):
2044 | +        f = open(gpu0.lease_path(), "a+")                # this process has the file open, nobody holds the lock
2045 | +        self.addCleanup(f.close)
2046 | +        self.assertFalse(gpu0.held())
2047 | +        self.assertIsNone(gpu0.holder())                 # still free: held() took nothing
2048 | +        with gpu0.lease("t"):
2049 | +            self.assertTrue(gpu0.held())
2050 | +
2051 | +    def test_a_lease_is_released_by_its_last_holder_across_threads(self):
2052 | +        import threading
2053 | +        inside, leave_a, done_b = threading.Event(), threading.Event(), threading.Event()
2054 | +
2055 | +        def a():
2056 | +            with gpu0.lease("A"):
2057 | +                inside.set()
2058 | +                leave_a.wait(10)
2059 | +
2060 | +        def b():
2061 | +            inside.wait(10)
2062 | +            with gpu0.lease("B"):
2063 | +                leave_a.set()
2064 | +                t.join(10)                                # A has left: B must still hold it
2065 | +                self.assertTrue(gpu0.held())
2066 | +                self.assertIsNotNone(gpu0.holder())
2067 | +            done_b.set()
2068 | +        t = threading.Thread(target=a)
2069 | +        u = threading.Thread(target=b)
2070 | +        t.start(); u.start(); u.join(20)
2071 | +        self.assertTrue(done_b.is_set())
2072 | +        self.assertIsNone(gpu0.holder())                  # released by the last one out
2073 | +
2074 | +    def test_reentrant_and_busy_names_the_holder(self):
2075 | +        with gpu0.lease("outer"):
2076 | +            with gpu0.lease("inner"):
2077 | +                self.assertTrue(gpu0.held())
2078 | +            self.assertTrue(gpu0.held())
2079 | +            code = textwrap.dedent(f"""
2080 | +                import sys; sys.path.insert(0, {PIPELINE!r}); import gpu0
2081 | +                try:
2082 | +                    with gpu0.lease("second"): print("GOT")
2083 | +                except gpu0.LeaseBusy as e: print("BUSY", e)""")
2084 | +            out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60).stdout
2085 | +            self.assertIn("BUSY", out)
2086 | +            self.assertIn("outer", out)                               # the holder is named
2087 | +        self.assertIsNone(gpu0.holder())
2088 | +
2089 | +    def test_an_inherited_descriptor_is_custody_a_reopened_one_is_not(self):
2090 | +        with gpu0.lease("parent"):
2091 | +            fd = gpu0._own[gpu0.lease_path()]["file"].fileno()
2092 | +            os.set_inheritable(fd, True)
2093 | +            code = f"import sys; sys.path.insert(0, {PIPELINE!r}); import gpu0; print(gpu0.held())"
2094 | +            inherited = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60,
2095 | +                                       pass_fds=(fd,)).stdout.strip()
2096 | +            reopened = subprocess.run([sys.executable, "-c", code + f"; f = open({gpu0.lease_path()!r}, 'a+'); "
2097 | +                                       "print(gpu0.held())"], capture_output=True, text=True, timeout=60).stdout.split()
2098 | +        self.assertEqual(inherited, "True")
2099 | +        self.assertEqual(reopened, ["False", "False"])
2100 | +
2101 | +
2102 | +class TestSwap(Box):
2103 | +    def test_a_foreign_process_is_refused_and_named(self):
2104 | +        self.procs[:] = [(424242, "python3", 4000)]
2105 | +        with gpu0.lease("t"):
2106 | +            with self.assertRaisesRegex(gpu0.Gpu0Foreign, "pid 424242 python3 4000 MiB"):
2107 | +                gpu0.swap_to("whisper:large-v3")
2108 | +
2109 | +    def test_everything_else_is_unloaded_and_the_memory_proven_free(self):
2110 | +        built = []
2111 | +        a = gpu0.model("embedder", lambda: built.append("embedder") or object())
2112 | +        b = gpu0.whisper("medium")
2113 | +        self.ollama[:] = ["gemma3:27b"]
2114 | +        gpu0._ollama_ours.add("gemma3:27b")                             # this run asked for it earlier
2115 | +        with gpu0.lease("t"):
2116 | +            with mock.patch.object(b, "_build", lambda: built.append("medium") or object()):
2117 | +                a.get()
2118 | +                self.assertEqual(self.unloaded, ["gemma3:27b"])        # the Ollama model went first
2119 | +                b.get()
2120 | +            self.assertEqual(built, ["embedder", "medium"])
2121 | +            self.assertFalse(a.loaded)                                 # one model at a time
2122 | +            self.assertTrue(b.loaded)
2123 | +            ev = gpu0.events()[-1]
2124 | +            self.assertEqual((ev["key"], ev["unloaded"]), ("whisper:medium", ["embedder"]))
2125 | +
2126 | +    def test_a_model_this_run_did_not_request_is_foreign_and_left_alone(self):
2127 | +        self.ollama[:] = ["qwen3-coder:30b"]                            # another client's job on the shared Ollama
2128 | +        with gpu0.lease("t"):
2129 | +            with self.assertRaisesRegex(gpu0.Gpu0Foreign, "ollama model qwen3-coder:30b .not requested by this run."):
2130 | +                gpu0.swap_to("whisper:large-v3")
2131 | +        self.assertEqual((self.unloaded, self.ollama), ([], ["qwen3-coder:30b"]))   # nothing of it unloaded
2132 | +
2133 | +    def test_memory_no_listed_process_accounts_for_is_foreign(self):
2134 | +        self.used[0] = 9000                                              # e.g. a graphics client nvidia-smi does not list
2135 | +        with gpu0.lease("t"):
2136 | +            with self.assertRaisesRegex(gpu0.Gpu0Foreign, "no listed compute process accounts for 9000 MiB"):
2137 | +                gpu0.swap_to("nvenc")
2138 | +
2139 | +    def test_a_cached_model_is_no_licence_without_the_lease(self):
2140 | +        m = gpu0.model("embedder", lambda: (lambda x: x * 2))
2141 | +        with gpu0.lease("t"):
2142 | +            self.assertEqual(m(21), 42)
2143 | +        with self.assertRaises(gpu0.LeaseMissing):                      # loaded, but the lease is gone
2144 | +            m(21)
2145 | +
2146 | +    def test_a_stored_call_reresolves_and_objects_inside_never_escape(self):
2147 | +        class Enc:
2148 | +            name = "enc"
2149 | +            inner = object()
2150 | +
2151 | +            def embed(self, x):
2152 | +                return x
2153 | +        m = gpu0.model("resemblyzer", Enc)
2154 | +        with gpu0.lease("t"):
2155 | +            call = m.embed
2156 | +            self.assertEqual(m.name, "enc")
2157 | +            with self.assertRaisesRegex(AttributeError, "an object inside the model"):
2158 | +                m.inner
2159 | +            m.unload()                                                   # a later swap deleted it
2160 | +            self.assertEqual(call(7), 7)                                 # the stored call loads it again
2161 | +            self.assertTrue(m.loaded)
2162 | +
2163 | +    def test_memory_that_never_comes_free_is_a_stop_naming_every_process(self):
2164 | +        self.used[0] = 22000
2165 | +        self.procs[:] = [(999999, "ollama", 21000)]                  # the Ollama runner: ours, but not free
2166 | +        need = gpu0.REQUIREMENT_MIB["whisper:large-v3"] + gpu0.MARGIN_MIB
2167 | +        with gpu0.lease("t"):
2168 | +            with self.assertRaisesRegex(gpu0.Gpu0NotFree, rf"needs {need} .*pid 999999 ollama 21000 MiB"):
2169 | +                gpu0.swap_to("whisper:large-v3", wait_s=0, poll_s=0)
2170 | +
2171 | +    def test_an_unknown_model_is_never_loaded(self):
2172 | +        with gpu0.lease("t"):
2173 | +            with self.assertRaisesRegex(gpu0.Gpu0NotFree, "no measured GPU0 requirement"):
2174 | +                gpu0.swap_to("whisper:tiny")
2175 | +
2176 | +    def test_the_model_already_resident_is_kept(self):
2177 | +        self.ollama[:] = ["gemma3:27b"]
2178 | +        gpu0._ollama_ours.add("gemma3:27b")
2179 | +        self.procs[:] = [(999999, "ollama", 20500)]
2180 | +        self.used[0] = 20600                                           # its own memory: not 'not free'
2181 | +        with gpu0.lease("t"):
2182 | +            ev = gpu0.swap_to("ollama:gemma3:27b", wait_s=0)
2183 | +        self.assertEqual((ev["already_resident"], self.unloaded), (True, []))
2184 | +
2185 | +
2186 | +class TestOutOfMemory(Box):
2187 | +    def test_every_spelling_is_recognised_and_nothing_else(self):
2188 | +        cpe = subprocess.CalledProcessError(1, ["ffmpeg"], stderr=b"OpenEncodeSessionEx failed: out of memory (10)")
2189 | +        for e in (RuntimeError("CUDA failed with error out of memory"), cpe,
2190 | +                  type("OutOfMemoryError", (RuntimeError,), {})("CUDA"), RuntimeError("CUBLAS_STATUS_ALLOC_FAILED")):
2191 | +            self.assertTrue(gpu0.is_oom(e), e)
2192 | +        for e in (MemoryError(), OSError(12, "Cannot allocate memory"), RuntimeError("decoder failed"),
2193 | +                  subprocess.CalledProcessError(1, ["ffmpeg"], stderr=b"Invalid data found")):
2194 | +            self.assertFalse(gpu0.is_oom(e), e)
2195 | +
2196 | +    def test_a_stop_passes_every_except_exception(self):
2197 | +        def helper():                                    # the shape of select_passages._whisper_transcribe
2198 | +            try:
2199 | +                with gpu0.guard("whisper: transcribe"):
2200 | +                    raise RuntimeError("CUDA failed with error out of memory")
2201 | +            except Exception:
2202 | +                return None                              # 'transcription failed' (E-FAIL-052)
2203 | +        with self.assertRaisesRegex(gpu0.GpuOOM, "whisper: transcribe: CUDA out of memory"):
2204 | +            helper()
2205 | +
2206 | +    def test_a_finished_nvenc_subprocess_that_ran_out_of_memory_is_named(self):
2207 | +        fail = subprocess.CompletedProcess(["ffmpeg"], 1, b"", b"[h264_nvenc] OpenEncodeSessionEx failed: out of memory (10)")
2208 | +        with self.assertRaisesRegex(gpu0.GpuOOM, "render16 nvenc: out of memory"):
2209 | +            gpu0.raise_if_oom(fail, "render16 nvenc")
2210 | +        gpu0.raise_if_oom(subprocess.CompletedProcess(["ffmpeg"], 1, b"", b"Invalid data found"), "x")   # not OOM
2211 | +        gpu0.raise_if_oom(subprocess.CompletedProcess(["ffmpeg"], 0, b"", b""), "x")                     # success
2212 | +
2213 | +    def test_a_lazily_decoded_out_of_memory_is_converted_too(self):
2214 | +        def segs():
2215 | +            yield 1
2216 | +            raise RuntimeError("CUDA failed with error out of memory")
2217 | +        it = gpu0.guard_iter(segs(), "decode")
2218 | +        self.assertEqual(next(it), 1)
2219 | +        with self.assertRaises(gpu0.GpuOOM):
2220 | +            next(it)
2221 | +
2222 | +    def test_a_model_call_is_guarded_and_a_non_oom_error_is_unchanged(self):
2223 | +        class Enc:
2224 | +            def embed(self, x):
2225 | +                if x == "oom":
2226 | +                    raise RuntimeError("CUDA error: out of memory")
2227 | +                raise ValueError("bad input")
2228 | +        m = gpu0.model("resemblyzer", Enc)
2229 | +        with gpu0.lease("t"):
2230 | +            with self.assertRaises(gpu0.GpuOOM):
2231 | +                m.embed("oom")
2232 | +            with self.assertRaises(ValueError):
2233 | +                m.embed("x")
2234 | +
2235 | +
2236 | +class TestPeaks(Box):
2237 | +    def test_the_peak_per_label(self):
2238 | +        s = gpu0.PeakSampler(interval_s=3600)
2239 | +        s.set("pinned")
2240 | +        self.used[0] = 5000
2241 | +        s._sample()
2242 | +        self.used[0] = 300
2243 | +        s.set("render")
2244 | +        s.set(None)
2245 | +        self.used[0] = 9999                              # outside any stage: attributed to none
2246 | +        s._sample()
2247 | +        self.assertEqual(s.peaks, {"pinned": 5000, "render": 300})
2248 | +
2249 | +
2250 | +class TestStageRunner(Box):
2251 | +    """run_fresh.Run._attempts: one bounded retry of an out-of-memory, both attempts in PROVENANCE, a second one a
2252 | +    HOLD naming every GPU0 process; every other GPU0 stop a HOLD with its real cause."""
2253 | +
2254 | +    def run_(self):
2255 | +        import run_fresh as rf
2256 | +        d = tempfile.mkdtemp(dir=self.tmp)
2257 | +        return rf, rf.Run(d)
2258 | +
2259 | +    def test_one_retry_then_success(self):
2260 | +        rf, run = self.run_()
2261 | +        calls = []
2262 | +
2263 | +        def stage():
2264 | +            calls.append(1)
2265 | +            if len(calls) == 1:
2266 | +                raise gpu0.GpuOOM("whisper:large-v3: transcribe: CUDA out of memory")
2267 | +            return "ok"
2268 | +        with mock.patch.object(gpu0, "release_all", return_value={"after": [18, 24564]}) as rel:
2269 | +            self.assertEqual(run.stage("pinned", stage), "ok")
2270 | +        self.assertEqual((len(calls), rel.call_count), (2, 1))
2271 | +        log = run.prov["gpu0_oom"]["pinned"]
2272 | +        self.assertEqual((len(log), log[0]["attempt"], log[0]["release"]), (2, 1, {"after": [18, 24564]}))
2273 | +        self.assertEqual((log[1]["attempt"], log[1]["outcome"]), (2, "passed"))      # both attempts logged
2274 | +
2275 | +    def test_a_second_out_of_memory_is_a_hold_naming_every_process(self):
2276 | +        rf, run = self.run_()
2277 | +        self.procs[:] = [(31337, "python3", 23000)]
2278 | +
2279 | +        def stage():
2280 | +            raise RuntimeError("CUDA failed with error out of memory")   # raw: recognised by the runner too
2281 | +        with mock.patch.object(gpu0, "release_all", return_value={}):
2282 | +            with self.assertRaises(rf.Hold) as cm:
2283 | +                run.stage("gates", stage)
2284 | +        msg = str(cm.exception)
2285 | +        self.assertTrue(msg.startswith("infrastructure: gates: CUDA out of memory twice"), msg)
2286 | +        self.assertIn("pid 31337 python3 23000 MiB", msg)
2287 | +        self.assertEqual(len(run.prov["gpu0_oom"]["gates"]), 2)
2288 | +
2289 | +    def test_a_failed_retry_keeps_the_out_of_memory_in_the_hold(self):
2290 | +        rf, run = self.run_()
2291 | +        n = []
2292 | +
2293 | +        def stage():
2294 | +            n.append(1)
2295 | +            if len(n) == 1:
2296 | +                raise gpu0.GpuOOM("whisper:medium: transcribe: CUDA out of memory")
2297 | +            raise rf.Hold("cut acceptance failed")
2298 | +        with mock.patch.object(gpu0, "release_all", return_value={}):
2299 | +            with self.assertRaises(rf.Hold) as cm:
2300 | +                run.stage("gates", stage)
2301 | +        msg = str(cm.exception)
2302 | +        self.assertTrue(msg.startswith("infrastructure: gates: CUDA out of memory on attempt 1"), msg)
2303 | +        self.assertIn("the retry then held: cut acceptance failed", msg)
2304 | +
2305 | +    def test_other_stops_hold_with_the_real_cause_and_ordinary_errors_are_not_retried(self):
2306 | +        rf, run = self.run_()
2307 | +        with self.assertRaisesRegex(rf.Hold, r"^infrastructure: render: GPU0 Gpu0Foreign: .*pid 7"):
2308 | +            run.stage("render", lambda: (_ for _ in ()).throw(gpu0.Gpu0Foreign("held by pid 7 x 1 MiB")))
2309 | +        n = []
2310 | +        with self.assertRaisesRegex(rf.Hold, "ValueError: no"):
2311 | +            run.stage("cut", lambda: n.append(1) or (_ for _ in ()).throw(ValueError("no")))
2312 | +        self.assertEqual(n, [1])
2313 | +
2314 | +    def test_e_fail_052_the_pinned_out_of_memory_is_reported_as_one(self):
2315 | +        """Nov 12: Whisper's out-of-memory in the pinned stage read 'pinned decision rejected: R-iKNbc7-zk:
2316 | +        transcription failed'. Now it reaches the HOLD as the out-of-memory it is (after one retry)."""
2317 | +        rf, run = self.run_()
2318 | +        import pinned
2319 | +        import select_passages as sp
2320 | +
2321 | +        class OOMWhisper:                                # what gpu0.whisper's guard makes of a CTranslate2 OOM
2322 | +            def transcribe(self, *a, **k):
2323 | +                with gpu0.guard("whisper:large-v3: transcribe"):
2324 | +                    raise RuntimeError("CUDA failed with error out of memory")
2325 | +        src = os.path.join(self.tmp, "src.mp4")
2326 | +        open(src, "wb").write(b"x")
2327 | +        seg = {"role": "hook", "video_id": "R-iKNbc7-zk", "start": 18.16, "end": 26.4, "source": {"kind": "youtube"}}
2328 | +        with mock.patch.object(sp, "_download_window", return_value=(src, 0.0)), \
2329 | +                mock.patch.object(gpu0, "whisper", return_value=OOMWhisper()), \
2330 | +                mock.patch.object(gpu0, "release_all", return_value={}):
2331 | +            with self.assertRaises(rf.Hold) as cm:
2332 | +                run.stage("pinned", lambda: pinned.acquire({"segments": [seg]}, run.dir, log=lambda s: None))
2333 | +        msg = str(cm.exception)
2334 | +        self.assertTrue(msg.startswith("infrastructure: pinned: CUDA out of memory twice"), msg)
2335 | +        self.assertNotIn("transcription failed", msg)
2336 | +        self.assertNotIn("pinned decision rejected", msg)
2337 | +
2338 | +
2339 | +class TestReadingsFailClosed(unittest.TestCase):
2340 | +    """The real parsers (no stubs of their own): a reading that cannot be read is a stop, never 'nothing there'."""
2341 | +
2342 | +    def test_an_unparsable_nvidia_smi_line_is_unreadable_and_other_gpus_are_ignored(self):
2343 | +        def smi(args, timeout=15):
2344 | +            if "--query-gpu=uuid" in args:
2345 | +                return "GPU-A\n"
2346 | +            return "123, GPU-A, 500, /usr/bin/python3\n456, GPU-B, 900, ollama\n" + smi.extra
2347 | +        smi.extra = ""
2348 | +        with mock.patch.object(gpu0, "_smi", side_effect=smi):
2349 | +            self.assertEqual(gpu0.processes(), [(123, "python3", 500)])
2350 | +            smi.extra = "[Not Supported]\n"
2351 | +            with self.assertRaises(gpu0.Gpu0Unreadable):
2352 | +                gpu0.processes()
2353 | +
2354 | +    def test_ss_failing_or_hiding_the_listener_pid_is_unreadable(self):
2355 | +        with mock.patch.object(gpu0.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "boom")):
2356 | +            with self.assertRaises(gpu0.Gpu0Unreadable):
2357 | +                gpu0._ollama_pids()
2358 | +        hidden = subprocess.CompletedProcess([], 0, "LISTEN 0 4096 127.0.0.1:11434 0.0.0.0:*\n", "")
2359 | +        with mock.patch.object(gpu0.subprocess, "run", return_value=hidden):
2360 | +            with self.assertRaisesRegex(gpu0.Gpu0Unreadable, "not visible to this user"):
2361 | +                gpu0._ollama_pids()
2362 | +
2363 | +
2364 | +class TestNoDirectLoaders(unittest.TestCase):
2365 | +    """L-r item 2 by construction: in the code a run imports, nothing builds a GPU0 model, moves a tensor to CUDA or calls
2366 | +    the GPU0 Ollama except through gpu0, and every function that encodes with NVENC swaps to it first."""
2367 | +    import glob as _g
2368 | +    FILES = sorted(f for f in _g.glob(os.path.join(PIPELINE, "*.py"))
2369 | +                   if not os.path.basename(f).startswith("test_")
2370 | +                   and os.path.basename(f) not in ("conftest.py", "gpu0.py", "measure_gpu0.py")) + \
2371 | +        [os.path.join(os.path.dirname(PIPELINE), "segment_v1", "qa_gates.py")]
2372 | +
2373 | +    def test_no_model_is_built_outside_gpu0(self):
2374 | +        import re
2375 | +        pats = [r"WhisperModel\(", r"BatchedInferencePipeline\(", r"VoiceEncoder\(\)", r"\.to\(['\"]cuda", r"device=['\"]cuda",
2376 | +                r"\.cuda\(\)"]
2377 | +        allowed = {("story_semantics.py", r"\.to\(['\"]cuda")}     # the Embedder: inside gpu0.model's build and guard
2378 | +        bad = []
2379 | +        for f in self.FILES:
2380 | +            src = open(f).read()
2381 | +            for pat in pats:
2382 | +                if (os.path.basename(f), pat) in allowed:
2383 | +                    continue
2384 | +                for m in re.finditer(pat, src):
2385 | +                    line = src.count("\n", 0, m.start()) + 1
2386 | +                    if not src.splitlines()[line - 1].lstrip().startswith("#"):
2387 | +                        bad.append(f"{os.path.relpath(f, PIPELINE)}:{line}: {pat}")
2388 | +        self.assertEqual(bad, [])
2389 | +
2390 | +    def test_every_nvenc_function_swaps_to_nvenc_first(self):
2391 | +        import ast
2392 | +        bad = []
2393 | +        for f in self.FILES:
2394 | +            src = open(f).read()
2395 | +            for fn in ast.parse(src).body:
2396 | +                if isinstance(fn, ast.FunctionDef):
2397 | +                    seg = ast.get_source_segment(src, fn)
2398 | +                    if "h264_nvenc" in seg and 'gpu0.swap_to("nvenc")' not in seg:
2399 | +                        bad.append(f"{os.path.relpath(f, PIPELINE)}: {fn.name}")
2400 | +        self.assertEqual(bad, [])
2401 | +
2402 | +    def test_the_gpu0_ollama_is_called_only_through_gpu0(self):
2403 | +        bad = [os.path.basename(f) for f in self.FILES if ("/api/generate" in open(f).read() or "/api/chat" in
2404 | +               open(f).read()) and os.path.basename(f) not in ("story_semantics.py", "preflight.py")]
2405 | +        self.assertEqual(bad, [])
2406 | +
2407 | +
2408 | +class TestPreflightLeavesGpu0AsFound(Box):
2409 | +    def test_a_model_left_resident_or_memory_left_used_fails(self):
2410 | +        import preflight
2411 | +        self.assertTrue(preflight.left_as_found(100, [], wait_s=0)[0])
2412 | +        self.ollama[:] = ["gemma3:27b"]
2413 | +        ok, why = preflight.left_as_found(100, [], wait_s=0)
2414 | +        self.assertFalse(ok)
2415 | +        self.assertIn("gemma3:27b", why)
2416 | +        self.ollama[:] = []
2417 | +        self.used[0] = 20659
2418 | +        ok, why = preflight.left_as_found(100, [], wait_s=0)
2419 | +        self.assertEqual((ok, "left GPU0 at 20659 MiB (found at 100 MiB)" in why), (False, True))
2420 | +
2421 | +
2422 | +if __name__ == "__main__":
2423 | +    unittest.main()
2424 | diff --git a/pipeline/test_gpu0_live.py b/pipeline/test_gpu0_live.py
2425 | new file mode 100644
2426 | index 00000000..13413205
2427 | --- /dev/null
2428 | +++ b/pipeline/test_gpu0_live.py
2429 | @@ -0,0 +1,216 @@
2430 | +#!/usr/bin/env python3
2431 | +"""Law L-r item 5 on the real GPU0 (a GPU session: CUDA_VISIBLE_DEVICES=0; pipeline/conftest.py holds the GPU0 lease
2432 | +for the session). Before each stage a real allocation sits on GPU0, and the stage refuses or recovers as the law says:
2433 | +  - a FOREIGN allocation (a process that is not this run's) -> every stage kind HOLDs at once, naming its pid and MiB;
2434 | +  - this run's OWN resident model -> the next stage's swap deletes it and the stage passes;
2435 | +  - a real CUDA out-of-memory -> released, retried ONCE, both attempts in PROVENANCE; a second one HOLDs naming every
2436 | +    GPU0 process.
2437 | +TestBackToBack (PP_GPU0_LIVE=1, ~2 x 50 min, a committed clean tree): run_fresh env -> pinned -> ... -> render ->
2438 | +gates twice back to back on the protected preview's PIN, printing both runs' per-stage GPU0 peak tables."""
2439 | +import json
2440 | +import os
2441 | +import re
2442 | +import signal
2443 | +import subprocess
2444 | +import sys
2445 | +import tempfile
2446 | +import time
2447 | +import unittest
2448 | +
2449 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
2450 | +REPO = os.path.dirname(PIPELINE)
2451 | +sys.path.insert(0, PIPELINE)
2452 | +import gpu0  # noqa: E402
2453 | +
2454 | +GPU = os.environ.get("CUDA_VISIBLE_DEVICES") == "0"
2455 | +SOURCE = os.path.join(REPO, "references", "pulse_preview_2026-11-11", "sources", "RXTVaDsN11M.mp4")
2456 | +
2457 | +
2458 | +def _wav(tmp, seconds=20):
2459 | +    wav = os.path.join(tmp, "a.wav")
2460 | +    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "30", "-t", str(seconds), "-i", SOURCE, "-vn", "-ac", "1",
2461 | +                    "-ar", "16000", wav], check=True, timeout=120)
2462 | +    return wav
2463 | +
2464 | +
2465 | +@unittest.skipUnless(GPU, "GPU0 session only (CUDA_VISIBLE_DEVICES=0)")
2466 | +class Live(unittest.TestCase):
2467 | +    def setUp(self):
2468 | +        self.assertTrue(gpu0.held(), "the session must hold the GPU0 lease (pipeline/conftest.py)")
2469 | +        gpu0.release_all()
2470 | +        self.tmp = tempfile.mkdtemp(prefix="gpu0live_")
2471 | +        self.wav = _wav(self.tmp)
2472 | +        import run_fresh as rf
2473 | +        self.rf = rf
2474 | +        self.run_ = rf.Run(self.tmp)
2475 | +        self.run_.sampler = gpu0.PeakSampler(interval_s=0.25).start()
2476 | +        self.addCleanup(self.run_.sampler.stop)
2477 | +        self.addCleanup(gpu0.release_all)
2478 | +
2479 | +    def transcribe(self, name):
2480 | +        segs, _ = gpu0.whisper(name).transcribe(self.wav, language="en", beam_size=5, word_timestamps=True,
2481 | +                                                vad_filter=False)
2482 | +        return sum(len(s.words or []) for s in segs)
2483 | +
2484 | +
2485 | +class TestForeignAllocationIsRefused(Live):
2486 | +    def test_every_stage_kind_holds_naming_the_foreign_process(self):
2487 | +        flag = os.path.join(self.tmp, "allocated")
2488 | +        code = ("import torch, time; x = torch.empty(int(2e9), dtype=torch.uint8, device='cuda:0'); "
2489 | +                f"open({flag!r}, 'w').write('ok'); time.sleep(900)")
2490 | +        # double fork: the allocator is NOT this process's descendant (a foreign job), and holds no lease descriptor
2491 | +        out = subprocess.run(["setsid", "bash", "-c", f"{sys.executable} -c \"{code}\" >/dev/null 2>&1 & echo $!"],
2492 | +                             capture_output=True, text=True, timeout=30, env={**os.environ, "CUDA_VISIBLE_DEVICES": "0"})
2493 | +        pid = int(out.stdout.strip())
2494 | +
2495 | +        def stop_allocator():                                         # we started it: stop it and wait until it is gone
2496 | +            if os.path.exists(f"/proc/{pid}"):
2497 | +                os.kill(pid, signal.SIGTERM)
2498 | +            for _ in range(120):
2499 | +                if not os.path.exists(f"/proc/{pid}") and all(p != pid for p, n, m in gpu0.processes()):
2500 | +                    return
2501 | +                time.sleep(0.5)
2502 | +        self.addCleanup(stop_allocator)
2503 | +        for _ in range(120):
2504 | +            if os.path.exists(flag) and any(p == pid for p, n, m in gpu0.processes()):
2505 | +                break
2506 | +            time.sleep(0.5)
2507 | +        else:
2508 | +            self.fail("the foreign allocation never appeared on GPU0")
2509 | +        stages = {"pinned": lambda: self.transcribe("large-v3"),
2510 | +                  "review": lambda: gpu0.swap_to("ollama:gemma3:27b"),
2511 | +                  "render": lambda: gpu0.swap_to("nvenc"),
2512 | +                  "gates": lambda: self.transcribe("medium")}
2513 | +        for name, fn in stages.items():
2514 | +            with self.assertRaises(self.rf.Hold, msg=name) as cm:
2515 | +                self.run_.stage(name, fn)
2516 | +            msg = str(cm.exception)
2517 | +            self.assertTrue(msg.startswith(f"infrastructure: {name}: GPU0 Gpu0Foreign"), msg)
2518 | +            self.assertIn(f"pid {pid} ", msg)
2519 | +        self.assertFalse(gpu0.whisper("large-v3").loaded)              # nothing was loaded next to it
2520 | +
2521 | +
2522 | +class TestOwnResidentModelIsSwappedOut(Live):
2523 | +    def test_the_next_stage_deletes_it_and_passes(self):
2524 | +        import story_semantics as sm
2525 | +        E = sm.Embedder()
2526 | +        E.encode(["bitcoin " * 200] * 16)                              # resident on GPU0 before the stage
2527 | +        self.assertTrue(E.model.loaded)
2528 | +        n = self.run_.stage("pinned", lambda: self.transcribe("large-v3"))
2529 | +        self.assertGreater(n, 10)
2530 | +        self.assertFalse(E.model.loaded)                               # deleted by the swap
2531 | +        ev = [e for e in gpu0.events() if e["key"] == "whisper:large-v3"][-1]
2532 | +        self.assertIn("embedder", ev["unloaded"])
2533 | +        print(f"\n  peaks MiB: {self.run_.sampler.peaks}")
2534 | +
2535 | +
2536 | +class TestRealOutOfMemory(Live):
2537 | +    def test_an_oom_caused_by_a_resident_model_is_recovered_by_releasing_it(self):
2538 | +        """Load-bearing: the out-of-memory happens BECAUSE Whisper medium is resident and referenced from the failing
2539 | +        frame; the retry can succeed only if the release really frees that model (traceback dropped, object deleted,
2540 | +        nvidia-smi showing the room). With the model pinned, release_all times out and the stage HOLDs."""
2541 | +        import torch
2542 | +        state = {}
2543 | +
2544 | +        def stage():
2545 | +            state["n"] = state.get("n", 0) + 1
2546 | +            if state["n"] == 1:
2547 | +                m = gpu0.whisper("medium")
2548 | +                obj = m.get()                                          # resident, referenced from this frame
2549 | +                used, total = gpu0.memory()
2550 | +                state["mib"] = total - used + 1024                     # 1 GiB more than is free with it loaded
2551 | +                with gpu0.guard("allocation next to a resident model"):
2552 | +                    torch.empty(state["mib"] * 1024 * 1024, dtype=torch.uint8, device="cuda:0")
2553 | +                return obj                                             # never reached
2554 | +            x = torch.empty(state["mib"] * 1024 * 1024, dtype=torch.uint8, device="cuda:0")   # fits once it is gone
2555 | +            del x
2556 | +            return self.transcribe("medium")
2557 | +        self.assertGreater(self.run_.stage("gates", stage), 10)
2558 | +        log = self.run_.prov["gpu0_oom"]["gates"]
2559 | +        self.assertEqual((state["n"], len(log), log[1]["outcome"]), (2, 2, "passed"))
2560 | +        self.assertIn("out of memory", log[0]["error"].lower())
2561 | +        self.assertIn("whisper:medium", log[0]["release"]["unloaded"])
2562 | +
2563 | +    def test_two_out_of_memory_attempts_hold_naming_every_gpu0_process(self):
2564 | +        import torch
2565 | +
2566 | +        def always():
2567 | +            with gpu0.guard("dummy allocation"):
2568 | +                torch.empty(int(40e9), dtype=torch.uint8, device="cuda:0")
2569 | +        with self.assertRaises(self.rf.Hold) as cm:
2570 | +            self.run_.stage("render", always)
2571 | +        msg = str(cm.exception)
2572 | +        self.assertTrue(msg.startswith("infrastructure: render: CUDA out of memory twice"), msg)
2573 | +        self.assertIn(f"pid {os.getpid()} ", msg)                     # every GPU0 process named (here: this one)
2574 | +        self.assertEqual(len(self.run_.prov["gpu0_oom"]["render"]), 2)
2575 | +
2576 | +
2577 | +class TestTheNov12Incident(Live):
2578 | +    """runs/pinned_20261112_064032: gemma3:27b resident on GPU0, then Whisper. Replayed both ways."""
2579 | +
2580 | +    def test_this_runs_editorial_model_is_swapped_out_before_whisper(self):
2581 | +        import story_semantics as sm
2582 | +        llm = sm.LocalLLM()
2583 | +        llm._post("Reply with the JSON object {\"ok\": true}.", 20, seed=7)    # gemma3:27b resident (this run's)
2584 | +        self.assertIn(sm.LLM_MODEL, gpu0.ollama_loaded())
2585 | +        n = self.run_.stage("pinned", lambda: self.transcribe("large-v3"))
2586 | +        self.assertGreater(n, 10)
2587 | +        self.assertNotIn(sm.LLM_MODEL, gpu0.ollama_loaded())
2588 | +        print(f"\n  peaks MiB: {self.run_.sampler.peaks}")
2589 | +
2590 | +    def test_a_model_another_client_loaded_holds_the_run_and_is_not_touched(self):
2591 | +        import json as _j
2592 | +        import urllib.request
2593 | +        import story_semantics as sm
2594 | +        body = _j.dumps({"model": sm.LLM_MODEL, "prompt": "ok", "stream": False, "options": {"num_predict": 1}}).encode()
2595 | +        urllib.request.urlopen(urllib.request.Request(f"http://{gpu0.OLLAMA_HOST}/api/generate", data=body,
2596 | +                               headers={"Content-Type": "application/json"}), timeout=300).read()   # another client
2597 | +        def unload_it():                                              # this test loaded it as 'another client'
2598 | +            urllib.request.urlopen(urllib.request.Request(
2599 | +                f"http://{gpu0.OLLAMA_HOST}/api/generate", data=_j.dumps({"model": sm.LLM_MODEL, "keep_alive": 0}).encode(),
2600 | +                headers={"Content-Type": "application/json"}), timeout=120).read()
2601 | +            for _ in range(120):
2602 | +                if sm.LLM_MODEL not in gpu0.ollama_loaded():
2603 | +                    return
2604 | +                time.sleep(0.5)
2605 | +        self.addCleanup(unload_it)
2606 | +        with self.assertRaises(self.rf.Hold) as cm:
2607 | +            self.run_.stage("pinned", lambda: self.transcribe("large-v3"))
2608 | +        msg = str(cm.exception)
2609 | +        self.assertIn(f"ollama model {sm.LLM_MODEL} (not requested by this run)", msg)
2610 | +        self.assertIn(sm.LLM_MODEL, gpu0.ollama_loaded())             # nothing of it was unloaded
2611 | +
2612 | +
2613 | +# the PBX-approved preview of Nov 11 (law L-d): local sources, every stage through render, gates and verify
2614 | +PIN = os.path.join(REPO, "references", "pulse_preview_2026-11-11", "PIN.json")
2615 | +
2616 | +
2617 | +@unittest.skipUnless(GPU and os.environ.get("PP_GPU0_LIVE") == "1", "PP_GPU0_LIVE=1: two full runs (~2 x 50 min)")
2618 | +class TestBackToBack(unittest.TestCase):
2619 | +    def test_two_runs_back_to_back_with_the_peak_table(self):
2620 | +        """Two full runs of the protected preview's PIN back to back, nothing released between them: the second must
2621 | +        find GPU0 as the first left it (its env stage refuses anything foreign), every stage must run and be sampled,
2622 | +        and no stage may hold for a GPU0 cause."""
2623 | +        fd = gpu0._own[gpu0.lease_path()]["file"].fileno()        # the session's lease: run_fresh inherits custody
2624 | +        os.set_inheritable(fd, True)
2625 | +        want = ["env", "pinned", "review", "validate", "cut", "sentence_law", "voice", "prepare", "layout", "render",
2626 | +                "gates", "verify"]
2627 | +        tables = []
2628 | +        for i in (1, 2):
2629 | +            r = subprocess.run([sys.executable, os.path.join(PIPELINE, "run_fresh.py"), "--pinned", PIN],
2630 | +                               capture_output=True, text=True, timeout=4 * 3600, pass_fds=(fd,), cwd=PIPELINE)
2631 | +            run_dir = re.search(r"=== FRESH-TOPIC RUN (\S+) ===", r.stdout).group(1)
2632 | +            report = open(os.path.join(run_dir, "REPORT.md")).read()
2633 | +            table = report[report.index("## GPU0 peak memory per stage"):].split("\n\n")[0]
2634 | +            tables.append((run_dir, r.returncode, table))
2635 | +            stages = {st["name"]: st for st in json.load(open(os.path.join(run_dir, "status.json")))["stages"]}
2636 | +            self.assertEqual([n for n in want if n not in stages], [], run_dir)
2637 | +            for n in want:
2638 | +                st = stages[n]
2639 | +                self.assertEqual(st["status"], "passed", (run_dir, n, st.get("reason")))
2640 | +                self.assertIsInstance(st.get("gpu0_peak_mib"), int, (run_dir, n))
2641 | +        for run_dir, rc, table in tables:
2642 | +            print(f"\n{run_dir} (exit {rc})\n{table}")
2643 | +
2644 | +if __name__ == "__main__":
2645 | +    unittest.main()
2646 | diff --git a/pipeline/conftest.py b/pipeline/conftest.py
2647 | new file mode 100644
2648 | index 00000000..34881961
2649 | --- /dev/null
2650 | +++ b/pipeline/conftest.py
2651 | @@ -0,0 +1,65 @@
2652 | +"""pytest and GPU0 (law L-r ONE OWNER, pipeline/gpu0.py). Decided once, before collection:
2653 | +  unset, '' or '-1'                a CPU session: takes nothing, hides every GPU (CUDA_VISIBLE_DEVICES=''); a GPU0 load in
2654 | +                                   it is refused (gpu0.require), and a CUDA context of it on GPU0 stops the session
2655 | +  '0'                              a GPU session, GPU0 only: holds the GPU0 lease for the whole session, or stops at
2656 | +                                   once with exit 75 naming the holder (a run or another session has GPU0)
2657 | +  anything else ('0,1', '1', ...)  refused (exit 2): GPU1 is quarantined"""
2658 | +import os
2659 | +import sys
2660 | +
2661 | +import pytest
2662 | +
2663 | +sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # gpu0 lives next to this file
2664 | +
2665 | +_CVD = os.environ.get("CUDA_VISIBLE_DEVICES")
2666 | +_CPU = _CVD in (None, "", "-1")
2667 | +_LEASE = []
2668 | +if _CPU:
2669 | +    import tempfile
2670 | +    os.environ["CUDA_VISIBLE_DEVICES"] = ""            # unset would show every GPU to the libraries: hide them all
2671 | +    # and a private lease file: code under test that enters gpu0.lease() (preflight.main, replay) never takes or blocks
2672 | +    # the production GPU0 lease from a CPU session (Nov 12: test_preflight briefly held /tmp/pulse_gpu0.lease)
2673 | +    os.environ["PP_GPU0_LEASE"] = os.path.join(tempfile.mkdtemp(prefix="pp_cpu_session_"), "gpu0.lease")
2674 | +
2675 | +
2676 | +def pytest_configure(config):
2677 | +    if _CPU:
2678 | +        return
2679 | +    if _CVD != "0":
2680 | +        pytest.exit(f"CUDA_VISIBLE_DEVICES={_CVD!r}: test sessions run on GPU0 only ('0', or '' for CPU)", returncode=2)
2681 | +    import gpu0
2682 | +    cm = gpu0.lease(f"pytest session (pid {os.getpid()})")
2683 | +    try:
2684 | +        cm.__enter__()
2685 | +    except gpu0.LeaseBusy as e:
2686 | +        pytest.exit(f"GPU0 is busy, no GPU test session now: {e}", returncode=75)
2687 | +    _LEASE.append(cm)
2688 | +
2689 | +
2690 | +def pytest_unconfigure(config):
2691 | +    while _LEASE:
2692 | +        _LEASE.pop().__exit__(None, None, None)
2693 | +
2694 | +
2695 | +def _holds_gpu0_context(pid):
2696 | +    import subprocess
2697 | +    try:
2698 | +        uuid = subprocess.run(["nvidia-smi", "-i", "0", "--query-gpu=uuid", "--format=csv,noheader"],
2699 | +                              capture_output=True, text=True, timeout=15).stdout.strip()
2700 | +        apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid", "--format=csv,noheader"],
2701 | +                              capture_output=True, text=True, timeout=15).stdout
2702 | +    except (OSError, subprocess.TimeoutExpired):
2703 | +        return False
2704 | +    return any([x.strip() for x in line.split(",")][:2] == [str(pid), uuid] for line in apps.splitlines() if uuid)
2705 | +
2706 | +
2707 | +def pytest_runtest_teardown(item, nextitem):
2708 | +    """L-r: a CPU session never touches GPU0. After each test module, a CUDA context of this process on GPU0 stops the
2709 | +    session at once, naming the module (on Nov 12 render16's import forced CUDA_VISIBLE_DEVICES=0 into a CPU session,
2710 | +    which then held 394 MiB on GPU0 without the lease)."""
2711 | +    if not _CPU or (nextitem is not None and nextitem.module is item.module):
2712 | +        return
2713 | +    if _holds_gpu0_context(os.getpid()):
2714 | +        pytest.exit(f"law L-r: this CPU test session holds a CUDA context on GPU0 after {item.module.__name__} "
2715 | +                    f"(last test {item.nodeid}, CUDA_VISIBLE_DEVICES now {os.environ.get('CUDA_VISIBLE_DEVICES')!r})",
2716 | +                    returncode=3)
2717 | diff --git a/pipeline/measure_gpu0.py b/pipeline/measure_gpu0.py
2718 | new file mode 100644
2719 | index 00000000..9d09ad6c
2720 | --- /dev/null
2721 | +++ b/pipeline/measure_gpu0.py
2722 | @@ -0,0 +1,107 @@
2723 | +#!/usr/bin/env python3
2724 | +"""pipeline/measure_gpu0.py — measure the peak GPU0 memory each gpu0.REQUIREMENT_MIB key needs (law L-r item 2:
2725 | +'the incoming model's known requirement'). Holds the GPU0 lease for the whole measurement; runs one child process per
2726 | +key (it inherits the lease descriptor and loads through gpu0, as the pipeline does) on a representative workload while
2727 | +this process samples nvidia-smi every 0.1 s. Prints the peak above the idle baseline per key; changes nothing.
2728 | +Usage: CUDA_VISIBLE_DEVICES=0 [MEASURE_SECONDS=600] python3 pipeline/measure_gpu0.py [key ...]"""
2729 | +import json
2730 | +import os
2731 | +import subprocess
2732 | +import sys
2733 | +import tempfile
2734 | +import threading
2735 | +import time
2736 | +
2737 | +PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
2738 | +REPO = os.path.dirname(PIPELINE_DIR)
2739 | +sys.path.insert(0, PIPELINE_DIR)
2740 | +import gpu0  # noqa: E402
2741 | +
2742 | +SOURCE = os.environ.get("MEASURE_SOURCE") or os.path.join(REPO, "references", "pulse_preview_2026-11-11", "sources",
2743 | +                                                       "jbDqdLytkNM.mp4")     # 733 s of speech (protected, read-only)
2744 | +
2745 | +CHILD = r'''
2746 | +import os, sys, json, urllib.request
2747 | +sys.path.insert(0, sys.argv[1])
2748 | +import gpu0
2749 | +key, wav = sys.argv[2], sys.argv[3]
2750 | +if key.startswith("whisper:"):
2751 | +    parts = key.split(":")
2752 | +    m = gpu0.whisper(parts[1], batched=len(parts) > 2)
2753 | +    kw = {"language": "en", "word_timestamps": True}
2754 | +    kw.update({"batch_size": 16} if len(parts) > 2 else {"beam_size": 5, "vad_filter": False})
2755 | +    segs, _ = m.transcribe(wav, **kw)
2756 | +    n = sum(len(s.words or []) for s in segs)
2757 | +    print(json.dumps({"words": n}))
2758 | +elif key == "embedder":
2759 | +    import story_semantics as sm
2760 | +    e = sm.Embedder()                                   # its model loads through gpu0.model('embedder')
2761 | +    v = e.encode([("bitcoin price support moving average " * 60)] * 64)
2762 | +    print(json.dumps({"vectors": len(v)}))
2763 | +elif key == "resemblyzer":
2764 | +    from resemblyzer import VoiceEncoder, preprocess_wav
2765 | +    enc = gpu0.model("resemblyzer", VoiceEncoder)          # as qa_gates' G1 loads it
2766 | +    print(json.dumps({"dims": len(enc.embed_utterance(preprocess_wav(wav)))}))
2767 | +elif key == "nvenc":
2768 | +    gpu0.swap_to("nvenc")
2769 | +    import subprocess
2770 | +    for size in ("1920x1080", "1080x1920"):
2771 | +        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=30", "-t", "8",
2772 | +                        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18", "-f", "null", "-"],
2773 | +                       check=True, timeout=300)
2774 | +    print(json.dumps({"encoded": 2}))
2775 | +elif key.startswith("ollama:"):
2776 | +    import story_semantics as sm
2777 | +    llm = sm.LocalLLM(model=key.split(":", 1)[1])          # as the editorial stages ask it (swap_to inside _post)
2778 | +    out = llm._post("Reply with a JSON object about Bitcoin's 200-day average in 150 words.", 200, seed=7)
2779 | +    llm.stop()
2780 | +    print(json.dumps({"chars": len(out)}))
2781 | +'''
2782 | +
2783 | +
2784 | +def main():
2785 | +    keys = sys.argv[1:] or list(gpu0.REQUIREMENT_MIB)
2786 | +    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
2787 | +        sys.exit("CUDA_VISIBLE_DEVICES must be 0")
2788 | +    with gpu0.lease("measure_gpu0 (L-r requirements)"), tempfile.TemporaryDirectory(prefix="gpu0m_") as tmp:
2789 | +        lease_fd = gpu0._own[gpu0.lease_path()]["file"].fileno()
2790 | +        os.set_inheritable(lease_fd, True)
2791 | +        wav = os.path.join(tmp, "a.wav")
2792 | +        secs = os.environ.get("MEASURE_SECONDS", "600")    # >= 480 s fills a batched 16 x 30 s window
2793 | +        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "60", "-t", secs, "-i", SOURCE, "-vn", "-ac", "1",
2794 | +                        "-ar", "16000", wav], check=True, timeout=120)
2795 | +        rows = []
2796 | +        for key in keys:
2797 | +            gpu0.release_all()
2798 | +            base, total = gpu0.memory()
2799 | +            peak = [base]
2800 | +            stop = threading.Event()
2801 | +
2802 | +            def sample():
2803 | +                while not stop.wait(0.1):
2804 | +                    try:
2805 | +                        peak[0] = max(peak[0], gpu0.memory()[0])
2806 | +                    except gpu0.Gpu0Stop:
2807 | +                        pass
2808 | +            t = threading.Thread(target=sample, daemon=True)
2809 | +            t.start()
2810 | +            t0 = time.time()
2811 | +            r = subprocess.run([sys.executable, "-c", CHILD, PIPELINE_DIR, key, wav], capture_output=True, text=True,
2812 | +                               timeout=1800, pass_fds=(lease_fd,))
2813 | +            stop.set()
2814 | +            t.join()
2815 | +            rows.append({"key": key, "baseline_mib": base, "peak_mib": peak[0], "need_mib": peak[0] - base,
2816 | +                         "seconds": round(time.time() - t0, 1), "rc": r.returncode,
2817 | +                         "out": (r.stdout.strip().splitlines() or [""])[-1][:120],
2818 | +                         "err": "" if r.returncode == 0 else r.stderr.strip()[-300:]})
2819 | +            print(json.dumps(rows[-1]), flush=True)
2820 | +        gpu0.release_all()
2821 | +        print("\n| key | baseline MiB | peak MiB | need MiB | s | rc |\n|---|---|---|---|---|---|")
2822 | +        for x in rows:
2823 | +            print(f"| {x['key']} | {x['baseline_mib']} | {x['peak_mib']} | {x['need_mib']} | {x['seconds']} | {x['rc']} |")
2824 | +        if any(x["rc"] != 0 for x in rows):
2825 | +            sys.exit(f"measure_gpu0: {sum(x['rc'] != 0 for x in rows)} key(s) failed; their peaks are not requirements")
2826 | +
2827 | +
2828 | +if __name__ == "__main__":
2829 | +    main()
2830 | 
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

