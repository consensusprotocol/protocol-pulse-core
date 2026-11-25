"""rising_star_candidate_v1 (core/book_signal_rules.py): the frozen constants, the rule's edges,
observed-rows-only behaviour, the 6 historical C6 episodes, and the prospective evaluator.

fixtures/rising_history_observed.json is compact_history() of the recovered collector history
(~/book_terminal_work/recovery/history_labeled.jsonl, 3,360 rows, not committed): every
observed rank of the 12 books that have one, every carried-forward row, and the IDs that only
ever had a placeholder. When the full file is on this machine, a test checks the fixture
against it and runs the rule on the full file too.

No network. Run: python3 -m pytest -q tests/books/ -p no:cacheprovider
"""
import json
import socket
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'rising_history_observed.json'
FULL_HISTORY = Path.home() / 'book_terminal_work' / 'recovery' / 'history_labeled.jsonl'
BACKTEST_SUMMARY = Path.home() / 'book_terminal_work' / 'rising_backtest' / 'summary.json'
SCRIPT = ROOT / 'scripts' / 'books' / 'evaluate_rising_star_prospective.py'
sys.path.append(str(ROOT / 'core'))

import book_signal_rules as rules  # noqa: E402

# summary.json, "C6_C4_persist3_rank_le_150k" -> "examples": all 6 episodes (asin, first day,
# improvement rounded to 2 places, reversed within 9 days; None = no window to judge).
C6_EPISODES = [
    ['0684832720', '2026-07-07', 0.5, False],
    ['0684832720', '2026-08-20', 0.6, False],
    ['1098150090', '2026-05-01', 0.45, False],
    ['1098150090', '2026-10-22', 0.5, False],
    ['1999257405', '2026-11-24', 0.46, None],
    ['B0DVTCVX8J', '2026-08-09', 0.44, False],
]
D0 = date(2026, 1, 1)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError('network access attempted in a book terminal test')
    monkeypatch.setattr(socket.socket, 'connect', refuse)
    monkeypatch.setattr(socket.socket, 'connect_ex', refuse)
    monkeypatch.setattr(socket, 'getaddrinfo', refuse)


def run_day(row):
    return date.fromisoformat(row['run_day'])


def compact_history(rows):
    """The fixture form of a labeled history: per book, one rank or None per day for the
    observations, [day index, rank] pairs for carried-forward rows, and the placeholder-only IDs."""
    days = sorted({row['run_day'] for row in rows})
    first, last = date.fromisoformat(days[0]), date.fromisoformat(days[-1])
    n = (last - first).days + 1
    observed, carried = {}, {}
    for row in rows:
        i = (run_day(row) - first).days
        if rules.is_observation(row):
            observed.setdefault(row['asin'], [None] * n)[i] = row['bsr']
        elif row['label'] == 'carried_forward':
            carried.setdefault(row['asin'], []).append([i, row['bsr']])
    seed_only = sorted({row['asin'] for row in rows} - set(observed))
    return {'first_day': first.isoformat(), 'last_day': last.isoformat(),
            'observed': dict(sorted(observed.items())),
            'carried_forward': {a: sorted(v) for a, v in sorted(carried.items())},
            'placeholder_only_ids': seed_only}


def fixture_rows(doc):
    """History rows (recovery format) rebuilt from the fixture: observed plus carried-forward."""
    first = date.fromisoformat(doc['first_day'])
    rows = []
    for asin, ranks in doc['observed'].items():
        rows += [{'asin': asin, 'bsr': r, 'run_day': (first + timedelta(days=i)).isoformat(), 'label': 'observed'}
                 for i, r in enumerate(ranks) if r is not None]
    for asin, pairs in doc['carried_forward'].items():
        rows += [{'asin': asin, 'bsr': r, 'run_day': (first + timedelta(days=i)).isoformat(), 'label': 'carried_forward'}
                 for i, r in pairs]
    return rows


def all_episodes(series_by_book):
    days = rules.evaluation_days(series_by_book)
    last = days[-1]
    found = []
    for asin, series in series_by_book.items():
        for ep in rules.episodes(series, days):
            verdict, _, _ = rules.outcome(series, date.fromisoformat(ep['day']), ep['prior_median'], 9, last)
            found.append([asin, ep['day'], round(ep['improvement'], 2),
                          {'held': False, 'reversed': True}.get(verdict)])
    return sorted(found)


@pytest.fixture(scope='module')
def history():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


# ── The frozen rule ──────────────────────────────────────────────────────────

