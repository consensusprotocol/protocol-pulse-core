# Batch 4 (4b: same-event merge, DEC-9 story ledger, letterbox one frame per shot) — dispositions

Audited range b74c3b6c..pulse-4b-wip (a2b56e53), pipeline/ + scripts/ (820 lines). Cross-LLM: GPT-4o +
Gemini (Grok blocked by the xAI ceiling). Heimdall: deepseek + qwen27b, one chunk per file (8 chunks).

## Implemented (follow-up commit on the same branch; each tested)
- Heimdall wrapper [high + medium, consensus]: the ledger call shared the delivery's python process, so a
  ledger fault (or a broken import) after a successful drop read as "Telegram delivery FAILED" (exit 70)
  and invited a duplicate drop. Now two steps: delivery (70 on failure), then the ledger from
  TELEGRAM_DELIVERY.json (71 = delivered but NOT recorded, logged loudly: the next auto run could select
  the story again). A ledger fault is never silent and never reads as a failed drop.
- Heimdall visual_check [medium, consensus]: with no VISION_MODELS the letterbox check passed vacuously
  (`all()` of nothing) -> no model asked = no answer = FAIL. Test: VISION_MODELS patched to ().
- Heimdall visual_check [low, consensus]: a talking head shorter than two frames gave lo > hi -> midpoint.
- Heimdall visual_check (one vote): layout=None -> treated as no layout. verify_pack (one vote): the V1
  message dropped the letterbox list when a route error was also present -> both are listed.
  story_ledger (one vote): `sel["headline"]` -> `.get`.
- Cross-LLM U2/5/7: each frame's row now carries every model's attempt trail (answer + reason, or the
  route error) into GATE_REPORT V1.letterbox_per_shot; ask_letterbox's retry exhaustion is tested
  (route error, then an unclear reply -> None, both attempts recorded).

## Rejected, with evidence
- Cross-LLM U1/UI1/UI2 and action items 1-4, 6, 9 ("the feature named pulse-sentence-law implements no
  sentence law, snap limit, onset/tail or credits gate; rename the branch"): `pulse-sentence-law` is the
  mission's audit folder, not this diff's scope. Those laws landed earlier with must-fail tests: 1a
  b6e7d436, 1b+1c 99add647, 1e (credits) 3641440f, 1d 9ad93344, punctuation a1e732e1; G16/G18 run on every
  render. This diff is mission 4b.
- Cross-LLM 8 (ledger across run boundaries untested): test_story_ledger TestLedgerInSelection runs the
  selection twice against a persisted ledger file and asserts the delivered event is excluded with its
  ledger run.
- Heimdall verify_pack (one vote) "a contact-sheet error skips the letterbox check, so a letterboxed video
  could PASS": with no sheet V1 is already FAIL ("no contact sheet") before the letterbox step.
- Heimdall story_ledger (one vote) `__main__` without an argument: an operator CLI helper; not changed.
