Generate and post a Protocol Pulse tweet.

Topic/angle: $ARGUMENTS
- If blank: use default tweet machine (random format from brief)
- If specified: pass as context to tweet machine for targeted content

Steps:
1. Check brief freshness: if >12h old, refresh first
2. Fire tweet machine: `cd ~/protocol_pulse && python3 services/tweet_machine.py`
3. If $ARGUMENTS specified, generate a targeted tweet about that topic
4. Check if posted or blocked — show gate decision
5. If blocked, explain which gate and fix