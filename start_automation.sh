#!/bin/bash
# Protocol Pulse - Continuous Automation Runner
# Runs automation_worker.py every 15 minutes in the background

echo "🚀 Starting Protocol Pulse Automation"
echo "📰 Articles will generate every 15 minutes"
echo "📊 Monitor at: http://localhost:5000/health/automation"
echo ""

# Run automation loop in background
while true; do
    echo "⏰ $(date '+%Y-%m-%d %H:%M:%S') - Running automation..."
    python3 automation_worker.py
    
    if [ $? -eq 0 ]; then
        echo "✅ Success! Next run in 15 minutes..."
    else
        echo "❌ Failed! Retrying in 15 minutes..."
    fi
    
    # Wait 15 minutes (900 seconds)
    sleep 900
done
