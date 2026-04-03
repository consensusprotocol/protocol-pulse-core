Check Protocol Pulse uptime monitoring status.

Steps:
1. Run: python3 ~/protocol_pulse/scripts/setup_uptime_monitor.py --status
2. Also check: curl -s http://localhost:5000/health
3. Report combined status — which monitors are UP/DOWN, local health endpoint response, and any anomalies.
