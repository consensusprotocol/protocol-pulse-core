# r123: the miner's last fallback, the local model on a free card under the lease, cycle 2: consensus

Reviewers (Heimdall, diff-scoped, cross-validating cycle 1 and its consensus): qwen3.8-27b (35 s, $0.002 reported):
"P0 CRITICAL: None. P1 HIGH: None. P2 MEDIUM: None ... PRODUCTION READY? Yes", its two cycle-1 "critical" points
withdrawn as "false positives or contextual errors"; muse-spark-open (105 s, $0.003 reported): "P0 CRITICAL: (none)",
one P1 (its own cycle-1 P2, raised), "Without P1-1: Still Yes, ship ... Do not block deploy on P1-1". Cycle 2: $0.0044;
the audit $0.0164 of its $1.00 cap (COST.json).

## Agreed by both (verified)
- The refutations of cycle 1 stand: the client file imports importlib.util (its line 10); one thread at a time is in
  complete() (the router's semaphore, providers.py:819); every back-end, the local one included, has the router's
  breaker (providers.py:817 / 868 / 1019; 5 failures in a row, 300 s open).
- The yield logic (`reached` False only for a refusal), the `busy` kind (no retry on the card, outage), the B3 check
  in enabled(), the tests' guard and the real-client integration test are correct (both: "high-fidelity").

## Refuted (with the evidence)
- muse P1-1 "catch BaseException around lease_client(): a SystemExit / KeyboardInterrupt / Gpu0Stop raised while the
  client file is imported escapes complete(), Router.run re-raises it and it kills the miner thread":
  1. Nothing kills a thread. The mine loop calls mine_once() with no wait (service.py:1002, wait=False), so no loop
     thread ever re-raises a window's exception; the video's own worker is a ThreadPoolExecutor worker, whose
     _WorkItem.run catches BaseException into the future (Python 3.10 concurrent.futures.thread); and
     service.mine_video's `except BaseException` (service.py:333) puts the video back to mine_waiting ("mining
     stopped: ...", retried after MINE_RETRY_S) before re-raising into that future. This is the path every GPU stop
     took by design before r123 ("never renamed").
  2. It cannot be raised in production: the real client imports only importlib.util, os and sys and defines a class
     and two functions; gpu0.py is loaded only inside chat_gpu1 (gpu0()), whose stops the client renames.
  3. Catching BaseException there would rename a process stop (KeyboardInterrupt) into "disabled", the thing law L-r's
     STOPS clause forbids; and the tests' stand-in file raises SystemExit on purpose so that a test that ever loaded it
     fails loudly (M61 is killed that way).

## Recorded (comments, for the next audited change; no edit after cycle 2: the code shipped is the code audited)
- qwen P3 / muse P2-1, P2-2: comments at `_free_at` (serialised by the router's semaphore), at lease_client()'s cache
  (kept only after the checks) and at `reached` (False only for a refusal). The class docstring already states the
  last two.
- service.py's idle release comment ("the local model (if any) leaves GPU0 (B3)", not in this diff) is stale: since
  r123 every back-end's release() is a no-op (nothing is held between requests).
- From cycle 1: reporting the GPU wait apart from the reply's latency (gpu0's events in this process); an adaptive
  yield (refused: looking at the lease is itself a flock probe).

Suite: tests/ingest 439 passed. Mutations M51-M64: 14 of 14 killed; the unmutated control passed. No P0 or P1 open.
