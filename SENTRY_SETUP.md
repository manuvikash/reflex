# Sentry Integration Setup

This guide shows you how to test SafeRunner end-to-end using the sample buggy app.

## Step 1: Create a Sentry Project

1. Go to https://sentry.io and sign up/log in
2. Create a new project:
   - Platform: **Python**
   - Name: **saferunner-test**
3. Copy your **DSN** (looks like: `https://xxxxx@xxxxx.ingest.sentry.io/xxxxx`)

## Step 2: Add DSN to Environment

```bash
# Add to your .env file
echo "SENTRY_DSN=your-dsn-here" >> .env

# Or export directly
export SENTRY_DSN="https://xxxxx@xxxxx.ingest.sentry.io/xxxxx"
```

## Step 3: Install Sentry SDK

```bash
pip install sentry-sdk
```

## Step 4: Update sample_buggy_app.py

The app is already configured! Just update line 21 with your actual repo:

```python
sentry_sdk.set_tag("repo", "your-github-username/saferunner")
```

## Step 5: Test Sentry Integration

Run the buggy app to send errors to Sentry:

```bash
# Make the script executable
chmod +x examples/run_buggy_app.sh

# Run it
bash examples/run_buggy_app.sh
```

Or run directly:

```bash
export SENTRY_DSN="your-dsn"
python examples/sample_buggy_app.py
```

You should see:
```
✓ Sentry initialized
Traceback (most recent call last):
  ...
ZeroDivisionError: division by zero
```

## Step 6: Verify in Sentry Dashboard

1. Go to your Sentry dashboard
2. You should see 3 errors:
   - `ZeroDivisionError: division by zero` (from divide)
   - `ZeroDivisionError: division by zero` (from calculate_average)
   - `KeyError: 'last_name'` (from get_user_name)

## Step 7: Create Sentry Internal Integration

1. Go to **Settings → Developer Settings → Internal Integrations**
2. Click **New Internal Integration**
3. Fill in:
   - **Name**: SafeRunner
   - **Webhook URL**: `http://localhost:8000/webhooks/sentry` (or your ngrok URL)
   - **Permissions**: 
     - Issue & Event: **Read**
   - **Webhooks**: 
     - Enable **Issue**
4. Click **Save**
5. Copy the **Webhook Secret**
6. Add to `.env`:
   ```bash
   SENTRY_WEBHOOK_SECRET=your-webhook-secret
   ```

## Step 8: Set Up ngrok (for local testing)

Since Sentry needs to reach your local server:

```bash
# Install ngrok
# Download from https://ngrok.com/download

# Start ngrok
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

Update your Sentry webhook URL to: `https://abc123.ngrok.io/webhooks/sentry`

## Step 9: Create Alert Rule

1. Go to **Alerts → Create Alert**
2. Choose **Issues**
3. Set conditions:
   - **When**: An issue is first seen
   - **If**: All events
4. **Then**: Send a notification via **SafeRunner**
5. Click **Save Rule**

## Step 10: Test End-to-End

Now test the full flow:

```bash
# Terminal 1: Start SafeRunner
make server

# Terminal 2: Start ngrok (if testing locally)
ngrok http 8000

# Terminal 3: Trigger an error
export SENTRY_DSN="your-dsn"
python examples/sample_buggy_app.py
```

**What should happen:**

1. ✅ Error sent to Sentry
2. ✅ Sentry creates issue
3. ✅ Alert rule triggers
4. ✅ Webhook sent to SafeRunner
5. ✅ SafeRunner receives webhook (check logs)
6. ✅ Daytona sandbox created
7. ✅ Tests run, patch generated
8. ✅ GitHub PR created

**Check SafeRunner logs:**
```
INFO: Received Sentry webhook for issue 12345678
INFO: Processing Sentry issue 12345678: ZeroDivisionError
INFO: Resolving repository and commit
INFO: Creating Daytona sandbox
INFO: Sandbox created: sandbox_xyz123
INFO: Cloning repository
INFO: Running tests to reproduce bug
INFO: Generating patch with Claude
INFO: Validating patch
INFO: Applying patch
INFO: Re-running tests
INFO: Tests passed after patch! ✅
INFO: Creating GitHub pull request
INFO: Pull request created: https://github.com/...
```

## Troubleshooting

### "SENTRY_DSN not set"
```bash
export SENTRY_DSN="your-dsn-here"
```

### "No errors in Sentry"
- Check DSN is correct
- Run the app again
- Check Sentry project settings

### "Webhook not received"
- Check ngrok is running
- Verify webhook URL in Sentry
- Check `SENTRY_WEBHOOK_SECRET` matches
- Look for signature errors in SafeRunner logs

### "Sandbox creation failed"
- Make sure snapshot is created: `make snapshot`
- Check Daytona API key is valid
- Verify Daytona account has resources available

### "PR creation failed"
- Check `GITHUB_TOKEN` has `repo` scope
- Verify `GITHUB_OWNER` and `GITHUB_REPO` are correct
- Make sure repo exists and token has access

## Next Steps

Once the test works:

1. **Integrate into your real app** - Add Sentry SDK
2. **Configure services.yaml** - Map services to repos
3. **Set up Sentry Releases** - For deterministic routing
4. **Deploy SafeRunner** - Use systemd, Docker, or cloud
5. **Monitor and iterate** - Review PRs and adjust guardrails

## Quick Reference

```bash
# Install Sentry SDK
pip install sentry-sdk

# Run buggy app
export SENTRY_DSN="your-dsn"
python examples/sample_buggy_app.py

# Start SafeRunner
make server

# Start ngrok
ngrok http 8000

# Check Sentry
open https://sentry.io

# Check SafeRunner logs
# (in terminal running make server)
```

Happy bug fixing! 🤖
