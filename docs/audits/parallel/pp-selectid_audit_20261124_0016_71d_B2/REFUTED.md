# Consensus findings refuted against the code (00:50 ET Nov 24)
Seats: qwen27b and gemma answered (effort high, 65,536 tokens); gpt-oss answered out of contract (no JSON).

1. [critical] "package.py 2387: call to undefined function package_pin.flags_cap": REFUTED. package_pin.flags_cap is defined (pipeline/package_pin.py, `def flags_cap(gates)`, returning REVIEW_FLAGS_MAX); `python3 -c "import package_pin as PP; print(PP.flags_cap({}))"` prints 3, and package.chain_cap() returns 3. The reviewers saw only the hunk that calls it.
2. [high] "package.py 167: .get() on STEP_A_SOFT, which is a set": REFUTED. STEP_A_SOFT is a dict (pipeline/package.py line 91, `STEP_A_SOFT = {"NOT_OWN_SINCERE": "...", ...}`); type() prints dict.
No code change. Suites 42 files, 0 failing.
