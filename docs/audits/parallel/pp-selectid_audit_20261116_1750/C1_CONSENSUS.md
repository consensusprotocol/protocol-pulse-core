# C1 CONSENSUS — pp-selectid audit 20261116_1750 (ORDER 17:50: --only and --stop-usd in the build driver)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: qwen 0,
gemma 1, mimo 1. Cycle 1 $0.0072 of Heimdall, not capped.

gemma's P1 ("main raises ValueError instead of returning 2"): NOT SO. Both checks run INSIDE the driver's refusal block
(dev48 proof_ledger.py:406 and the --stop-usd check after it), whose handler (:436, unchanged) catches ValueError, prints
REFUSED and returns 2; the tests assert exactly that and pass (no proof dir written).
mimo's P1 ("the order's 'unless a package is one call from its seal' is not implemented: --stop-usd is a hard stop"):
TRUE THAT THE STOP IS HARD, by design: the exception is the operator's, said in tonight's plan on STATE line 1: when a
build stops on its $0.80 limit one paid call short of a seal, the SAME --only set is run again with --stop-usd 1.00; the
calls it already made are served from the step-A, hook, join, visual caches and the recorded replies, so only the
missing call is paid. No change.
mimo's P2 (an --only set none of whose ids is in the pool gives an empty pool): the build then records "0 of N listed
moments" and no package; it spends nothing. Kept (the generator writes only ids it read from the newest record).
mimo's P3s (a test of the 1.25 boundary; --only with --from-candidate): noted; tonight's runs never combine them.
qwen's [P1] headings are checks it answers itself (count 0).
