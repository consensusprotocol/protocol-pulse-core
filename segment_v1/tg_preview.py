#!/usr/bin/env python3
"""Send a render preview to PBX's Telegram (@Proto_P_bot chat) for the ship/hold gate.
Usage: tg_preview.py <video.mp4> <caption>

R2-12: Import-safe — no side effects at import time. All logic in functions."""
import json
import os
import subprocess
import sys


def _load_env():
    """Load .env file into a dict without side effects."""
    env = {}
    env_path = os.path.expanduser('~/protocol_pulse/.env')
    if os.path.exists(env_path):
        for line in open(env_path):
            if '=' in line and not line.startswith('#'):
                k, v = line.rstrip('\n').split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def send_preview(video, caption):
    """Send video preview to Telegram. Returns (ok, message_id, file_size)."""
    env = _load_env()
    tok = env.get('TELEGRAM_BOT_TOKEN', '')
    chat = env.get('TELEGRAM_CHAT_ID', '')
    if not tok or not chat:
        print("tg_preview: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return False, None, None

    # Probe real width/height with ffprobe (never hardcode)
    probe = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=width,height', '-of', 'csv=p=0', video],
        capture_output=True, text=True, timeout=10)
    dims = probe.stdout.strip().split(',')
    if len(dims) < 2:
        print(f"tg_preview: ffprobe failed for {video}")
        return False, None, None
    width, height = dims[0], dims[1]
    print(f'ffprobe dims: {width}x{height}')

    cmd = ['curl', '-sS', '-X', 'POST', f'https://api.telegram.org/bot{tok}/sendVideo',
           '-F', f'chat_id={chat}', '-F', f'caption={caption}', '-F', 'supports_streaming=true',
           '-F', f'width={width}', '-F', f'height={height}', '-F', f'video=@{video}']
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    r = json.loads(out.stdout or '{}')
    ok = r.get('ok', False)
    msg_id = r.get('result', {}).get('message_id')
    file_size = r.get('result', {}).get('video', {}).get('file_size')
    print('sent:', ok, 'message_id', msg_id,
          'file_size', file_size, '' if ok else r.get('description'))
    return ok, msg_id, file_size


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <video.mp4> <caption>")
        sys.exit(1)
    send_preview(sys.argv[1], sys.argv[2])
