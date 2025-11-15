"""FastAPI webhook server for receiving Sentry issue alerts."""
import hashlib
import hmac
import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from control.worker import process_sentry_alert

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SafeRunner")

SENTRY_WEBHOOK_SECRET = os.getenv("SENTRY_WEBHOOK_SECRET", "")


def verify_sentry_signature(body: bytes, signature: str) -> bool:
    """Verify Sentry webhook signature using HMAC-SHA256."""
    if not SENTRY_WEBHOOK_SECRET:
        logger.warning("SENTRY_WEBHOOK_SECRET not set, skipping verification")
        return True
    
    expected_signature = hmac.new(
        key=SENTRY_WEBHOOK_SECRET.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/webhooks/sentry")
async def sentry_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive Sentry issue alert webhooks.
    Verifies signature and queues processing in background.
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Get signature from header
    signature = request.headers.get("Sentry-Hook-Signature", "")
    
    if not signature:
        logger.error("Missing Sentry-Hook-Signature header")
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    # Verify signature
    if not verify_sentry_signature(body, signature):
        logger.error("Invalid Sentry webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Log the event
    event_id = payload.get("data", {}).get("event", {}).get("event_id", "unknown")
    issue_id = payload.get("data", {}).get("issue", {}).get("id", "unknown")
    logger.info(f"Received Sentry webhook for issue {issue_id}, event {event_id}")
    
    # Queue background processing
    background_tasks.add_task(process_sentry_alert, payload)
    
    return JSONResponse(content={"ok": True}, status_code=200)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
