# Batch 62 cycle 2: no consensus findings
glm raised three, each with 1 vote:
- F2 [medium] "a failed scoring is never retried": wrong on the code.
  - latest() returns an entry with score None only when no entry has a score. The reuse test then fails, and the
    candidate is queued again.
  - Its earlier request file has moved to requests/done/, so the new one is written.
  - A failed scoring is asked again on the next candidates pass.
- F1 [high] / F3 [medium]: a score-None entry is a recorded failure, not a verdict. It reaches the builder as
  affirmed false WITH "error", so they never mistake it for a refusal. Entries for several events share a moment's
  file, and every reader filters by event (latest(); the contract says so). The render's validate never reads these
  files: it asks the model, whose reply cache is keyed by the exact prompt.
- Cross-examination (not voted): partial-write edge cases in answer(). A failure there surfaces as an exception in
  the service's log; nothing is affirmed by it.