def test_rule_constants_are_frozen():
    assert dict(rules.RISING_STAR_RULE) == {
        'name': 'rising_star_candidate_v1', 'frozen': '2026-11-25', 'median_window_days': 14,
        'min_improvement': 0.40, 'min_observed_per_window': 10, 'max_current_median_rank': 150000,
        'persistence_days': 3, 'status': 'provisional'}
    with pytest.raises(TypeError):
        rules.RISING_STAR_RULE['min_improvement'] = 0.3
    assert rules.PUBLISHING_ENABLED is False


def climb(prior, current, days=28, gaps=()):
    """A series of `days` days ending on D0 + days - 1: prior rank for the first half, current for the rest."""
    return {D0 + timedelta(days=i): (prior if i < days - 14 else current) for i in range(days) if i not in gaps}


@pytest.mark.parametrize('prior, current, met', [
    (100000, 60000, True),      # exactly 40% better
    (100000, 60001, False),     # 39.999%
    (250000, 150000, True),     # current median exactly at the cap
    (250001, 150001, False),    # 40% better, but above the cap
])
def test_condition_threshold_and_cap(prior, current, met):
    series = climb(prior, current)
    assert rules.condition(series, D0 + timedelta(days=27))['met'] is met


@pytest.mark.parametrize('gaps, evaluable', [
    ((0, 1, 2, 3), True),           # 10 observed days in the prior window: enough
    ((0, 1, 2, 3, 4), False),       # 9: not evaluable
    ((14, 15, 16, 17), True),       # 10 in the current window
    ((14, 15, 16, 17, 18), False),  # 9
])
def test_condition_needs_ten_observed_days_per_window(gaps, evaluable):
    result = rules.condition(climb(100000, 50000, gaps=gaps), D0 + timedelta(days=27))
    assert (result['improvement'] is not None) is evaluable
    assert result['met'] is evaluable


def test_qualifies_only_after_three_consecutive_days():
    # Rank 100,000 on days 0-13, then 50,000. The prior window (14 days ending 14 days back) first
    # holds 10 observed days on day 23, so the condition first holds on day 23 and the rule on day 25.
    series = {D0 + timedelta(days=i): (100000 if i < 14 else 50000) for i in range(31)}
    met = {i: rules.condition(series, D0 + timedelta(days=i))['met'] for i in range(31)}
    first = min(i for i, m in met.items() if m)
    assert first == 23 and all(met[i] for i in range(23, 31))
    assert rules.evaluate(series, D0 + timedelta(days=first + 1))['qualifies'] is False
    result = rules.evaluate(series, D0 + timedelta(days=first + 2))
    assert result['qualifies'] is True and result['persistence'] == [True, True, True]
    del series[D0 + timedelta(days=first + 1)]  # a missing day does not break persistence by itself
    assert rules.evaluate(series, D0 + timedelta(days=first + 2))['qualifies'] is True


def test_only_observations_enter_a_window():
    rows = ([{'asin': 'X', 'bsr': 100000, 'run_day': (D0 + timedelta(days=i)).isoformat(), 'label': 'observed'}
             for i in range(14)]
            + [{'asin': 'X', 'bsr': 50000, 'run_day': (D0 + timedelta(days=i)).isoformat(), 'label': 'observed'}
               for i in range(14, 23)]                                  # 9 observed days in the current window
            + [{'asin': 'X', 'bsr': 50000, 'run_day': (D0 + timedelta(days=i)).isoformat(), 'label': 'carried_forward'}
               for i in range(23, 28)]                                  # carried: never an observation
            + [{'asin': 'X', 'bsr': 50000, 'run_day': (D0 + timedelta(days=27)).isoformat(), 'label': 'seed_default'}])
    series = rules.observed_series(rows, run_day)['X']
    assert len(series) == 23 and max(series) == D0 + timedelta(days=22)
    assert rules.condition(series, D0 + timedelta(days=27))['improvement'] is None   # 9 < 10: not evaluable
    counted = rules.observed_series([dict(r, label='observed') for r in rows], run_day)['X']
    assert rules.condition(counted, D0 + timedelta(days=27))['met'] is True          # what counting them would claim


@pytest.mark.parametrize('row, counted', [
    ({'asin': 'X', 'bsr': 1234, 'status': 'ok'}, True),          # the collector's history format
    ({'asin': 'X', 'bsr': 1234, 'status': 'error'}, False),
    ({'asin': 'X', 'bsr': None, 'status': 'ok'}, False),
    ({'asin': 'X', 'bsr': 0, 'label': 'observed'}, False),
    ({'asin': 'X', 'bsr': True, 'label': 'observed'}, False),
    ({'asin': 'X', 'bsr': '1234', 'label': 'observed'}, False),
    ({'asin': 'X', 'bsr': 1234, 'label': 'carried_forward'}, False),
])
def test_is_observation(row, counted):
    assert rules.is_observation(row) is counted


