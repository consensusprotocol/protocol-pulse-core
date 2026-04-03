Show PM2 process status dashboard.

Steps:
1. Run: pm2 list
2. Run: pm2 jlist (JSON status of all processes)
3. Report status, uptime, memory, and restart count for each managed process:
   - waitress (Flask web server, port 5000)
   - relay (Ultron relay, port 8201)
   - ollama (local LLM inference)
   - social-daemon (social media automation)
4. Flag any process that is stopped, errored, or has restarted more than 3 times
5. Note: the HeyGen video process is intentionally NOT managed by PM2 (DISABLED)
