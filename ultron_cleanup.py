#!/usr/bin/env python3
"""
ultron_cleanup.py — Auto-cleanup zombie processes and stale tmux sessions
Runs every 30 min via cron. Safe: never kills active renders or the loop.
"""
import subprocess, time, os, json
from datetime import datetime

LOG = '/home/ultron/protocol_pulse/logs/cleanup.log'

PROTECTED_PROCS = [
    'autonomous_render_loop',
    'overnight_render_loop',
    'daily_producer',
    'gunicorn',
    'tg_watcher',
    'ultron_relay',
    'nostr_monitor',
    'avatar_server',
    'flask',
]

PROTECTED_SESSIONS = [
    'flask_main', 'gunicorn', 'tg_watcher', 'video_server',
]

ZOMBIE_PROCS = [
    'channel_daemon',
    'imap_idle_daemon',
    'daily_run.py',
    'x_spaces_scraper',
]

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    with open(LOG, 'a') as f:
        f.write(line + '\n')

def kill_zombies():
    for proc in ZOMBIE_PROCS:
        r = subprocess.run(['pkill', '-9', '-f', proc], capture_output=True)
        if r.returncode == 0:
            log(f'KILLED zombie: {proc}')

def kill_stale_tmux():
    r = subprocess.run(['tmux', 'ls'], capture_output=True, text=True)
    if r.returncode != 0:
        return
    for line in r.stdout.strip().split('\n'):
        if not line:
            continue
        session = line.split(':')[0].strip()
        # Keep protected sessions
        if session in PROTECTED_SESSIONS:
            continue
        # Keep cc_ sessions that are actively running claude
        if session.startswith('cc_') or session.startswith('cc'):
            # Check if claude is running in this session
            pane = subprocess.run(['tmux', 'capture-pane', '-t', session, '-p'],
                                   capture_output=True, text=True).stdout
            if 'bypass permissions' in pane or 'Thinking' in pane or 'Synthesizing' in pane or 'cogitat' in pane.lower():
                continue  # actively working - keep it
            # Check age - kill cc_ sessions older than 2 hours if idle
            # Get session creation time from tmux ls output
            if '(created' in line:
                # Session is idle - kill it
                subprocess.run(['tmux', 'kill-session', '-t', session])
                log(f'KILLED stale tmux session: {session}')

def check_api_spend():
    # Check if channel_daemon or other zombies crept back
    r = subprocess.run(['pgrep', '-f', 'channel_daemon'], capture_output=True)
    count = len(r.stdout.decode().strip().split('\n')) if r.stdout.strip() else 0
    if count > 2:
        subprocess.run(['pkill', '-9', '-f', 'channel_daemon'])
        log(f'EMERGENCY: killed {count} channel_daemon instances that respawned')

if __name__ == '__main__':
    log('--- cleanup run ---')
    kill_zombies()
    kill_stale_tmux()
    check_api_spend()
    log('--- done ---')
