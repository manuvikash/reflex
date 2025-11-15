#!/bin/bash
# Development setup script for SafeRunner

set -e

echo "🚀 SafeRunner Development Setup"
echo "================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ required, found $python_version"
    exit 1
fi
echo "✅ Python $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Check for .env file
echo ""
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "📝 Please edit .env with your credentials:"
    echo "   - DAYTONA_API_KEY"
    echo "   - SENTRY_WEBHOOK_SECRET"
    echo "   - GITHUB_TOKEN"
    echo "   - ANTHROPIC_API_KEY"
else
    echo "✅ .env file exists"
fi

# Check Daytona CLI
echo ""
echo "Checking Daytona CLI..."
if command -v daytona &> /dev/null; then
    echo "✅ Daytona CLI installed"
    daytona_version=$(daytona version 2>&1 || echo "unknown")
    echo "   Version: $daytona_version"
else
    echo "⚠️  Daytona CLI not found"
    echo ""
    echo "Install with:"
    echo "  curl -sf https://download.daytona.io/daytona/install.sh | sh"
fi

# Check for services.yaml
echo ""
if [ ! -f "services.yaml" ]; then
    echo "⚠️  No services.yaml found (optional)"
else
    echo "✅ services.yaml exists"
fi

echo ""
echo "================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your credentials"
echo "  2. Run: make snapshot (to create Daytona snapshot)"
echo "  3. Run: make server (to start webhook server)"
echo "  4. Test: python examples/test_webhook.py"
echo ""
echo "For more info, see QUICKSTART.md"
