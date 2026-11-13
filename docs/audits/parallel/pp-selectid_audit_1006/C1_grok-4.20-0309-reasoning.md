# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 47 s finish=stop usage in 7934 / out 290 usd~0.047 (upper-bound price)

**P0: none**

**P1: none**

**P2:**
- pipeline/package.py:66 (first_fresh): extra lineup_for() call per angle (up to 3) solely for sorting; cost is verifiable in the added lines and test coverage but not measured.
- pipeline/package.py:56 (key = (f[0], f[1], ...)): prepends (has_fresh, -mean_age) ahead of prior positional/duration keys; matches stated K3 but changes every call site that passes now.
- pipeline/package.py:68 (sorted(..., key=lambda a: not first_fresh(a))): reordering is stable and purely by whether the *best* lineup under the new key contains a fresh clip; verified by TestRuling57Fresh but relies on cleared/ctx.now defined earlier in build().
- pipeline/package.py:39 (fresh_key): no-published_at case treated as oldest (max(default=0.0)+1); test at line 120 confirms but behavior for mixed known/unknown lists is only partially exercised.
- No diff lines alter accept=half, need_onset, need_stand_alone, dropped sets, or any gate/usable() logic; time-sensitive enforcement (L-v 3) untouched.

All stated K1-K3 readings match the code. TestRuling57Fresh and existing callers (now=None path) pass.

**SHIP: yes**