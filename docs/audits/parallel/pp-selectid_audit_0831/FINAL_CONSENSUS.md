# pp-selectid audit 0831 (order 08:06 item 55): final consensus after cycle 2

**Cycle 2:** no P0 from any reviewer. qwen: production ready. grok and glm: "yes with conditions".

| # | condition | disposition |
|---|---|---|
| C1 | grok "P1": the new test opens files without closing them | Fixed: every read uses `with open(...)` (a small lines() helper). |
| C2 | glm: does any other path in Router.call abandon a back-end without the DeadlineExceeded handler? | No. In call(), a back-end is abandoned at its deadline ONLY in the DeadlineExceeded branch, which logs it. The other outcomes are not missed deadlines: a skip (avoided or down, no call made), a replayed recording, RequestRejected (the vendor refused), Unavailable (marked down), and any other exception (re-raised). |
| C3 | glm: a schema paragraph in the evidence file | Added to pp-selectid_HEIMDALL_DEADLINES.md. The backfilled .jsonl lines now use the code's kind names ("answered_slowly", with threshold_s 240). |
| C4 | glm (optional): cap notices, hoist makedirs, millisecond stamps, a usage=None test | Not taken: optional and P2. A missing usage records in / out as null. |

Verification: test_providers 16 OK; every other suite OK; regression_test.sh is run before the commit.
