# Rising Star candidate rule: `rising_star_candidate_v1`

**Status: provisional. Publishing is disabled.** No page, feed, post or alert shows a rising star from
observed data. `core/book_signal_rules.py` holds the rule (`RISING_STAR_RULE`, read-only) and
`PUBLISHING_ENABLED = False`. The only "Rising Stars" on the site is the illustrative section of the private
`/books/market` prototype, which applies this rule to synthetic data and says so.

Frozen on 2026-11-25. Selected on observations from 2026-04-01 to 2026-11-24 (see "How the threshold was
selected": the selection is in-sample).

## The frozen rule

```python
RISING_STAR_RULE = {"name": "rising_star_candidate_v1", "frozen": "2026-11-25", "median_window_days": 14,
                    "min_improvement": 0.40, "min_observed_per_window": 10, "max_current_median_rank": 150000,
                    "persistence_days": 3, "status": "provisional"}
```

For one book on one day (`evaluate(series, day)`):

| Step | Definition |
|---|---|
| Current median | Median of the book's observed Amazon ranks on the 14 calendar days ending on the day |
| Prior median | Median of its observed ranks on the 14 calendar days before those |
| Evaluable | Each window holds at least 10 observed days |
| Condition | Current median ≤ 150,000, and improvement = (prior − current) / prior ≥ 0.40 (a lower rank number is better) |
| Qualifies | The condition holds on the day and on each of the 2 calendar days before it |
| Episode | The first day of a run of qualifying evaluation days (evaluation days: every day on which at least one tracked book has an observation) |

Observed rows only: a row counts when it is an observation (`label: "observed"` in the recovered history,
`status: "ok"` in the collector's history) with a positive integer rank. Carried-forward values, placeholder
ranks, failed fetches and null ranks never enter a window, and a missing day stays missing. The test
`test_counting_carried_forward_rows_would_change_the_episodes` shows that counting carried-forward rows would
change the episode list on the real history.

Ranks are compared only within one book's own series. The rule never compares two books, and it never mixes
the Amazon list a rank belongs to with another one.

## The 6 historical episodes

The rule finds exactly the 6 episodes of the backtest's C6 variant (`~/book_terminal_work/rising_backtest/summary.json`,
`C6_C4_persist3_rank_le_150k`). `tests/books/test_rising_star_rule.py` reproduces them from a committed
fixture and, on a machine that has it, from the full history file too.

| # | Book | Amazon ID | First qualifying day | Prior 14-day median | Current 14-day median | Improvement (gain) | 9-day outcome (share of the gain kept) | 28-day outcome, in-sample (share kept) |
|---|---|---|---|---|---|---|---|---|
| 1 | Mastering Bitcoin (3rd ed.) | 1098150090 | 2026-05-01 | 223,090 (13 days) | 122,438 (13 days) | 45.1% | held (median 115,309; 48.3% kept) | held (median 207,473; 7.0% kept) |
| 2 | The Sovereign Individual | 0684832720 | 2026-07-07 | 15,519 (13 days) | 7,825 (10 days) | 49.6% | held (median 11,291.5; 27.2% kept) | held (median 15,075; 2.9% kept) |
| 3 | The Big Print | B0DVTCVX8J | 2026-08-09 | 69,462.5 (12 days) | 38,835 (13 days) | 44.1% | held (median 67,511; 2.8% kept) | held (median 48,974; 29.5% kept) |
| 4 | The Sovereign Individual | 0684832720 | 2026-08-20 | 15,409 (11 days) | 6,174 (14 days) | 59.9% | held (median 6,450.5; 58.1% kept) | held (median 8,840; 42.6% kept) |
| 5 | Mastering Bitcoin (3rd ed.) | 1098150090 | 2026-10-22 | 273,106 (11 days) | 137,528.5 (12 days) | 49.6% | held (median 155,314; 43.1% kept) | held (median 180,831; 33.8% kept) |
| 6 | The Price of Tomorrow | 1999257405 | 2026-11-24 | 86,298 (13 days) | 46,712 (13 days) | 45.9% | cannot be evaluated yet | cannot be evaluated yet |

The summary file lists the gains rounded to two places: 0.45, 0.5, 0.44, 0.6, 0.5 and 0.46.

**The 5 evaluable outcomes: none reversed within 9 days.** The 9-day check is the backtest's: the median of
the observed ranks on days 5 to 9 after the first qualifying day (at least 2 observations) is compared with
the prior median. At or above it, the whole gain was given back ("reversed"). Below it, "held".

**Why the 6th cannot be evaluated.** The Price of Tomorrow first qualified on 2026-11-24, the last observed
day of the history. No observation exists after that day, so the 9-day window (2026-11-29 to 2026-12-03)
and the 28-day window have nothing to judge yet.

**What "held" does and does not mean.** "Held" only says the book did not give back the *whole* gain. Episode 3
kept 2.8% of a 44.1% climb at day 9 and still counts as held. The "share kept" columns give the size: (prior
median − outcome-window median) / prior median. The 28-day column applies the same check to days 24 to 28. It
is in-sample, computed for reference after the rule was chosen, so it is not evidence for the rule.

## How the threshold was selected

Seven variants (C0 to C6) were tried, all on the same history (2026-04-01 to 2026-11-24, 12 books with
observations, 2,467 observed rows). They were defined after looking at that history, and the best one, C6, was
chosen. **This is in-sample selection, based on 6 episodes, so the overfitting risk is material.** A 0%
reversal rate on 5 evaluable episodes is weak evidence: the rule's thresholds (40%, 150,000, 14 days, 10
days, 3 days) were picked on the same data they are scored on.

