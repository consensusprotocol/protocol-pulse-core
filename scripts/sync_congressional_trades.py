#!/usr/bin/env python3
"""
sync_ihx_etf.py - IHX: Institutional Insider Heat from Bitcoin ETF flows.
Tracks IBIT/FBTC/ARKB/BITB daily price/volume as proxy for institutional accumulation.
Cron: */30 * * * * cd /home/ultron/protocol_pulse && python3 scripts/sync_ihx_etf.py
"""
import json, os, tempfile, urllib.request, logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [IHX] %(message)s')
log = logging.getLogger(__name__)
OUT = Path('/home/ultron/protocol_pulse/data/congressional_trades.json')

ETFS = {
    'IBIT': 'BlackRock',
    'FBTC': 'Fidelity',
    'ARKB': 'ARK Invest',
    'BITB': 'Bitwise',
}

def fetch_etf(ticker):
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/' + ticker + '?interval=1d&range=5d'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=8) as r:
        d = json.loads(r.read())
    meta = d['chart']['result'][0]['meta']
    price = float(meta.get('regularMarketPrice', 0) or 0)
    prev = float(meta.get('chartPreviousClose', price) or price)
    chg_pct = round((price - prev) / prev * 100, 2) if prev else 0
    vols = d['chart']['result'][0].get('indicators', {}).get('quote', [{}])[0].get('volume', [])
    avg_vol = round(sum(v for v in vols if v) / max(1, len([v for v in vols if v])))
    return {'ticker': ticker, 'issuer': ETFS[ticker], 'price': price, 'chg_pct': chg_pct, 'avg_vol_5d': avg_vol}

def compute_ihx(etf_data):
    if not etf_data:
        return {'score': 50, 'direction': 'neutral', 'interpretation': 'ETF data unavailable.', 'etfs': []}
    pos = sum(1 for e in etf_data if e['chg_pct'] > 0.5)
    neg = sum(1 for e in etf_data if e['chg_pct'] < -0.5)
    flat = len(etf_data) - pos - neg
    total = len(etf_data)
    avg_chg = sum(e['chg_pct'] for e in etf_data) / total if total else 0
    # Score: base 50, +/- based on avg change and directional agreement
    score = round(max(0, min(100, 50 + avg_chg * 6)))
    if score >= 65:
        direction = 'bullish'
        interpretation = (str(pos) + '/' + str(total) + ' Bitcoin ETFs gaining (avg ' + str(round(avg_chg,2)) +
                         '%) — institutional accumulation signal.')
    elif score <= 35:
        direction = 'bearish'
        interpretation = (str(neg) + '/' + str(total) + ' Bitcoin ETFs declining (avg ' + str(round(avg_chg,2)) +
                         '%) — institutional distribution signal.')
    else:
        direction = 'neutral'
        interpretation = ('Bitcoin ETF flows mixed (avg ' + str(round(avg_chg,2)) +
                         '%) — no clear institutional conviction.')
    return {'score': score, 'direction': direction, 'interpretation': interpretation, 'etfs': etf_data,
            'avg_chg_pct': round(avg_chg, 2), 'bullish_count': pos, 'bearish_count': neg}

def main():
    log.info('Fetching Bitcoin ETF data for IHX...')
    etf_data = []
    for ticker in ETFS:
        try:
            data = fetch_etf(ticker)
            etf_data.append(data)
            log.info(ticker + ': ' + str(data['price']) + ' (' + str(data['chg_pct']) + '% chg)')
        except Exception as e:
            log.warning('Failed ' + ticker + ': ' + str(e))

    ihx = compute_ihx(etf_data)
    log.info('IHX: ' + str(ihx['score']) + ' (' + ihx['direction'] + ') - ' + ihx['interpretation'])

    payload = {
        'last_updated': datetime.now(timezone.utc).isoformat(),
        'ihx': ihx,
        'source': 'bitcoin_etf_flows',
        'etf_count': len(etf_data),
    }
    fd, tmp = tempfile.mkstemp(dir=str(OUT.parent), suffix='.tmp')
    with os.fdopen(fd, 'w') as f:
        json.dump(payload, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, str(OUT))
    log.info('Saved to ' + str(OUT))

if __name__ == '__main__':
    main()
