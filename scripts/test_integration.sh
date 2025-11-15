#!/bin/bash
# Integration test script for SafeRunner

set -e

echo "🧪 SafeRunner Integration Test"
echo "==============================="
echo ""

# Check if server is running
echo "Checking if server is running..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Server not running on port 8000"
    echo "   Start with: make server"
    exit 1
fi
echo "✅ Server is running"

# Check environment variables
echo ""
echo "Checking environment variables..."
source .env 2>/dev/null || true

if [ -z "$DAYTONA_API_KEY" ]; then
    echo "❌ DAYTONA_API_KEY not set"
    exit 1
fi

if [ -z "$SENTRY_WEBHOOK_SECRET" ]; then
    echo "❌ SENTRY_WEBHOOK_SECRET not set"
    exit 1
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN not set"
    exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not set"
    exit 1
fi

echo "✅ All required environment variables set"

# Check Daytona snapshot
echo ""
echo "Checking Daytona snapshot..."
if daytona snapshot list | grep -q "saferunner-ci"; then
    echo "✅ Snapshot 'saferunner-ci' exists"
else
    echo "⚠️  Snapshot 'saferunner-ci' not found"
    echo "   Create with: make snapshot"
    exit 1
fi

# Send test webhook
echo ""
echo "Sending test webhook..."
python examples/test_webhook.py

echo ""
echo "================================"
echo "✅ Integration test complete!"
echo ""
echo "Check server logs for processing status."
echo "A GitHub PR should be created if all steps succeed."
