#!/bin/bash
# Setup script for saferunner-test repository

echo "🚀 Setting up saferunner-test repository..."
echo ""

# Check if repo name is provided
REPO_NAME=${1:-saferunner-test}
GITHUB_USERNAME=${2:-YOUR-USERNAME}

echo "Repository: $REPO_NAME"
echo "GitHub User: $GITHUB_USERNAME"
echo ""
echo "⚠️  Make sure you've created the repo on GitHub first!"
echo "   Go to: https://github.com/new"
echo "   Name: $REPO_NAME"
echo ""
read -p "Press Enter to continue..."

# Create directory
mkdir -p ../$REPO_NAME
cd ../$REPO_NAME

# Initialize git
git init
echo "✓ Initialized git repository"

# Create .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
.env
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
EOF
echo "✓ Created .gitignore"

# Create README
cat > README.md << 'EOF'
# SafeRunner Test Repository

This is a test repository for demonstrating SafeRunner's automated bug fixing capabilities.

## The Bug

This repository contains a simple calculator with intentional bugs:
- Division by zero not handled
- Empty list not handled in average calculation

## How It Works

1. Sentry captures errors from the application
2. SafeRunner receives the webhook
3. SafeRunner creates a Daytona sandbox
4. Runs tests to reproduce the bug
5. Uses Claude to generate a fix
6. Validates the fix with tests
7. Creates a PR with the fix

## Running the App

```bash
pip install -r requirements.txt
python app.py
```

## Running Tests

```bash
pytest -v
```
EOF
echo "✓ Created README.md"

# Create requirements.txt
cat > requirements.txt << 'EOF'
pytest==7.4.3
sentry-sdk==2.18.0
python-dotenv==1.0.0
EOF
echo "✓ Created requirements.txt"

# Create .env.example
cat > .env.example << 'EOF'
SENTRY_DSN=your_sentry_dsn_here
EOF
echo "✓ Created .env.example"

# Create the buggy calculator
cat > calculator.py << 'EOF'
"""
Simple calculator with intentional bugs for testing SafeRunner.
"""

def divide(a: float, b: float) -> float:
    """
    Divide two numbers.
    
    Bug: No check for division by zero!
    """
    return a / b


def average(numbers: list) -> float:
    """
    Calculate the average of a list of numbers.
    
    Bug: Doesn't handle empty list!
    """
    return sum(numbers) / len(numbers)


def get_user_info(user: dict) -> str:
    """
    Get formatted user information.
    
    Bug: Doesn't handle missing keys!
    """
    return f"{user['name']} ({user['email']})"
EOF
echo "✓ Created calculator.py"

# Create the app with Sentry integration
cat > app.py << 'EOF'
"""
Main application with Sentry integration.
This will capture errors and send them to Sentry.
"""
import os
from pathlib import Path
import sentry_sdk
from dotenv import load_dotenv
from calculator import divide, average, get_user_info

# Load environment variables
load_dotenv()

# Initialize Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
    
    # Add tags for SafeRunner routing
    sentry_sdk.set_tag("service", "calculator-app")
    sentry_sdk.set_tag("repo", "YOUR-USERNAME/saferunner-test")  # UPDATE THIS!
    sentry_sdk.set_tag("environment", "production")
    
    print("✓ Sentry initialized")
else:
    print("⚠️  SENTRY_DSN not set - errors won't be captured")


def main():
    """Run the calculator app and trigger errors."""
    print("🧮 Calculator App")
    print("=" * 50)
    
    # Normal operations (these work)
    print("\n✅ Normal operations:")
    print(f"10 / 2 = {divide(10, 2)}")
    print(f"Average of [1,2,3,4,5] = {average([1, 2, 3, 4, 5])}")
    print(f"User: {get_user_info({'name': 'John', 'email': 'john@example.com'})}")
    
    # Buggy operations (these will crash)
    print("\n❌ Buggy operations (will trigger Sentry errors):")
    
    try:
        print("Attempting division by zero...")
        result = divide(10, 0)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        sentry_sdk.capture_exception(e)
    
    try:
        print("Attempting average of empty list...")
        result = average([])
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        sentry_sdk.capture_exception(e)
    
    try:
        print("Attempting to get user info with missing email...")
        result = get_user_info({'name': 'Jane'})
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        sentry_sdk.capture_exception(e)
    
    # Flush events to Sentry
    print("\n📤 Flushing events to Sentry...")
    sentry_sdk.flush(timeout=5)
    print("✅ Done! Check Sentry dashboard for errors.")


if __name__ == "__main__":
    main()
EOF
echo "✓ Created app.py"

# Create tests
cat > test_calculator.py << 'EOF'
"""
Tests for calculator functions.
These tests will fail until the bugs are fixed.
"""
import pytest
from calculator import divide, average, get_user_info


class TestDivide:
    """Tests for divide function."""
    
    def test_divide_normal(self):
        """Test normal division."""
        assert divide(10, 2) == 5
        assert divide(15, 3) == 5
        assert divide(7, 2) == 3.5
    
    def test_divide_by_zero(self):
        """Test division by zero raises appropriate error."""
        with pytest.raises(ZeroDivisionError):
            divide(10, 0)


class TestAverage:
    """Tests for average function."""
    
    def test_average_normal(self):
        """Test normal average calculation."""
        assert average([1, 2, 3]) == 2
        assert average([10, 20, 30]) == 20
        assert average([5]) == 5
    
    def test_average_empty_list(self):
        """Test empty list raises appropriate error."""
        with pytest.raises(ValueError):
            average([])


class TestGetUserInfo:
    """Tests for get_user_info function."""
    
    def test_get_user_info_normal(self):
        """Test normal user info retrieval."""
        user = {'name': 'John', 'email': 'john@example.com'}
        assert get_user_info(user) == "John (john@example.com)"
    
    def test_get_user_info_missing_keys(self):
        """Test missing keys raises appropriate error."""
        with pytest.raises(KeyError):
            get_user_info({'name': 'Jane'})
        
        with pytest.raises(KeyError):
            get_user_info({'email': 'jane@example.com'})
EOF
echo "✓ Created test_calculator.py"

# Create GitHub Actions workflow (optional but nice to have)
mkdir -p .github/workflows
cat > .github/workflows/test.yml << 'EOF'
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest -v
EOF
echo "✓ Created GitHub Actions workflow"

# Initial commit
git add .
git commit -m "Initial commit: Calculator app with bugs for SafeRunner testing"
echo "✓ Created initial commit"

echo ""
echo "✅ Repository setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Create the repository on GitHub:"
echo "   https://github.com/new"
echo ""
echo "2. Add the remote and push:"
echo "   cd ../$REPO_NAME"
echo "   git remote add origin https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3. Update app.py line 27 with your GitHub username"
echo ""
echo "4. Create .env file with your Sentry DSN:"
echo "   cd ../$REPO_NAME"
echo "   echo 'SENTRY_DSN=your_dsn_here' > .env"
echo ""
echo "5. Update SafeRunner .env with:"
echo "   GITHUB_OWNER=$GITHUB_USERNAME"
echo "   GITHUB_REPO=$REPO_NAME"
echo ""
echo "6. Test the app:"
echo "   cd ../$REPO_NAME"
echo "   pip install -r requirements.txt"
echo "   python app.py"
echo ""
