# C2 CONSENSUS — pp-selectid audit 20261116_1750 (ORDER 17:50: --only and --stop-usd in the build driver)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 2 of 3 (mimo cut off at 32,000
tokens, no answer). P1_OR_WORSE: qwen 0, gemma 0 (gemma withdrew its cycle-1 P1). The whole audit $0.0139 of Heimdall,
not capped. CLEARED. On dev48: 40 suite files by exit code, 847 tests; mutations O1-O6 after a control run: 4 of 6
killed; O1 (applying --only) and O3 (the stop to the start check) are main()'s two call sites, reachable only by a full
driver run: tonight's records show them (inputs.only; spend_ruling_48.stop / order_17_50_stop).
