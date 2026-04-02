You are executing a 3-hour autonomous build session. Read ALL of these before writing code:
1. PIPELINE_LAWS.md
2. ~/protocol_pulse/PRODUCTION_DESIGN_LAWS.md
3. ~/protocol_pulse/CONTENT_INTELLIGENCE_LAWS.md
4. ~/protocol_pulse/PULSE_TERMINAL_LAWS.md

This session builds the LIVE INTELLIGENCE SYSTEM — real-time capture and analysis of YouTube Live streams and X Spaces from partner channels. This is the competitive moat. Nobody else has this.

=== PHASE 1: LIVE_INTELLIGENCE_LAWS.md Gospel Doc ===

Create ~/protocol_pulse/LIVE_INTELLIGENCE_LAWS.md with comprehensive rules for:

1. YouTube Live Stream Detection + Capture:
   - Poll YouTube Data API or yt-dlp every 5 minutes for live streams from channels.yaml
   - When a partner channel goes live, capture audio stream in real-time
   - Use yt-dlp --live-from-start for YouTube live capture
   - Stream audio to Whisper in 30-second chunks (don't wait for stream to end)
   - Classify each chunk's topics and sentiment immediately
   - Update data/intelligence/live_signals.json with real-time data
   - Alert Terminal subscribers via WebSocket when live signal detected

2. X Spaces Detection + Capture:
   - Monitor partner accounts for active X Spaces (Twitter Spaces)
   - Use twspace-dl or yt-dlp for X Spaces audio capture
   - Same 30-second chunk processing pipeline as YouTube Live
   - X Spaces are the purest form of real-time unfiltered sentiment

3. Data Flow:
   Channel goes live → Detect (5 min poll) → Capture audio → 
   Whisper chunk (30s) → Claude classify → live_signals.json → 
   Terminal API (WebSocket push) → X post (commentary) → 
   Video pipeline (next episode references it)

4. Technical Architecture:
   - utils/live_monitor.py — main daemon
   - utils/live_capture.py — audio stream capture
   - utils/live_transcriber.py — Whisper chunked processing
   - utils/live_classifier.py — topic + sentiment classification
   - data/intelligence/live_signals.json — real-time output
   - Cron: */5 * * * * for live detection polling

5. Cost Management:
   - Whisper runs free on 4090 GPU
   - Claude API for classification: ~$0.01 per 30-second chunk
   - A typical 2-hour live stream = 240 chunks = ~$2.40 in Claude API
   - Only capture from Tier 1 + Tier 2 channels (not all 80)

6. Integration with existing systems:
   - Terminal API adds: GET /api/v2/terminal/live — current live streams + real-time topics
   - Video pipeline: daily_producer.py checks live_signals.json for hot topics
   - X posting: auto-commentary when live sentiment spikes

Commit: git add ~/protocol_pulse/LIVE_INTELLIGENCE_LAWS.md -m 'docs: LIVE_INTELLIGENCE_LAWS.md — real-time stream intelligence system'

=== PHASE 2: Build the Live Monitor ===

Create utils/live_monitor.py:

import subprocess, json, os, time, logging
from datetime import datetime

CHANNELS_FILE = 'channels.yaml'
LIVE_SIGNALS = 'data/intelligence/live_signals.json'

def detect_live_streams():
    '''Check all Tier 1+2 channels for active live streams.'''
    import yaml
    with open(CHANNELS_FILE) as f:
        config = yaml.safe_load(f)
    
    live_streams = []
    channels = config.get('channels', []) + config.get('mainstream', [])
    
    for ch in channels:
        if ch.get('priority', 99) > 2:
            continue  # Only Tier 1+2
        url = ch.get('url', '')
        name = ch.get('name', '')
        try:
            # Check for live content
            result = subprocess.run(
                ['yt-dlp', '--flat-playlist', '--match-filter', 'is_live',
                 '--print', '%(id)s|%(title)s|%(uploader)s',
                 url + '/streams', '--max-downloads', '1'],
                capture_output=True, text=True, timeout=15
            )
            if result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 2:
                    live_streams.append({
                        'video_id': parts[0],
                        'title': parts[1],
                        'channel': name,
                        'url': f'https://www.youtube.com/watch?v={parts[0]}',
                        'detected_at': datetime.now().isoformat()
                    })
        except Exception as e:
            logging.warning(f'Live check failed for {name}: {e}')
    
    return live_streams

def capture_live_audio(video_url, output_dir):
    '''Capture live stream audio. Returns path to audio file.'''
    os.makedirs(output_dir, exist_ok=True)
    output = os.path.join(output_dir, 'live_audio.m4a')
    
    proc = subprocess.Popen(
        ['yt-dlp', '-f', 'bestaudio', '--live-from-start',
         '-o', output, video_url],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return proc, output

def transcribe_chunk(audio_path, start_time, duration=30):
    '''Transcribe a 30-second chunk using Whisper.'''
    import whisper
    model = whisper.load_model('base', device='cuda')
    # Extract chunk
    chunk_path = audio_path + f'.chunk_{start_time}.wav'
    subprocess.run([
        'ffmpeg', '-ss', str(start_time), '-t', str(duration),
        '-i', audio_path, '-ar', '16000', '-ac', '1', chunk_path,
        '-y', '-loglevel', 'quiet'
    ])
    if os.path.exists(chunk_path):
        result = model.transcribe(chunk_path)
        os.remove(chunk_path)
        return result.get('text', '')
    return ''

def classify_chunk(text, channel):
    '''Quick topic + sentiment classification.'''
    # Simple keyword-based classification (fast, no API cost)
    topics = []
    sentiment_score = 50  # neutral default
    
    keywords = {
        'mining': ['mining', 'hashrate', 'hash rate', 'difficulty', 'miner'],
        'ETF': ['etf', 'blackrock', 'fidelity', 'grayscale', 'inflows', 'outflows'],
        'price': ['price', 'rally', 'dump', 'bull', 'bear', 'ath', 'all-time'],
        'regulation': ['regulation', 'sec', 'congress', 'ban', 'legislation'],
        'self-custody': ['custody', 'keys', 'wallet', 'cold storage', 'not your keys'],
        'lightning': ['lightning', 'layer 2', 'l2', 'payments'],
        'macro': ['fed', 'inflation', 'interest rate', 'dollar', 'treasury'],
    }
    
    text_lower = text.lower()
    for topic, kws in keywords.items():
        if any(kw in text_lower for kw in kws):
            topics.append(topic)
    
    # Simple sentiment
    bullish_words = ['bullish', 'moon', 'pump', 'rally', 'accumulate', 'buy', 'stack', 'up']
    bearish_words = ['bearish', 'crash', 'dump', 'sell', 'fear', 'down', 'collapse']
    
    bull_count = sum(1 for w in bullish_words if w in text_lower)
    bear_count = sum(1 for w in bearish_words if w in text_lower)
    
    if bull_count > bear_count:
        sentiment_score = 50 + min(bull_count * 10, 40)
    elif bear_count > bull_count:
        sentiment_score = 50 - min(bear_count * 10, 40)
    
    return topics, sentiment_score

def update_live_signals(stream_info, topics, sentiment, transcript_chunk):
    '''Update live_signals.json with new data.'''
    signals = {'live_streams': [], 'updated_at': datetime.now().isoformat()}
    if os.path.exists(LIVE_SIGNALS):
        with open(LIVE_SIGNALS) as f:
            signals = json.load(f)
    
    # Find or create stream entry
    stream_entry = None
    for s in signals.get('live_streams', []):
        if s.get('video_id') == stream_info.get('video_id'):
            stream_entry = s
            break
    
    if not stream_entry:
        stream_entry = {
            'video_id': stream_info['video_id'],
            'title': stream_info['title'],
            'channel': stream_info['channel'],
            'started_at': stream_info['detected_at'],
            'topics': [],
            'sentiment_history': [],
            'transcript_chunks': []
        }
        signals.setdefault('live_streams', []).append(stream_entry)
    
    # Update
    stream_entry['topics'] = list(set(stream_entry.get('topics', []) + topics))
    stream_entry['sentiment_history'].append({
        'time': datetime.now().isoformat(),
        'score': sentiment
    })
    stream_entry['transcript_chunks'].append(transcript_chunk[:200])  # Keep it small
    stream_entry['last_updated'] = datetime.now().isoformat()
    
    signals['updated_at'] = datetime.now().isoformat()
    
    with open(LIVE_SIGNALS, 'w') as f:
        json.dump(signals, f, indent=2)

def run_daemon():
    '''Main daemon loop. Run via cron every 5 minutes.'''
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [live] %(message)s')
    
    live = detect_live_streams()
    if not live:
        logging.info('No live streams detected')
        return
    
    for stream in live:
        logging.info(f'LIVE: {stream["channel"]} — {stream["title"]}')
        # For now, just detect and log. Full capture requires background process.
        # Phase 2 will add chunked capture.
        update_live_signals(stream, [], 50, 'Live stream detected, capture pending')

if __name__ == '__main__':
    run_daemon()

Test: python3 utils/live_monitor.py
Install cron: */5 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/live_monitor.py >> logs/live_monitor.log 2>&1

Commit: git add utils/live_monitor.py -m 'feat: live stream monitor — detect YouTube Live + classify in real-time'

=== PHASE 3: Terminal API Live Endpoint ===

Add to routes_api_terminal.py:

GET /api/v2/terminal/live
Returns current live streams with real-time topic/sentiment data.
Read from data/intelligence/live_signals.json.

Response:
{
  "data": {
    "live_streams": [
      {
        "channel": "Simply Bitcoin",
        "title": "Bitcoin price reaction LIVE",
        "topics": ["price", "ETF"],
        "current_sentiment": 72,
        "duration_minutes": 45,
        "url": "https://youtube.com/watch?v=..."
      }
    ],
    "monitoring": true,
    "channels_watched": 42,
    "last_check": "2026-03-05T19:00:00Z"
  }
}

Commander+ tier only.

Commit: git add routes_api_terminal.py -m 'feat: Terminal /live endpoint — real-time stream intelligence'

=== PHASE 4: Intelligent Clip Selection Engine ===

Per PRODUCT_BACKLOG.md item #2. Build utils/clip_scorer.py:

Score each potential clip moment 0-100 based on:
1. Topic velocity (from daily_signals.json): How many channels cover this topic? (0-25 points)
2. Engagement potential (from tweet study data): Does this topic trend on X? (0-20 points)
3. Novelty (from episode memory): Has this been covered in last 3 episodes? (0-20 points)
4. Speaker authority (from channel priority in channels.yaml): Tier 1 > Tier 2 (0-15 points)
5. Emotional impact (keyword analysis): controversial, surprising, data-heavy? (0-20 points)

def score_clip(clip_moment, daily_signals, episode_memory, channel_config):
    score = 0
    
    # 1. Topic velocity (0-25)
    for topic in daily_signals.get('topics', []):
        if any(kw in clip_moment['transcript'].lower() for kw in topic['topic'].lower().split()):
            score += min(topic['velocity_score'] / 4, 25)
            break
    
    # 2. Engagement potential (0-20)
    # Check if clip topics align with high-engagement X topics
    
    # 3. Novelty (0-20)
    # Check episode_memory for recent coverage
    
    # 4. Speaker authority (0-15)
    priority = channel_config.get('priority', 3)
    score += {1: 15, 2: 10, 3: 5}.get(priority, 0)
    
    # 5. Emotional impact (0-20)
    impact_words = ['breaking', 'shocking', 'unprecedented', 'historic', 'billion', 'million',
                    'crashed', 'surged', 'banned', 'approved', 'emergency', 'revolutionary']
    impact_count = sum(1 for w in impact_words if w in clip_moment['transcript'].lower())
    score += min(impact_count * 5, 20)
    
    return min(score, 100)

Wire into clip_selector.py: After Claude selects candidates, score them all, then pick top 5 from 5 unique channels by score.

Commit: git add utils/clip_scorer.py clip_selector.py -m 'feat: intelligent clip selection engine — data-driven scoring'

=== PHASE 5: Git Push Everything ===

git add -A && git push origin main

Report all completed items.

DO NOT render a new video in this session. Just build infrastructure.
PBX will review video notes and trigger the next render separately.