Post a specific tweet to X/Protocol Pulse account.

Tweet text: $ARGUMENTS

Steps:
1. Verify tweet is <280 chars
2. Check X gate: is posting allowed right now?
3. Post via tweepy using credentials from .env
4. Report: tweet ID, URL, or gate rejection reason
```bash
cd ~/protocol_pulse && python3 -c "
from services.x_service import post_tweet, x_gate_check
text = '$ARGUMENTS'
allowed, reason = x_gate_check(text, source='manual', angle_category='manual')
if allowed:
    result = post_tweet(text)
    print(f'Posted: {result}')
else:
    print(f'Blocked: {reason}')
"
```