Full Protocol Pulse system status dashboard:

**Infrastructure:**
- Waitress (port 5000): alive/dead + uptime
- RAM: used/total + top 3 consumers
- GPU: nvidia-smi summary
- Disk: df -h /home

**Content Pipeline:**
- Last render: when + success/fail + duration
- Last tweet: when + text + posted/blocked
- Morning brief: age + sentiment
- Transcript intel: last run + creator count
- KOL sentiment: avg score + creator count

**Cron Health:**
- Tweet machine: last fire time
- Brief generation: last fire time  
- Convergence engine: last fire time
- Media sync: last fire time

Format as a clean, readable dashboard.