def test_outcome_verdicts():
    series = {D0 + timedelta(days=i): r for i, r in [(5, 40000), (7, 42000), (9, 41000), (24, 99000), (26, 120000)]}
    assert rules.outcome(series, D0, 100000, 9, D0 + timedelta(days=40)) == ('held', 41000, 3)
    assert rules.outcome(series, D0, 100000, 28, D0 + timedelta(days=40)) == ('reversed', 109500.0, 2)
    assert rules.outcome(series, D0, 100000, 28, D0 + timedelta(days=27))[0] == 'pending'
    assert rules.outcome({D0 + timedelta(days=9): 1}, D0, 100000, 9, D0 + timedelta(days=40)) == ('not evaluable', None, 1)


# ── The historical episodes ──────────────────────────────────────────────────

def test_reproduces_exactly_the_six_c6_episodes(history):
    series = rules.observed_series(fixture_rows(history), run_day)
    assert len(series) == 12
    assert all_episodes(series) == sorted(C6_EPISODES)


def test_counting_carried_forward_rows_would_change_the_episodes(history):
    rows = [dict(r, label='observed') for r in fixture_rows(history)]
    assert all_episodes(rules.observed_series(rows, run_day)) != sorted(C6_EPISODES)


def test_fixture_matches_the_full_history_and_the_backtest_summary(history):
    if not FULL_HISTORY.is_file():
        pytest.skip(f'{FULL_HISTORY} is not on this machine')
    rows = [json.loads(line) for line in FULL_HISTORY.read_text(encoding='utf-8').splitlines()]
    assert compact_history(rows) == {k: history[k] for k in ('first_day', 'last_day', 'observed', 'carried_forward',
                                                             'placeholder_only_ids')}
    assert all_episodes(rules.observed_series(rows, run_day)) == sorted(C6_EPISODES)
    if BACKTEST_SUMMARY.is_file():
        c6 = json.loads(BACKTEST_SUMMARY.read_text(encoding='utf-8'))['C6_C4_persist3_rank_le_150k']
        assert c6['episodes'] == 6 and sorted(c6['examples']) == sorted(C6_EPISODES)


# ── Prospective evaluator (scripts/books/evaluate_rising_star_prospective.py) ──

def run_script(tmp_path, rows, *args):
    src = tmp_path / 'history.jsonl'
    src.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    out = tmp_path / 'report.json'
    done = subprocess.run([sys.executable, str(SCRIPT), str(src), '--out', str(out), *args],
                          capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    return json.loads(out.read_text(encoding='utf-8'))


def test_prospective_report_counts_only_episodes_from_the_freeze_on(tmp_path, history):
    report = run_script(tmp_path, fixture_rows(history))
    assert report['rule'] == dict(rules.RISING_STAR_RULE) and report['publishing_enabled'] is False
    assert report['since'] == '2026-11-25' and report['input']['last_day'] == '2026-11-24'
    assert report['episodes'] == [] and report['in_sample_episodes_before_since'] == 6
    assert report['input']['observed_rows'] == sum(1 for r in fixture_rows(history) if r['label'] == 'observed')

    report = run_script(tmp_path, fixture_rows(history), '--since', '2026-11-24')
    [ep] = report['episodes']
    assert (ep['asin'], ep['title'], ep['first_day'], round(ep['improvement'], 2)) == (
        '1999257405', 'The Price of Tomorrow', '2026-11-24', 0.46)
    assert ep['outcome_9d']['verdict'] == ep['outcome_28d']['verdict'] == 'pending'


def test_prospective_report_reads_the_collector_history_format(tmp_path):
    # Two runs a day apart in the collector's own format; ts in UTC, the day is New York's date.
    rows = []
    for i in range(31):
        day = D0 + timedelta(days=i)
        ts = f'{day.isoformat()}T11:17:00+00:00'
        rows.append({'asin': 'B0DVTCVX8J', 'bsr': 100000 if i < 14 else 50000, 'ts': ts, 'status': 'ok',
                     'error': None, 'category': 'Books', 'marketplace': 'US'})
        rows.append({'asin': '0684832720', 'bsr': None, 'ts': ts, 'status': 'error', 'error': 'HTTP 503',
                     'category': None, 'marketplace': 'US'})
    report = run_script(tmp_path, rows, '--since', D0.isoformat())
    assert report['input']['observed_rows'] == 31 and report['input']['books_observed'] == 1
    [ep] = report['episodes']
    assert ep['asin'] == 'B0DVTCVX8J' and ep['title'] == 'The Big Print' and ep['current_median'] == 50000
