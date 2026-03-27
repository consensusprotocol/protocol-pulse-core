#!/bin/bash
# Kill any hung gunicorn workers on port 5000
fuser -k 5000/tcp 2>/dev/null
pkill -9 -f gunicorn.*app:app 2>/dev/null
sleep 3
# Start with correct chdir
cd /home/ultron/protocol_pulse/core
/usr/bin/python3 /home/ultron/.local/bin/gunicorn app:app   --workers 2   --bind 0.0.0.0:5000   --timeout 300   --daemon   --chdir /home/ultron/protocol_pulse/core   --error-logfile /home/ultron/protocol_pulse/logs/gunicorn_error.log   --access-logfile /home/ultron/protocol_pulse/logs/gunicorn_access.log
