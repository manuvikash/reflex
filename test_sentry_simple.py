#!/usr/bin/env python3
"""Simple Sentry test - no dependencies on .env"""
import sentry_sdk

# Initialize with your DSN directly
sentry_sdk.init(
    dsn="https://2ebaab09628b365f5101dd41e0a2aae6@o4510365755310080.ingest.us.sentry.io/4510367264407552",
    traces_sample_rate=1.0,
)

print("Sending test error to Sentry...")

# Capture a test exception
try:
    1 / 0
except Exception as e:
    sentry_sdk.capture_exception(e)
    print(f"Captured: {e}")

# Flush and wait
print("Flushing to Sentry...")
sentry_sdk.flush(timeout=5)

print("✅ Done! Check Sentry dashboard: https://sentry.io")
