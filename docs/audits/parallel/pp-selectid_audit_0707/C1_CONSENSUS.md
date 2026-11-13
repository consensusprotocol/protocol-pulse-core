# pp-selectid audit 0707 (RULING 48: the spend cap on vendor-reported dollars): cycle 1 consensus

**Run.** Verdicts:
- grok: no P0 / P1, "SHIP: yes";
- qwen: no P0 / P1, "SHIP: yes";
- glm: no P0, "SHIP: yes with conditions" (P1-1, P1-2).

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | glm P1-2: the reported basis reads a missing usd_reported / usd_unreported_estimate as 0.0, a silent fail-open on a legacy ledger | _basis_total refuses (SpendLimit) a ledger that has calls but neither key. _settle creates one of the two keys on every settled call, a free one included, so only a ledger that predates them can lack both. Tested. |
| F2 | glm P1-1, the part that holds: after the build, router.spent() raises SpendLimit on an unreadable ledger, before package.json is written, so the build's record would be lost | The post-build read is caught. spend_ruling_48.after then records "unreadable: ...", and the record is always written. |

## Refuted (verified from the code)

| # | claim | the code |
|---|---|---|
| R1 | glm P1-1: `res["spend_ruling_48"] = ...` raises when the build produced no package | res is the dict PK.build returns on every path (out). The line before it already does res.update(...). A build that raises never reaches either line, as before. |

## Verification

- test_providers 15 OK (the ruling-48 test extended with F1); every other suite OK.
