# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 42 s finish=stop usage in 13464 / out 685 usd~0.084 (upper-bound price)

**P0: pipeline/package.py:83 (same_speech)**  
REPOST_ALIGN_MIN is read (sum of long matching blocks >= REPOST_ALIGN_MIN * short) but no definition, assignment, or import of it appears anywhere in the diff (only SAME_SPEECH_MIN_WORDS=8 and SAME_SPEECH_RUN=3 are added). Concrete scenario: any call to usable() on a delivered span from another video raises NameError before same_speech can enforce ruling 76(b). Tests that invoke PK.same_speech would also fail under a clean interpreter.

**P1: pipeline/package.py:110 and candidates.py:46 (expire + usable interaction)**  
A candidate whose *last* clip is >12 h (or has unknown publish time) is expired/closed, but the diff does not show that CA.due(), CA.registered(), or any later seed() path is guaranteed to ignore a re-seeded record that was previously closed as "expired". Concrete scenario: proof_ledger re-runs on a CANDIDATES.json that later gets a fresh seed(reg, record_with_old_clip, ...) before the expire() call; the diff leaves open whether the closed state survives or the moment re-enters a lineup. (Test only shows one fresh registry after expiry.)

**P2: tests/package/test_medley.py:338 and pipeline/package.py:82**  
same_speech accepts any two strings whose canonical tokens are identical even if <8 words, but rejects any pair <8 words that differ. Concrete scenario: a 7-word delivered hook that is re-posted verbatim in another video is *not* blocked by ruling 76(b) (only the overlap rule can catch it, and that rule is video_id-specific). The 80 % / run-length heuristic is therefore unreachable for short clips; the diff gives no evidence this matches the owner's intent for "the same speech".

**P2: pipeline/package_pin.py:149 and proof_ledger.py:230**  
window_problems() and the pin-stage call both default to datetime.now(timezone.utc) at the exact instant the check runs. This satisfies "render clock at that moment" for the shown path, but the diff does not show what happens if the pin write is deferred (e.g. queued for later render); the re-check would then use a later clock. (Uncertain from diff alone whether any such deferral path exists.)

**P2: pipeline/candidates.py:38 (_at)**  
expire() calls _at(published[mid]) inside a try/except that treats any failure as "no known publish time". _at itself is not modified or shown in the diff; behavior for malformed ISO strings or missing keys is therefore unchanged from prior code.

All other required checks (no >12 h moment reaches a pin, delivered same-speech blocked for other videos, --hours >12 refused before any write, seal() byte signature untouched, only the two new elif branches added to usable(), ruling-76 counts logged, tests cover the new branches and the mutated refusal paths) pass on the visible diff. The 15-suite "OK" claim cannot be independently verified from the diff alone.

**SHIP: no** (P0 NameError blocks any execution of ruling 76(b); must add/fix REPOST_ALIGN_MIN constant and confirm due()/seed() cannot revive an "expired" candidate).