Refresh the Protocol Pulse morning intelligence brief:
1. Check Ollama: `pgrep -f "ollama serve"` — start if not running
2. Wait for Ollama: `sleep 10` if just started
3. Run: `cd ~/protocol_pulse && python3 services/morning_brief.py`
4. Report: age, sentiment, top narratives, BTC price used
5. If failed, check logs/morning_brief_cron.log for error