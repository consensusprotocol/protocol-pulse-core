#!/usr/bin/env python3
"""Prospective evaluation of rising_star_candidate_v1 (core/book_signal_rules.py). Not scheduled.

Reads a labeled history file (JSON lines) and writes a JSON report of the rule's episodes whose
first qualifying day is on or after --since. The default is the freeze date, 2026-11-25: the rule
was chosen on observations through 2026-11-24, so only later days are new to it.

Rows it reads:
  recovered history  {"asin", "bsr", "run_day", "label"}  label 'observed' counts
  collector history  {"asin", "bsr", "ts", "status"}      status 'ok' counts; the day is the date
                                                          of ts in New York (the collector runs 06:17 ET)
Nothing else is an observation: carried-forward and placeholder rows, error rows and null ranks
never enter a window.

Each episode lists the Amazon ID, the registry title (when the ID is in the registry), the first
qualifying day, the improvement, both 14-day medians with their observed-day counts, and
outcome_9d / outcome_28d: 'held' or 'reversed' (median of the observed ranks on the 5 days
ending 9 / 28 days after the first day, at least 2 of them, against the prior median),
'pending' while that window is still open, 'not evaluable' with fewer observations. A run that
began before --since is not a new episode.

No network, no publishing; every number of the rule comes from RISING_STAR_RULE.
Usage: python3 scripts/books/evaluate_rising_star_prospective.py HISTORY.jsonl --out REPORT.json [--since YYYY-MM-DD]
"""
import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'core'))
import book_signal_rules as rules  # noqa: E402
import books_registry  # noqa: E402

NEW_YORK = ZoneInfo('America/New_York')


def day_of(row):
    if row.get('run_day'):
        return date.fromisoformat(row['run_day'])
    ts = datetime.fromisoformat(row['ts'])
    return (ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)).astimezone(NEW_YORK).date()


def read_rows(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError as e:
                    raise SystemExit(f'{path}:{n}: not a JSON line ({e})')
    return rows


def build_report(rows, since, titles, source):
    series = rules.observed_series(rows, day_of)
    days = rules.evaluation_days(series)
    last = days[-1] if days else None
    found, before = [], 0
    for asin, book_series in sorted(series.items()):
        for ep in rules.episodes(book_series, days):
            first = date.fromisoformat(ep['day'])
            if first < since:
                before += 1
                continue
            entry = {'asin': asin, 'title': titles.get(asin), 'first_day': ep['day'], 'improvement': ep['improvement'],
                     'current_median': ep['current_median'], 'prior_median': ep['prior_median'],
                     'observed_current': ep['observed_current'], 'observed_prior': ep['observed_prior']}
            for horizon in rules.OUTCOME_HORIZONS:
                verdict, window_median, observed = rules.outcome(book_series, first, ep['prior_median'], horizon, last)
                entry[f'outcome_{horizon}d'] = {'verdict': verdict, 'window_median': window_median,
                                                'window_observed': observed}
            found.append(entry)
    found.sort(key=lambda e: (e['first_day'], e['asin']))
    report = {
        'rule': dict(rules.RISING_STAR_RULE),
        'publishing_enabled': rules.PUBLISHING_ENABLED,
        'since': since.isoformat(),
        'generated_at': datetime.now(NEW_YORK).strftime('%Y-%m-%d %H:%M %Z'),
        'input': {'path': str(source), 'rows': len(rows), 'observed_rows': sum(map(rules.is_observation, rows)),
                  'books_observed': len(series), 'first_day': days[0].isoformat() if days else None,
                  'last_day': last.isoformat() if last else None},
        'episodes': found,
        'in_sample_episodes_before_since': before,
    }
    if since < date.fromisoformat(rules.RISING_STAR_RULE['frozen']):
        report['note'] = ('--since is before the freeze date: episodes before '
                          f"{rules.RISING_STAR_RULE['frozen']} are in-sample, not a prospective result")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('history', type=Path, help='labeled history, JSON lines')
    parser.add_argument('--out', type=Path, required=True, help='report path (JSON)')
    parser.add_argument('--since', type=date.fromisoformat, default=date.fromisoformat(rules.RISING_STAR_RULE['frozen']),
                        help='first day that counts (default: the freeze date)')
    args = parser.parse_args(argv)
    titles = {b['amazon_id']: b['title'] for b in books_registry.load_registry()}
    report = build_report(read_rows(args.history), args.since, titles, args.history)
    args.out.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print(f"{len(report['episodes'])} episode(s) since {report['since']} "
          f"({report['input']['observed_rows']} observed rows, last day {report['input']['last_day']}); wrote {args.out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
