---
name: site-check
description: Check Protocol Pulse website health. Tests endpoints, waitress, SSL, response times.
invocation: user
---
# Site Check Skill
1. Waitress: pgrep -f waitress
2. Health: curl localhost:5000/health
3. Endpoints: /terminal, /intelligence, /briefs, /oracle, /panopticon
4. BTC price: /api/btc-price
5. SSL: curl https://protocolpulse.io
6. Report: endpoint status + response times
