"""
X Spaces Sentiment Service — computes x_spaces_sentiment score 0-100 from
live_signals.json + chunk transcripts, updates sentiment.json with x_spaces component.

Weights: YouTube=50%, X_Spaces=30%, topic_velocity=20%
Runs every 5 minutes via scheduler.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

BASE_PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LIVE_SIGNALS_PATH = os.path.join(BASE_PROJECT, 'video_pipeline_v3', 'data', 'intelligence', 'live_signals.json')
SENTIMENT_PATH = os.path.join(BASE_PROJECT, 'video_pipeline_v3', 'data', 'intelligence', 'sentiment.json')
SPACES_DATA_DIR = os.path.join(BASE_PROJECT, 'video_pipeline_v3', 'data', 'spaces')
SCRAPER_CACHE_DIR = os.path.join(BASE_PROJECT, 'x_spaces_scraper', 'cache')

BULLISH_WORDS = [
    "bullish", "moon", "pump", "rally", "accumulate", "buy", "stack",
    "surge", "breakout", "green", "higher", "ath", "adoption", "inflows",
    "institutional", "approval", "confirmed",
]
BEARISH_WORDS = [
    "bearish", "crash", "dump", "sell", "fear", "down", "collapse",
    "red", "lower", "capitulation", "panic", "ban", "outflows", "reject",
]

LEGENDARY_HANDLES = [
    "saylor", "lopp", "natbrunell", "martybent", "prestonpysh", "odell",
    "jack", "gladstein", "stephanlivera", "petermccormack", "lynaldencontact",
    "apompliano",
]


class SpacesSentimentService:
    def get_live_spaces(self) -> List[Dict]:
        """Return x_spaces entries from live_signals.json updated within 6 hours."""
        if not os.path.exists(LIVE_SIGNALS_PATH):
            return []
        try:
            with open(LIVE_SIGNALS_PATH) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
        results = []
        for stream in data.get('live_streams', []):
            if stream.get('source') != 'x_spaces':
                continue
            last_updated = stream.get('last_updated') or stream.get('started_at', '')
            try:
                ts = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                if ts >= cutoff:
                    results.append(stream)
            except (ValueError, AttributeError):
                continue
        return results

    def get_recent_chunks(self) -> List[str]:
        """Scan spaces data and scraper cache for recent chunk text."""
        chunks = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=6)

        for search_dir in [SPACES_DATA_DIR, SCRAPER_CACHE_DIR]:
            if not os.path.isdir(search_dir):
                continue
            for root, dirs, files in os.walk(search_dir):
                for fname in files:
                    if not fname.endswith('.jsonl'):
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(fpath), tz=timezone.utc)
                        if mtime < cutoff:
                            continue
                        with open(fpath) as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    entry = json.loads(line)
                                    text = entry.get('text', '') or entry.get('chunk_text', '') or ''
                                    if text:
                                        chunks.append(text)
                                except json.JSONDecodeError:
                                    continue
                    except OSError:
                        continue
        return chunks

    def compute_sentiment_score(self, live_spaces: List[Dict], chunks: List[str]) -> Dict:
        """Compute x_spaces_sentiment 0-100 with label, metadata."""
        if not live_spaces and not chunks:
            return {
                'score': 50,
                'label': 'NEUTRAL',
                'active_count': 0,
                'top_host': None,
                'top_quote': '',
                'topics': [],
                'confidence': 'LOW',
                'computed_at': datetime.now(timezone.utc).isoformat(),
            }

        # Average sentiment from live_signals entries
        sentiment_scores = [s.get('current_sentiment', 50) for s in live_spaces]
        avg_signal = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 50

        # Keyword analysis on chunks
        all_text = ' '.join(chunks).lower()
        bull_count = sum(1 for w in BULLISH_WORDS if w in all_text)
        bear_count = sum(1 for w in BEARISH_WORDS if w in all_text)
        if bull_count > bear_count:
            keyword_score = 50 + min((bull_count - bear_count) * 5, 30)
        elif bear_count > bull_count:
            keyword_score = 50 - min((bear_count - bull_count) * 5, 30)
        else:
            keyword_score = 50

        # Blend: 60% signal avg + 40% keyword
        base_score = avg_signal * 0.6 + keyword_score * 0.4

        # Legendary handle bonus (+10)
        legendary_bonus = 0
        for space in live_spaces:
            channel = (space.get('channel', '') or '').lower().lstrip('@')
            if any(lh in channel for lh in LEGENDARY_HANDLES):
                legendary_bonus = 10
                break

        # Recency bonus (+5 if any space started within 1h)
        recency_bonus = 0
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        for space in live_spaces:
            started = space.get('started_at', '')
            try:
                ts = datetime.fromisoformat(started.replace('Z', '+00:00'))
                if ts >= one_hour_ago:
                    recency_bonus = 5
                    break
            except (ValueError, AttributeError):
                continue

        score = int(min(100, max(0, base_score + legendary_bonus + recency_bonus)))

        # Label
        if score >= 65:
            label = 'BULLISH'
        elif score <= 35:
            label = 'BEARISH'
        else:
            label = 'NEUTRAL'

        # Top host
        top_host = None
        if live_spaces:
            top_host = live_spaces[0].get('channel', '').lstrip('@')

        # Top quote (best chunk <= 200 chars)
        top_quote = ''
        for chunk in chunks:
            if 20 < len(chunk) <= 200:
                top_quote = chunk
                break
        if not top_quote and chunks:
            top_quote = chunks[0][:200]

        # Topics (union from all live spaces)
        topics = list(set(t for s in live_spaces for t in s.get('topics', [])))

        # Confidence
        active_count = len(live_spaces)
        if active_count >= 3 and len(chunks) >= 5:
            confidence = 'HIGH'
        elif active_count >= 1 or len(chunks) >= 2:
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'

        return {
            'score': score,
            'label': label,
            'active_count': active_count,
            'top_host': top_host,
            'top_quote': top_quote,
            'topics': topics,
            'confidence': confidence,
            'computed_at': datetime.now(timezone.utc).isoformat(),
        }

    def update_sentiment_json(self, result: Dict) -> None:
        """Write x_spaces_sentiment to sentiment.json, recompute overall with weights."""
        # Load existing
        if os.path.exists(SENTIMENT_PATH):
            try:
                with open(SENTIMENT_PATH) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                data = {}
        else:
            data = {}

        data.setdefault('data', {})
        data['data'].setdefault('overall', {})
        data['data'].setdefault('breakdown', {})
        data['data'].setdefault('historical', [])

        # Update x_spaces breakdown
        data['data']['breakdown']['x_spaces'] = {
            'score': result['score'],
            'label': result['label'],
            'active_count': result['active_count'],
            'top_host': result['top_host'],
            'top_quote': result['top_quote'],
            'topics': result['topics'],
            'confidence': result['confidence'],
            'driver': 'x_spaces live intel',
            'computed_at': result['computed_at'],
        }

        # Get component scores for weighted overall
        yt_score = data['data']['overall'].get('components', {}).get('youtube_sentiment', 50)
        xs_score = result['score']
        tv_score = data['data']['overall'].get('components', {}).get('topic_velocity_bullish_pct', 50)

        # Weighted: YouTube=50%, X_Spaces=30%, topic_velocity=20%
        overall_score = int(yt_score * 0.5 + xs_score * 0.3 + tv_score * 0.2)
        overall_score = max(0, min(100, overall_score))

        if overall_score >= 65:
            overall_label = 'bullish'
        elif overall_score <= 35:
            overall_label = 'bearish'
        else:
            overall_label = 'neutral'

        data['data']['overall']['score'] = overall_score
        data['data']['overall']['label'] = overall_label
        data['data']['overall'].setdefault('components', {})
        data['data']['overall']['components']['youtube_sentiment'] = yt_score
        data['data']['overall']['components']['x_spaces_sentiment'] = xs_score
        data['data']['overall']['components']['topic_velocity_bullish_pct'] = tv_score

        data['scan_time'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Atomic write
        os.makedirs(os.path.dirname(SENTIMENT_PATH), exist_ok=True)
        tmp = SENTIMENT_PATH + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, SENTIMENT_PATH)

    def run(self) -> Dict:
        """Full cycle: gather data, compute, update JSON, return result."""
        live_spaces = self.get_live_spaces()
        chunks = self.get_recent_chunks()
        result = self.compute_sentiment_score(live_spaces, chunks)
        self.update_sentiment_json(result)
        logger.info(f"X Spaces sentiment: score={result['score']} label={result['label']} active={result['active_count']}")
        return result


spaces_sentiment_service = SpacesSentimentService()
