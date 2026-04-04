Run a comprehensive site health check on protocolpulse.io.

Check ALL of these endpoints and report results:
```bash
for ep in /health /api/btc-price /api/pro-metrics /api/kol/sentiment /api/kol/themes /api/media/stats /api/intelligence/sovereign-context; do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:5000$ep)
    echo "$ep → $code"
done
```

Also check:
- BTC price value (should be >0): `curl -s http://localhost:5000/api/btc-price | python3 -c "import sys,json; print(json.load(sys.stdin))"`
- Morning brief age
- Last article generated
- Site health log: `tail -10 ~/protocol_pulse/logs/site_health.log`

If any endpoint returns non-200, diagnose and fix immediately.