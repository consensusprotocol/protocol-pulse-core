#!/bin/bash
pkill -f "gunicorn.*8201" 2>/dev/null
sleep 2
exec /usr/bin/python3 /home/ultron/.local/bin/gunicorn \
  --workers 4 --bind 0.0.0.0:8201 --timeout 120 \
  --max-requests 1000 --max-requests-jitter 100 \
  --keep-alive 65 \
  /home/ultron/protocol_pulse/ultron_relay:app \
  --chdir /home/ultron/protocol_pulse \
  --error-logfile /home/ultron/protocol_pulse/logs/relay_error.log
