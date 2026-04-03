Diagnose why something is broken or not working.

Problem: $ARGUMENTS

Protocol:
1. Search logs for errors: grep -ri "error\|fail\|traceback" in relevant log files
2. Check if the relevant service/process is running
3. Check cron schedule — did it fire?
4. Check dependencies (Ollama, waitress, API keys)
5. Trace the data path from source to output
6. Identify root cause (not symptoms)
7. Propose fix with exact code change
Do NOT fix yet — just diagnose and report findings.