Variant definitions, as in `backtest_rising.py`. "Rank" means the observed Amazon rank number, where lower is better.

| Variant | Signal on day t |
|---|---|
| C0 `prev_fetch_10pct` | Rank at least 10% lower than the book's previous observed rank (the retired previous-fetch rule) |
| C1 `7d_median_20pct_min5obs` | Median of days t−2..t at least 20% lower than the median of days t−9..t−7; at least 2 observations in each of those windows and at least 5 observed days in t−7..t |
| C2 `7d_median_30pct_min5obs` | As C1, with 30% |
| C3 `7d_30pct_persist3` | C2 on 3 consecutive calendar days |
| C4 `14d_vs_prior14d_40pct_min10obs` | Median of days t−13..t at least 40% lower than the median of days t−27..t−14; at least 10 observed days in each |
| C5 `C4_plus_rank_le_150k` | C4, and the current 14-day median ≤ 150,000 |
| C6 `C4_persist3_rank_le_150k` | C5 on 3 consecutive calendar days (the frozen rule) |

The full results from `summary.json` follow. The window is 238 days (34 weeks).

| Variant | Signal days | Episodes | Episodes per week | Distinct books | Episodes checked for reversal | Reversed within 9 days | Reversal rate |
|---|---|---|---|---|---|---|---|
| C0 | 596 | 466 | 13.71 | 12 | 450 | 138 | 0.31 |
| C1 | 622 | 199 | 5.85 | 12 | 192 | 59 | 0.31 |
| C2 | 475 | 166 | 4.88 | 12 | 159 | 39 | 0.25 |
| C3 | not recorded | 73 | 2.15 | 12 | not recorded | not recorded | 0.17 |
| C4 | not recorded | 40 | 1.18 | 12 | not recorded | not recorded | 0.25 |
| C5 | not recorded | 9 | 0.26 | 4 | not recorded | not recorded | 0.12 |
| C6 | not recorded | 6 | 0.18 | 4 | 5 (from the 6 listed episodes) | 0 | 0.0 |

For C3 to C6 the summary stores only the rate and up to 8 example episodes. C6 has 6 episodes and all of them
are listed, so its checked and reversed counts follow from the list.

## Prospective evaluation plan

1. **Score new observations only.** An episode counts when its first qualifying day is on or after
   2026-11-25, the freeze date. A run that began before that date is not a new episode. Windows may reach back
   into older observations: they need 28 days of history.
2. **No threshold changes before ≥ 12 weeks or ≥ 10 new episodes, whichever comes first.** That means no
   change before 2027-02-17 (12 weeks after the freeze) unless 10 new episodes arrive sooner. Any later change is a new rule with a new
   name and freeze date, and it starts its own prospective count.
3. **Record each episode's 9-day and 28-day outcome**, as defined above. An outcome window that has not ended
   is "pending", never judged on a partial window. (The backtest judged partial windows near the end of its
   data. None of the 6 C6 episodes was affected.)
4. **Publishing stays disabled** throughout: no surface shows these episodes. Turning publishing on is an
   owner decision after the evaluation, together with the wording and the data-quality checks.

The tool is `scripts/books/evaluate_rising_star_prospective.py`. It is not scheduled, and it makes no network
calls.

```bash
python3 scripts/books/evaluate_rising_star_prospective.py data/book_metrics_history.jsonl --out /path/to/report.json
```

It reads the recovered format (`run_day`, `label`) and the collector's own history format (`ts`, `status`;
the day is the New York date of `ts`). It writes the rule, the input summary, and every episode from `--since`
on (default 2026-11-25) with both outcomes. On the recovered history, which ends 2026-11-24, it reports 0
prospective episodes and 6 in-sample ones before the freeze date.

## Data

- Source: `~/book_terminal_work/recovery/history_labeled.jsonl`, the collector history archived on 2026-11-24.
  Each of its 3,360 rows is labeled against the archived run log: 2,467 observed, 221 carried forward, 672
  placeholders. It is not committed. `tests/books/fixtures/rising_history_observed.json` holds its observed
  ranks and carried-forward rows in compact form (23 KB), plus the 3 IDs that only ever had a placeholder.
- 14 days between 2026-04-01 and 2026-11-24 have no history at all. The windows treat them as missing days.
- Two of the 12 observed IDs are no longer in the registry: 1260026671 (Cryptoassets, removed) and
  1544526474 (an ID the registry replaced). Neither has a C6 episode.
- The registry tracks print editions in Amazon's "Books" list, apart from The Fiat Standard (Kindle, "Kindle
  Store" list). The rule compares each book only with itself.
