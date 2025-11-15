#!/usr/bin/env python3
"""
Test script to trigger Sentry errors and webhook.
This version has the DSN hardcoded so it will definitely work.
"""
import time
import sentry_sdk

# Initialize Sentry with your DSN directly
sentry_sdk.init(
    dsn="https://2ebaab09628b365f5101dd41e0a2aae6@o4510365755310080.ingest.us.sentry.io/4510367264407552",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

# Add tags for SafeRunner routing
sentry_sdk.set_tag("service", "sample-buggy-app")
sentry_sdk.set_tag("repo", "your-org/saferunner")
sentry_sdk.set_tag("environment", "test")

print("✓ Sentry initialized")
print("🐛 Triggering errors and sending to Sentry...\n")

errors_triggered = 0

# Error 1: Division by zero
try:
    print("1. Testing divide by zero...")
    result = 10 / 0
except Exception as e:
    print(f"   ❌ Error: {e}")
    sentry_sdk.capture_exception(e)
    errors_triggered += 1

# Error 2: Empty list
try:
    print("2. Testing empty list average...")
    numbers = []
    result = sum(numbers) / len(numbers)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sentry_sdk.capture_exception(e)
    errors_triggered += 1

# Error 3: Missing key
try:
    print("3. Testing missing dictionary key...")
    user = {"first_name": "John"}
    full_name = f"{user['first_name']} {user['last_name']}"
except Exception as e:
    print(f"   ❌ Error: {e}")
    sentry_sdk.capture_exception(e)
    errors_triggered += 1

# Flush events to Sentry
print(f"\n📤 Flushing {errors_triggered} errors to Sentry...")
sentry_sdk.flush(timeout=5)

print("✅ Done! Check your Sentry dashboard for the errors.")
print("   URL: https://sentry.io")
print("\n⏳ Waiting for webhook to fire...")
print("   Check SafeRunner logs and ngrok dashboard")

time.sleep(2)
