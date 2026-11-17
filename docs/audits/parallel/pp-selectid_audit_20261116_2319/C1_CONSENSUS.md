# C1 CONSENSUS — pp-selectid audit 20261116_2319 (RULING 130 (3): the vision reserve priced from the bills)

Seats (Heimdall only): qwen3.8-27b (effort medium, 24,000), gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 2 of 3
(mimo EMPTY at 32,000). P1_OR_WORSE: qwen 0, gemma 0. Cycle 1 $0.0099 of Heimdall, not capped.
qwen's three P3s, no change: (1) held == 0 cannot reach the new test: over_held needs a configured fraction, and such a
back-end's reservation is fraction x a positive upper bound; a back-end without one (Heimdall, uncapped) never trips;
(2) reserve_list_fraction_why is documentation only, as its suffix says; (3) the vision test reads the live config on
purpose: it takes every number from the configured spec (price, min_out, fraction), none typed, so a price change moves
its expectations with it. dev52: mutations V1-V3 3 of 3 killed after a control run; 40 suite files by exit code, 852
tests.
