#!/bin/bash
# Quick Bitcoin/Lightning payment setup

echo "Bitcoin/Lightning Payment Setup"
echo "================================"
echo ""

# Check if already configured
if [ -n "$BTC_ADDRESS" ]; then
    echo "BTC Address: $BTC_ADDRESS"
else
    echo "BTC_ADDRESS not set"
fi

if [ -n "$LIGHTNING_ADDRESS" ]; then
    echo "Lightning Address: $LIGHTNING_ADDRESS"
else
    echo "LIGHTNING_ADDRESS not set"
fi

echo ""
echo "To configure, add to Replit Secrets:"
echo "  BTC_ADDRESS=bc1q..."
echo "  LIGHTNING_ADDRESS=you@getalby.com"
