# Batch 6 (orchestrator 08:30: replay harness, stand-alone + topic rule, decimal canonicaliser, shot snap, Telegram only on a pass) — dispositions

Audited: the staged diff (pipeline/ + scripts/). Cross-LLM GPT-4o + Gemini (Grok blocked by the xAI ceiling);
Heimdall deepseek + qwen27b, one chunk per file (11 chunks).

## Implemented
- Heimdall test_stand_alone [high, consensus]: for a non-Bitcoin story (Nov 4's Binance hack) the subject
  terms also counted Bitcoin, so a Bitcoin aside would pass as a clip of that story. Now: a Bitcoin story's
  subject is Bitcoin/BTC; any other story's subject is its own words only (no words at all: Bitcoin/BTC).
  Test: "Bitcoin is sitting at 77,000 today." fails topic in the Binance story.
- Heimdall replay.py [high, consensus]: a non-Hold exception ended the replay with a traceback instead of a
  verdict (the claimed KeyError cannot happen: Run initialises verdict=None, but the replay would exit 1 with
  VERDICT "None"). Now, like run_fresh.main, anything unexpected is a HOLD with its reason. One-vote item
  also done: sources/ entries that are not files are copied, not hard-linked.
- Heimdall test_shot_snap [medium, consensus]: the test proved the frames were uniform, not that the held
  shot is the speaker's; it now also checks the held luma equals the speaker's (red) shot. One-vote items
  also done: audio start/duration, frame rate and duration are compared before/after the snap.
- Heimdall editorial_select [low, consensus]: the "no hook passage scored >= 4.0" reason was wrong when hooks
  scored but failed the stand-alone/topic rule; the reason now says which.

## Rejected, with evidence
- Cross-LLM U1/U2/P1/P2/P4 "D1 onset clipping and D4 avatar warping not addressed": scope misreading of the
  audit folder name; D1 = b6e7d436 (lead-in pad) + 9ad93344, D4 = 3641440f (registry avatars), each with
  must-fail tests; G15's run-6 failure is OD-1 (the N of "Natalie", od1_g15_evidence/).
- Cross-LLM I2 "HOLD verdicts silently dropped by the wrapper; get sign-off": the orchestrator ordered it
  (08:30: "PBX gets the next thing only when it passes"), the wrapper logs "HOLD (run_fresh exit N): not
  delivered; see REPORT.md", and the comment cites the note.
- Cross-LLM P5 (scorer timeout must fail closed): already the behaviour (rate errors -> rate_error, no
  verdict -> the conjunction clip fails) and tested (test_a_clean_lineup_passes_and_an_unavailable_scorer_
  fails_closed). P6 (zero-length clip in shot_snap.plan): head >= tail returns no snap.
- Cross-LLM U3 (error messages): the HOLD reasons name the segment, the failing part and the scorer verdict;
  shot_snap raises with the clip path on a frame-count change.
