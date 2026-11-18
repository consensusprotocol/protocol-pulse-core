# qwen3.8-27b (qwen/qwen3.8-27b) 169 s finish=stop usage in 5972 / out 4812 usd_reported=0.003709 usd~0.090 (upper-bound price)



## Audit Findings — pp-selectid / C1_STEP.diff

### Context

The diff extracts the never-empty pass's "come-back" logic into `stand_soft_back(ms, no_role, soft)` and removes the `m["moment_id"] not in trims` guard. Rationale: build 147 showed that when a trim variant fails ruling 33 (HARD), the original was still excluded because it *had* an affirmed variant, losing the channel entirely. The fix lets the original re-enter the pool flagged (`stand_soft`) beside its variant, relying on L-y 4 (one clip per video) to prevent double-selection.

---

### Findings

**[P2] No integration test for the build-147 regression path**

The new unit test (`test_an_original_comes_back_beside_its_trim_variant`) exercises `stand_soft_back` in isolation with synthetic moments and verifies the signature no longer accepts `trims`. However, the actual failure mode that motivated this change — a trim variant present in the pool that *fails* ruling 33's trimmed-cut gate, causing the line-up to fall back to the `stand_soft`-flagged original — is not tested end-to-end in this diff. The description states "the existing end-to-end STAND_ALONE tests pass unchanged," but those tests were written under the old invariant (original excluded when a variant exists). A regression test that:

1. places a moment in `ms` with an affirmed trim variant in `trims`,
2. causes the variant to fail `trim_refused` / ruling 33,
3. asserts the original carries `stand_soft` and is selectable,

would lock in the fix and prevent a future refactor from silently re-introducing the `not in trims` guard.

**[P2] L-y 4 mutual-exclusion not verified in this diff's tests**

The docstring and the change description both state "one line-up never takes both (one clip per video, L-y 4)." Now that both the original and its trim variant can coexist in the pool, the line-up selection must enforce that only one is chosen. This diff's tests do not assert that constraint for the new co-existence case. If L-y 4 is enforced elsewhere with its own tests, this is a coverage gap in *this* diff rather than a correctness bug; but a one-line assertion in the new test (or a companion test) that the line-up picks exactly one of {original, variant} would make the invariant explicit at the point where the co-existence is introduced.

**[P3] `import inspect` inside the test method**

```python
import inspect
self.assertNotIn("trims", inspect.signature(PK.stand_soft_back).parameters)
```

The import is local to the method. Functionally harmless, but inconsistent with the module's top-level imports and slightly obscures the test's intent (it's really a "the helper must not depend on trims" assertion, which could be phrased as a docstring note or a `# noqa`-style comment). Nit only.

---

### Law-compliance check

| Law | Status |
|-----|--------|
| SENTENCE LAW | Unaffected — no boundary logic changed. |
| SELECTION LOCK | Unaffected — `selection_lock` / sha256 seal untouched. |
| SNAP LIMIT / NEIGHBOUR / ONSET-TAIL | Unaffected. |
| L-a … L-l | Unaffected. |
| LAW 20 / M2 | Compliant — no gate threshold altered; no failing gate reclassified. The trim variant still must pass ruling 33 independently; the original still must pass the opener rule (softly). |
| M12 FAIL CLOSED | Compliant — `soft=False` returns `{}`; `no_topic(m) is not None` excludes the moment; `stand_plain(m)` returning falsy excludes it. No path produces a pass from missing data. |
| LAW 22 (v2f) | Unaffected. |
| Smallest diff / M1 | Compliant — one function extracted, one condition removed, one call-site updated. No new renderer, compositor, or selector. |

No [P0] or [P1] violations identified.

---

P1_OR_WORSE: 0