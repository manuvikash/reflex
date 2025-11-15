"""
Sample buggy application for testing SafeRunner.
This demonstrates a simple bug that SafeRunner can fix.
"""
import os
from pathlib import Path
import sentry_sdk
from dotenv import load_dotenv

# Load environment variables from .env file in project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize Sentry
# Get DSN from environment variable or use your actual DSN
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
    
    # Add tags for SafeRunner routing
    sentry_sdk.set_tag("service", "sample-buggy-app")
    sentry_sdk.set_tag("repo", "your-org/saferunner")  # Update with your repo
    sentry_sdk.set_tag("environment", "test")
    
    print("✓ Sentry initialized")
else:
    print("⚠️  SENTRY_DSN not set - errors won't be captured")


def divide(a: float, b: float) -> float:
    """
    Divide two numbers.
    
    Bug: No check for division by zero!
    """
    return a / b


def calculate_average(numbers: list) -> float:
    """
    Calculate the average of a list of numbers.
    
    Bug: Doesn't handle empty list!
    """
    return sum(numbers) / len(numbers)


def get_user_name(user_dict: dict) -> str:
    """
    Get user's full name.
    
    Bug: Doesn't handle missing keys!
    """
    return f"{user_dict['first_name']} {user_dict['last_name']}"


if __name__ == "__main__":
    import time
    
    print("🐛 Triggering errors and sending to Sentry...\n")
    
    # Trigger errors and capture them with Sentry
    errors_triggered = 0
    
    # Error 1: Division by zero
    try:
        print("1. Testing divide by zero...")
        result = divide(10, 0)
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        sentry_sdk.capture_exception(e)
        errors_triggered += 1
    
    # Error 2: Empty list average
    try:
        print("2. Testing empty list average...")
        result = calculate_average([])
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        sentry_sdk.capture_exception(e)
        errors_triggered += 1
    
    # Error 3: Missing dictionary key
    try:
        print("3. Testing missing dictionary key...")
        result = get_user_name({"first_name": "John"})
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        sentry_sdk.capture_exception(e)
        errors_triggered += 1
    
    # Flush events to Sentry (important!)
    print(f"\n📤 Flushing {errors_triggered} errors to Sentry...")
    sentry_sdk.flush(timeout=5)
    
    print("✅ Done! Check your Sentry dashboard for the errors.")
    print(f"   URL: https://sentry.io")
    
    # Give a moment for events to be sent
    time.sleep(2)
