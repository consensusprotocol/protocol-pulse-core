# Cycle 1 consensus (pp-selectid_audit_20261117_1135, rulings 136 / 137 stage 1)

SEATS ANSWERED: 1 of 3 (qwen3.8-27b, P0/P1 none, a traced review; gpt-oss-20b and gemma-4-31b-it spent their token
caps with no answer). Cycle 2 raises their caps (gpt-oss 32,000, gemma 24,000).

## Findings
- qwen [P2] build(*args, **kw) would forward a caller's soft=True into the CLEAN pass: ACCEPTED. The wrapper strips
  "soft" from kw before the clean pass; a test passes soft=True and shows the passes are still clean then soft.

## Changed since cycle 1's diff
1. RULING 138 (3) (orchestrator 11:40 ET): "each flag is one plain sentence PBX can judge in five seconds (what the
   checker doubted, about which clip), no codes". STEP_A_SOFT now holds the doubt in plain words; flag_sentence(label,
   channel, code) makes "The opening clip (Scott Melker): the checker doubted this is the speaker's own sincere view
   (they may be quoting someone or joking)."; inventory(..., who={label: channel}) builds one sentence per clip and
   code; both inventory calls pass who from the package's segments.
2. RULING 137 (3): the day cap is $1.50 all-in from tonight (today's stop $1.40, passed as --stop-usd), so
   proof_ledger.STOP_CEILING_USD 1.25 -> 1.50 (its test: 1.51 is refused). Without it today's kept line-up's fourth
   vision check could not start under the old $1.25 ceiling (four sheets of 0.6 x list each, after the step-A bill).
3. Suites: 41 files by exit code, 880 tests (before changes 1-2); the touched files' suites pass after them (81 tests).
