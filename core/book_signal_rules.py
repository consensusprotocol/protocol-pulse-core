"""Book Signal rules: frozen, provisional candidates. Nothing here publishes anything.

RISING_STAR_RULE (rising_star_candidate_v1, frozen 2026-11-25, status provisional) is the C6
variant of the Apr 1 - Nov 24 2026 backtest; docs/books/RISING_STAR_CANDIDATE.md has its
history, its selection and the prospective plan. For one book on one day:

  current median  median of the book's observed ranks on the 14 calendar days ending on the day
  prior median    median of its observed ranks on the 14 calendar days before those
  evaluable       each window holds at least 10 observed days
  condition       current median <= 150,000 and (prior - current) / prior >= 0.40
                  (a lower rank number is better, so a positive improvement is a climb)
  qualifies       the condition holds on the day and on each of the 2 calendar days before it

Only observed ranks count. observed_series() keeps a history row only when it is an observation
(label 'observed' in the recovered history, status 'ok' in the collector's history) with a
positive integer rank: a carried-forward or placeholder number never enters a window, and a
missing day stays missing.

Episodes: walking a list of evaluation days in order (the backtest used every day on which any
tracked book had an observation), a run is a stretch of consecutive qualifying entries; its
first day is the episode. An outcome compares the median of the observed ranks on the 5 days
ending `horizon` days after the episode (at least 2 of them) with the prior median: at or above
it, the whole gain was given back ('reversed'); below it, 'held'. The backtest's reversal check
is the 9-day horizon.

Stdlib only and free of I/O: tests/books and scripts/books/evaluate_rising_star_prospective.py
share these functions.
"""
from datetime import timedelta
from statistics import median
from types import MappingProxyType

RISING_STAR_RULE = MappingProxyType({
    'name': 'rising_star_candidate_v1',
    'frozen': '2026-11-25',
    'median_window_days': 14,
    'min_improvement': 0.40,
    'min_observed_per_window': 10,
    'max_current_median_rank': 150000,
    'persistence_days': 3,
    'status': 'provisional',
})
PUBLISHING_ENABLED = False      # no surface shows a rising star from observed data
OUTCOME_WINDOW_DAYS = 5         # the outcome median spans days horizon-4 .. horizon
OUTCOME_MIN_OBSERVED = 2
OUTCOME_HORIZONS = (9, 28)

_DAY = timedelta(days=1)


def _rank(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def is_observation(row):
    """True for a history row that is a real observation with a positive integer rank."""
    label = row.get('label')
    if label is None and 'status' in row:  # the collector's history: status 'ok' or 'error'
        label = 'observed' if row['status'] == 'ok' else row['status']
    return label == 'observed' and _rank(row.get('bsr'))


def observed_series(rows, day_of):
    """{asin: {date: rank}} of the observations among rows; day_of(row) gives the row's date.

    Rows that are not observations are dropped. Two observations of one book on one day keep
    the later row (file order), as a later run of the same day would.
    """
    series = {}
    for row in rows:
        if is_observation(row):
            series.setdefault(row['asin'], {})[day_of(row)] = row['bsr']
    return series


def evaluation_days(series_by_book):
    """Every day on which at least one book has an observation, in order."""
    return sorted({d for series in series_by_book.values() for d in series})


def _window(series, first, last):
    values, d = [], first
    while d <= last:
        if _rank(series.get(d)):
            values.append(series[d])
        d += _DAY
    return values


def condition(series, day, rule=RISING_STAR_RULE):
    """The one-day test on `day`, before persistence. series: {date: rank} of observations."""
    w = rule['median_window_days']
    current = _window(series, day - (w - 1) * _DAY, day)
    prior = _window(series, day - (2 * w - 1) * _DAY, day - w * _DAY)
    out = {'day': day.isoformat(), 'observed_current': len(current), 'observed_prior': len(prior),
           'current_median': median(current) if current else None,
           'prior_median': median(prior) if prior else None, 'improvement': None, 'met': False}
    need = rule['min_observed_per_window']
    if len(current) < need or len(prior) < need:
        out['reason'] = 'not evaluable: fewer than %d observed days in a window' % need
        return out
    now, base = out['current_median'], out['prior_median']
    out['improvement'] = (base - now) / base
    if now > rule['max_current_median_rank']:
        out['reason'] = 'current median above the rank cap'
    elif out['improvement'] >= rule['min_improvement']:
        out['met'], out['reason'] = True, 'met'
    else:
        out['reason'] = 'improvement below the threshold'
    return out


def evaluate(series, day, rule=RISING_STAR_RULE):
    """rising_star_candidate_v1 for one book on `day` (a date), from its observations only.

    Returns the day's condition() result plus 'qualifies' (the condition holds on the day and on
    each of the persistence_days - 1 calendar days before it) and 'persistence' (those days'
    'met' flags, newest first).
    """
    checks = [condition(series, day - i * _DAY, rule) for i in range(rule['persistence_days'])]
    return dict(checks[0], qualifies=all(c['met'] for c in checks), persistence=[c['met'] for c in checks])


def episodes(series, days, rule=RISING_STAR_RULE):
    """evaluate() results for the first day of each run of qualifying entries of `days`."""
    found, in_run = [], False
    for day in days:
        result = evaluate(series, day, rule)
        if result['qualifies'] and not in_run:
            found.append(result)
        in_run = result['qualifies']
    return found


def outcome(series, episode_day, prior_median, horizon, last_day):
    """'held', 'reversed', 'pending' (the window ends after last_day) or 'not evaluable'.

    The window is the OUTCOME_WINDOW_DAYS days ending `horizon` days after the episode day;
    it needs OUTCOME_MIN_OBSERVED observations. Returns (verdict, window median or None, count).
    """
    end = episode_day + horizon * _DAY
    if end > last_day:
        return 'pending', None, None
    values = _window(series, end - (OUTCOME_WINDOW_DAYS - 1) * _DAY, end)
    if len(values) < OUTCOME_MIN_OBSERVED:
        return 'not evaluable', None, len(values)
    later = median(values)
    return ('reversed' if later >= prior_median else 'held'), later, len(values)
