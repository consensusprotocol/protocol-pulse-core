View Protocol Pulse unified logs.

Mode: $ARGUMENTS
- If blank or "summary": show last line from each log with age
- If "follow" or "-f": tail -f all logs simultaneously
- If a specific service name: show last 20 lines of that log

```bash
~/protocol_pulse/scripts/unified_log.sh $ARGUMENTS
```