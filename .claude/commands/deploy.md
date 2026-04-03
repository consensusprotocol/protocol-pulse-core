Verify full Protocol Pulse deployment health. Check ALL of these:
1. Waitress alive: `pgrep -f "waitress.*5000"` 
2. Website responds: `curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/health`
3. RAM usage: `free -h` (warn if >70GB used)
4. Top RAM consumers: `ps aux --sort=-%mem | head -5` (flag any >5GB)
5. Cloudflare tunnel: `curl -s -o /dev/null -w '%{http_code}' https://protocolpulse.io/health`
6. Ollama running: `pgrep -f "ollama serve"`
7. Last tweet: check logs/tweet_machine_cron.log for most recent post
8. Brief freshness: check age of data/intelligence/morning_intelligence_brief.json
9. Git status: `git status --porcelain | wc -l` uncommitted files
Report each check as PASS/FAIL with details.