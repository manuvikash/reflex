"""
Example script to test SafeRunner webhook locally.
Simulates a Sentry webhook payload with proper signature.
"""
import hashlib
import hmac
import json
import os
import requests
from datetime import datetime

# Load environment
from dotenv import load_dotenv
load_dotenv()

WEBHOOK_SECRET = os.getenv("SENTRY_WEBHOOK_SECRET", "test-secret")
WEBHOOK_URL = "http://localhost:8000/webhooks/sentry"


def create_test_payload():
    """Create a realistic Sentry issue alert payload."""
    return {
        "action": "triggered",
        "data": {
            "issue": {
                "id": "12345678",
                "title": "ZeroDivisionError: division by zero",
                "permalink": "https://sentry.io/organizations/myorg/issues/12345678/",
                "status": "unresolved",
            },
            "event": {
                "event_id": "abc123def456",
                "title": "ZeroDivisionError: division by zero",
                "release": "v1.0.0",
                "tags": [
                    {"key": "service", "value": "my-api"},
                    {"key": "environment", "value": "production"},
                ],
                "exception": {
                    "values": [
                        {
                            "type": "ZeroDivisionError",
                            "value": "division by zero",
                            "stacktrace": {
                                "frames": [
                                    {
                                        "filename": "src/calculator.py",
                                        "function": "divide",
                                        "lineno": 42,
                                        "context_line": "    result = a / b",
                                    }
                                ]
                            },
                        }
                    ]
                },
            },
            "project": {
                "slug": "my-project",
                "organization": {
                    "slug": "my-org"
                }
            }
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for payload."""
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256
    ).hexdigest()


def send_test_webhook():
    """Send a test webhook to SafeRunner."""
    payload = create_test_payload()
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode("utf-8")
    
    # Generate signature
    signature = sign_payload(payload_bytes, WEBHOOK_SECRET)
    
    # Prepare request
    headers = {
        "Content-Type": "application/json",
        "Sentry-Hook-Signature": signature,
    }
    
    print("Sending test webhook to SafeRunner...")
    print(f"URL: {WEBHOOK_URL}")
    print(f"Issue ID: {payload['data']['issue']['id']}")
    print(f"Error: {payload['data']['event']['title']}")
    print()
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            data=payload_bytes,
            headers=headers,
            timeout=10
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code == 200:
            print("\n✅ Webhook accepted! Check server logs for processing status.")
        else:
            print(f"\n❌ Webhook rejected: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running?")
        print("   Start with: make server")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    send_test_webhook()
