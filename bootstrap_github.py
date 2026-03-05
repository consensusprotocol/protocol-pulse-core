import urllib.request, os, json

GH = 'https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/'
FILES = ['routes_api_terminal.py', 'routes_newsletter_trigger.py', 'routes_api_v2.py']

for fn in FILES:
    try:
        d = urllib.request.urlopen(GH + fn, timeout=10).read()
        with open(fn, 'wb') as f:
            f.write(d)
    except:
        pass

os.makedirs('config', exist_ok=True)
os.makedirs('data/intelligence', exist_ok=True)
if not os.path.exists('config/api_keys.json'):
    json.dump({'keys': [{'key': 'pp-test-commander-001', 'tier': 'commander', 'subscriber': 'PBX', 'active': True}]}, open('config/api_keys.json', 'w'))
if not os.path.exists('data/intelligence/daily_signals.json'):
    json.dump({'topics': [], 'breaking': False}, open('data/intelligence/daily_signals.json', 'w'))
