# Ruling 87, the builder's probe claim taken up: cycle 1 consensus

Reviewers (Heimdall): qwen3.8-27b (197 s, $0.020): "The change is correct ... ready for production"; muse-spark-open
(469 s, $0.028): "P0 CRITICAL (none) ... P1 HIGH (none) ... Ready for production. Deploy on next restart"; glm-5.3-flash
(723 s, $0.007; its reply reached its length limit while reviewing the rest of the package): "Verdict on the change:
correct, minimal, fail-closed". All three answered the three questions the same way: the signature check is sound
(a plain module-level function; the TypeError / ValueError fallback); the claim leaves the probe life cycle as it was
(report first; `_probing()` guards this process, the claim guards the fleet; a kept report (C2-1) lands inside the slot
its claim already stamped, or is dropped and the slot stays spent from the claim); no path where `who` makes a call
fail on either module version (a table of new / old / broken / missing module from muse).

## Taken
- qwen P3: a test for the fallback when `inspect.signature` cannot read probe_due's signature
  (`test_a_probe_due_whose_signature_cannot_be_read_is_called_without_a_name`: a `__signature__` that is not a
  Signature raises TypeError; the watcher calls probe_due without a name and the probe works).

## Recorded, not changed
- muse P2 "catch BaseException in `_call`": older than this change and the same in every loop of the watcher
  (`Service._loop` catches Exception); a KeyboardInterrupt is delivered to the main thread only, and a SystemExit from
  the builder's module would be a bug in that module. Not changed.
- glm P3 "the check reads the parameter's name, not whether it can be passed by keyword": a future positional-only
  `who` would make probe_due raise TypeError inside `_call`, i.e. "not read" (live.json at once, STATE after 30 min):
  fail-closed and visible, not silent. glm P3 "the check is made once at start": the module is loaded once per process
  by design (a restart takes up a new version). glm P2 note: if reports are lost systematically, a probe runs every
  ~120 s plus its duration (claim-anchored): the builder's semantics, accepted.
- Items on code outside this change (muse: yt-dlp pinning, the all-time spend query, structured logs; glm's whole-package
  walk-through): recorded only.

Tests: tests/ingest 271 passed (27 in test_signal.py). Cycle 1: $0.055.
