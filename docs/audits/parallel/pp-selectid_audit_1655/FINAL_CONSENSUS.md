# pp-selectid audit 1655 (ruling 66: the search leaves every registered line-up to the registry): FINAL consensus (cycle 2)

**Cycle 2:** grok "SHIP: yes", qwen "Production ready: yes", glm "Production ready: yes, no conditions". No P0 and no
P1 from any reviewer.

All three confirm the cycle-1 consensus fix: the no-voice fallback was the one judging site outside the main loop's
check, and both medley() sites now read held_map.

No code change after cycle 1.

## Recorded, no change

| # | finding | why no change |
|---|---|---|
| 1 | qwen P1-1 (self-retracted in the same review): the no-voice check reads `cand` before the added clip | `cand = [segs[0]] + sorted(segs[1:] + [m], ...)` includes the added clip `m`. The test's `registered_skipped == ["h+x+y+z"]` shows it. Not a defect. |
| 2 | qwen P2: comment that `cand` is the new line-up | Its assignment is two lines above the check. One reviewer only. |
| 3 | qwen P2: a simpler unit test for the no-voice check | The Rig test drives the real loop, and its mutation run fails without the check. |
| 4 | glm P2-1 / qwen C1 P2-2: refused_only() patches os.makedirs for its block | Intended to be strict. The refusal path only reads, and the driver's first write is os.makedirs(out_dir). |
| 5 | glm P2-2: the second CA.registered(reg), after run_due, sits outside the refusal try | It cannot raise there. run_due / outcome change only state, until, history, fresh_used and trying_fresh. registered() reads lineup, key, source and index, which the first call validated. |
| 6 | glm P2-3: why_not uses `.get` in the condition and `[...]` in the value | Evaluated together; cosmetic. |
| 7 | glm P2-4: the pool-fill test captures the line-up from a first Rig | The Rig has no randomness, and both rigs get identical inputs. |
| 8 | glm N4: "angle 2's line-up is ['x']" | A misreading. `[c[0] for c in rig.medley_calls]` lists each judged line-up's first id (its hook), so this says angle 2's line-up opens on x. |
| 9 | grok P2: held_map assumes a dict or None; the why f-string assumes the keys exist | The driver passes candidates.registered(), whose entries always carry key, state, until, source and index (validated in the refusal block). |

## Cost of this audit (upper-bound price estimates from each reply's usage, outside the ruling-48 ledger)

| cycle | grok | qwen | glm |
|---|---|---|---|
| 1 | $0.058 | $0.055 | $0.077 |
| 2 | $0.092 | $0.093 | $0.092 |

About $0.47 in all.
