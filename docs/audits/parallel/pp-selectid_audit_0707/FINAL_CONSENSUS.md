# pp-selectid audit 0707 (RULING 48): final consensus after cycle 2

**Cycle 2:** no P0 or P1 from any reviewer.
- grok: "yes with conditions" (accept or tighten its P2s; run the suites);
- qwen: production ready, no P0 / P1;
- glm: "yes with conditions", all P2 (below).
All agree that:
- F1 (a legacy ledger fails closed) and F2 (the post-build read cannot lose the record) are right and tested;
- the reported basis counts every call exactly once;
- the lock and reservation logic are unchanged;
- the $10 start-gate and the $12 hard cap read the ruling correctly.

## The conditions, answered (no code change)

| # | condition | answer |
|---|---|---|
| A1 | glm N1 / condition 1: guard `res` before `res["spend_ruling_48"]` | PK.build returns its dict `out` on every return path (every `return out` in build()), and the line before already calls res.update(...). A non-dict res cannot reach the assignment. |
| A2 | glm condition 2 / N2: does _settle write the keys on every settled call? | Yes. providers.Router._settle: a call with the vendor's figure adds it to usd_reported; else, a free call or a zero-valued one included, it adds its estimate to usd_unreported_estimate. A ledger where every call so far reported a figure has no unreported key, and its unreported total is then truly 0. |
| A3 | grok / glm: the STATE line-1 total | The builder writes STATE line 1 after every build from package.json's spend_ruling_48 (before / after / cap / stop). The driver logs the same figures. |
| A4 | grok: run the suites | Done before the commit: test_providers 15 OK, every other suite OK, regression_test.sh 0 FAIL. |
