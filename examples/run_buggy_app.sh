#!/bin/bash
# Run the sample buggy app with Sentry integration

echo "🐛 Running Sample Buggy App with Sentry"
echo "========================================"
echo ""

# Check if SENTRY_DSN is set
if [ -z "$SENTRY_DSN" ]; then
    echo "❌ SENTRY_DSN environment variable not set!"
    echo ""
    echo "Please set it first:"
    echo "  export SENTRY_DSN='https://your-key@your-org.ingest.sentry.io/your-project-id'"
    echo ""
    echo "Or add it to your .env file and run:"
    echo "  export \$(cat .env | grep SENTRY_DSN | xargs)"
    exit 1
fi

echo "✓ SENTRY_DSN is set"
echo ""

# Install sentry-sdk if not already installed
if ! python -c "import sentry_sdk" 2>/dev/null; then
    echo "Installing sentry-sdk..."
    pip install sentry-sdk
    echo ""
fi

echo "Running buggy app (this will trigger errors)..."
echo ""

# Run the app
python examples/sample_buggy_app.py

echo ""
echo "✅ Errors sent to Sentry!"
echo ""
echo "Next steps:"
echo "1. Check your Sentry dashboard for the errors"
echo "2. Make sure SafeRunner webhook is configured in Sentry"
echo "3. Create an alert rule to trigger SafeRunner"
echo "4. Watch SafeRunner create a PR with the fix!"
