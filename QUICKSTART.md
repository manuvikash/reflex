# SafeRunner Quick Start Guide

Get SafeRunner up and running in 5 minutes.

## Prerequisites Checklist

- [ ] Python 3.11+ installed
- [ ] Daytona account ([sign up](https://daytona.io))
- [ ] GitHub personal access token
- [ ] Sentry project with Internal Integration
- [ ] Anthropic API key

## Step 1: Install Dependencies

```bash
cd saferunner
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Get from https://app.daytona.io/settings/api-keys
DAYTONA_API_KEY=dtna_xxxxx

# Get from Sentry Settings → Developer Settings → Internal Integrations
SENTRY_WEBHOOK_SECRET=your_secret_here

# Get from GitHub Settings → Developer settings → Personal access tokens
GITHUB_OWNER=your-org
GITHUB_REPO=your-repo
GITHUB_TOKEN=ghp_xxxxx

# Get from https://console.anthropic.com/settings/keys
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

## Step 3: Create Daytona Snapshot

```bash
# Install Daytona CLI if not already installed
curl -sf https://download.daytona.io/daytona/install.sh | sh

# Login to Daytona
daytona login

# Create snapshot
make snapshot
```

This creates a pre-built environment with pytest and dependencies.

## Step 4: Start the Server

```bash
make server
```

Server runs on `http://localhost:8000`

Test it:
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

## Step 5: Configure Sentry Webhook

### Create Internal Integration

1. Go to Sentry: **Settings → Developer Settings → Internal Integrations**
2. Click **New Internal Integration**
3. Fill in:
   - **Name**: SafeRunner
   - **Webhook URL**: `https://your-domain.com/webhooks/sentry`
   - **Permissions**: Issue & Event: Read
   - **Webhooks**: Enable "Issue"
4. Click **Save**
5. Copy the **Webhook Secret** to your `.env` file

### Expose Local Server (for testing)

Use ngrok or similar:

```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) and update your Sentry webhook URL to:
```
https://abc123.ngrok.io/webhooks/sentry
```

### Create Alert Rule

1. Go to **Alerts → Create Alert**
2. Choose **Issues**
3. Set conditions (e.g., "First seen")
4. Under "Perform these actions", choose **Send a notification via** → **SafeRunner**
5. Save the alert

## Step 6: Test the Flow

### Trigger a Test Error

In your application:

```python
import sentry_sdk

sentry_sdk.init(dsn="your-dsn")
sentry_sdk.set_tag("service", "my-service")  # Optional: for routing

# Trigger an error
raise Exception("Test error for SafeRunner")
```

### Watch the Logs

```bash
# In the terminal running the server
# You should see:
# - Webhook received
# - Signature verified
# - Sandbox created
# - Tests run
# - Patch generated
# - PR created
```

### Check GitHub

A new PR should appear with:
- Branch: `saferunner/fix-{issue-id}-{timestamp}`
- Title: `🤖 Fix: {error message}`
- Description: Details about the fix

## Step 7: Configure Service Routing (Optional)

Edit `services.yaml`:

```yaml
my-api:
  repo: myorg/my-api
  path: ""
  test_command: "pytest -q tests/"

my-frontend:
  repo: myorg/my-frontend
  path: "packages/frontend"
  test_command: "npm test"
```

Tag your Sentry events:

```python
sentry_sdk.set_tag("service", "my-api")
sentry_sdk.set_tag("repo", "myorg/my-api")
```

## Troubleshooting

### "DAYTONA_API_KEY not set"
- Check your `.env` file exists
- Verify the key starts with `dtna_`
- Try: `export $(cat .env | xargs)` then run again

### "Snapshot not found"
- Run `make snapshot` to create it
- Verify with: `daytona snapshot list`

### "Invalid signature"
- Check `SENTRY_WEBHOOK_SECRET` matches Sentry
- Ensure you're using Internal Integration (not legacy plugin)

### "Failed to create PR"
- Verify `GITHUB_TOKEN` has `repo` scope
- Check `GITHUB_OWNER` and `GITHUB_REPO` are correct
- Ensure token hasn't expired

### "Tests still failing after patch"
- Check logs for Claude's generated patch
- Verify test command is correct in `services.yaml`
- Ensure dependencies are in `sandbox/requirements.txt`

## Next Steps

1. **Set up Sentry Releases** for deterministic commit routing:
   ```bash
   sentry-cli releases new $VERSION
   sentry-cli releases set-commits --auto $VERSION
   ```

2. **Add more services** to `services.yaml`

3. **Configure network restrictions** in `daytona_client.py`:
   ```python
   sandbox = daytona.create_sandbox(
       network_block_all=True,
       network_allow_list=["github.com", "pypi.org"]
   )
   ```

4. **Deploy to production** (use systemd, Docker, or cloud platform)

## Production Deployment

### Using systemd

Create `/etc/systemd/system/saferunner.service`:

```ini
[Unit]
Description=SafeRunner Service
After=network.target

[Service]
Type=simple
User=saferunner
WorkingDirectory=/opt/saferunner
Environment="PATH=/opt/saferunner/venv/bin"
ExecStart=/opt/saferunner/venv/bin/python -m control.server
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable saferunner
sudo systemctl start saferunner
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "control.server"]
```

Build and run:
```bash
docker build -t saferunner .
docker run -p 8000:8000 --env-file .env saferunner
```

## Support

- **Documentation**: See [README.md](README.md)
- **Issues**: Open a GitHub issue
- **Daytona Docs**: https://docs.daytona.io
- **Sentry Docs**: https://docs.sentry.io

---

🎉 **You're all set!** SafeRunner is now monitoring your Sentry alerts and will automatically create PRs for bugs.
