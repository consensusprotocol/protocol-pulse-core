Generate and post a Protocol Pulse tweet:
1. Check brief freshness: `stat data/intelligence/morning_intelligence_brief.json`
2. If brief >12h old, refresh: `python3 services/morning_brief.py`
3. Fire tweet machine: `python3 services/tweet_machine.py`
4. Check if posted or blocked — read the last 10 lines of output
5. If blocked, explain which gate blocked it and fix
6. Show the tweet text that was generated