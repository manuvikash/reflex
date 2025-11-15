# SafeRunner 🤖

**Automated bug reproduction and fixing service** that receives Sentry issue alerts, spins up isolated Daytona sandboxes to safely reproduce bugs, generates minimal fixes using Claude, and opens GitHub pull requests.

## 🎯 Features

- **Webhook Integration**: Receives Sentry "Issue Alert" webhooks with signature verification
- **Safe Reproduction**: Spins up ephemeral Daytona sandboxes with network isolation
- **AI-Powered Fixes**: Uses Claude Sonnet 4.5 to generate minimal unified diffs
- **Automated Testing**: Reproduces bugs, applies patches, and validates fixes
- **GitHub Integration**: Creates branches and pull requests automatically
- **Smart Routing**: Resolves repositories and commits from Sentry releases and tags

## 🏗️ Architecture

```
Sentry Alert → Webhook Server → Worker → Daytona Sandbox → Claude → GitHub PR
                    ↓                           ↓
              Signature Check            Reproduce Bug
                                              ↓
                                         Apply Patch
                                              ↓
                                         Run Tests
                                              ↓
                                         Create PR
```

## 📦 Installation

### Prerequisites

- Python 3.11+
- Daytona account and API key ([sign up](https://daytona.io))
- GitHub personal access token with `repo` scope
- Sentry Internal Integration webhook secret
- Anthropic API key

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd saferunner
   ```

2. **Install dependencies**
   ```bash
   make install
   # or
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Create Daytona snapshot**
   ```bash
   make snapshot
   ```
   This creates a pre-built snapshot with pytest and build dependencies.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following:

```bash
# Daytona
DAYTONA_API_KEY=your_daytona_api_key
DAYTONA_API_URL=https://app.daytona.io/api
DAYTONA_TARGET=us

# Sentry
SENTRY_WEBHOOK_SECRET=your_webhook_secret
SENTRY_AUTH_TOKEN=your_sentry_auth_token  # Optional: for release mapping

# GitHub
GITHUB_OWNER=your_github_org
GITHUB_REPO=your_repo_name
GITHUB_TOKEN=your_github_pat

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_key
ANTHROPIC_MODEL=claude-sonnet-4-5
```

### Service Routing

Edit `services.yaml` to map service names to repositories:

```yaml
my-api-service:
  repo: myorg/my-api
  path: ""  # Empty for root, or "services/api" for monorepo
  test_command: "pytest -q tests/"

my-frontend:
  repo: myorg/my-frontend
  path: ""
  test_command: "npm test"
```

## 🚀 Usage

### Start the Webhook Server

```bash
make server
# or
python -m control.server
```

The server runs on `http://0.0.0.0:8000` with endpoints:
- `GET /health` - Health check
- `POST /webhooks/sentry` - Sentry webhook receiver

### Configure Sentry Webhook

1. Go to **Settings → Developer Settings → Internal Integrations**
2. Create a new Internal Integration
3. Enable **Issue Alerts** webhook
4. Set webhook URL to `https://your-domain.com/webhooks/sentry`
5. Copy the webhook secret to your `.env` file

### Set Up Sentry Releases (Recommended)

To enable deterministic commit routing, configure Sentry releases in your CI:

```bash
# In your CI pipeline
export SENTRY_AUTH_TOKEN=your_token
export SENTRY_ORG=your_org
export SENTRY_PROJECT=your_project

# Create release and associate commits
sentry-cli releases new $VERSION
sentry-cli releases set-commits --auto $VERSION
sentry-cli releases finalize $VERSION
```

## 🔒 Security Features

### Signature Verification
All incoming webhooks are verified using HMAC-SHA256 signatures from Sentry.

### Sandbox Isolation
- **Ephemeral sandboxes**: Automatically deleted after use
- **Auto-stop**: Sandboxes stop after 20 minutes of inactivity
- **Resource limits**: CPU, memory, and disk quotas
- **Network controls**: Optional network blocking and allowlists

### Patch Guardrails
- **Path restrictions**: Only modifies `src/`, `tests/`, `app/`, `lib/`
- **Line limits**: Patches capped at 150 lines
- **No traversal**: Blocks parent directory access (`..`)
- **Forbidden paths**: Blocks system directories (`/etc`, `/root`, etc.)

## 📋 Workflow

1. **Webhook Received**: Sentry sends issue alert with error details
2. **Routing**: Resolves repository and commit from:
   - Event tags (`service`, `repo`, `monorepo_path`)
   - Release mapping (via Sentry API)
   - Fallback to `services.yaml`
3. **Sandbox Creation**: Spins up Daytona sandbox from snapshot
4. **Reproduction**: Clones repo, checks out commit, runs tests
5. **Patch Generation**: Claude analyzes error and generates minimal diff
6. **Validation**: Checks patch against safety guardrails
7. **Application**: Applies patch with `git apply`
8. **Testing**: Re-runs tests to verify fix
9. **PR Creation**: Creates branch, commits changes, opens PR
10. **Cleanup**: Stops and deletes sandbox

## 🧪 Testing

The system validates fixes by:
1. Running tests before patch (should fail)
2. Applying the patch
3. Running tests after patch (must pass)
4. Only creating PR if tests pass

## 📊 Monitoring

Logs include:
- Webhook signature verification
- Routing decisions
- Sandbox lifecycle events
- Patch generation and validation
- Test results
- PR creation status

## 🛠️ Development

### Project Structure

```
saferunner/
├── control/
│   ├── server.py          # FastAPI webhook server
│   ├── worker.py          # Main orchestration logic
│   ├── daytona_client.py  # Daytona SDK wrapper
│   ├── patcher.py         # Claude patch generation
│   ├── github_api.py      # GitHub API client
│   └── routing.py         # Repository routing
├── sandbox/
│   ├── Dockerfile.ci      # Snapshot base image
│   └── requirements.txt   # Test dependencies
├── scripts/
│   └── make_snapshot.sh   # Snapshot creation script
├── services.yaml          # Service routing config
├── requirements.txt       # Python dependencies
├── Makefile              # Common commands
└── README.md
```

### Adding New Services

1. Add service to `services.yaml`:
   ```yaml
   new-service:
     repo: org/repo
     path: ""
     test_command: "pytest -q"
   ```

2. Tag Sentry events with service name:
   ```python
   import sentry_sdk
   
   sentry_sdk.set_tag("service", "new-service")
   ```

## 🔗 API Documentation

### Daytona SDK
- [Create Sandbox](https://docs.daytona.io/api/sandbox/create)
- [Execute Commands](https://docs.daytona.io/api/sandbox/exec)
- [Git Operations](https://docs.daytona.io/api/sandbox/git)
- [Preview Links](https://docs.daytona.io/api/sandbox/preview)

### Sentry
- [Issue Alerts](https://docs.sentry.io/product/alerts/alert-types/#issue-alerts)
- [Webhooks](https://docs.sentry.io/product/integrations/integration-platform/webhooks/)
- [Releases](https://docs.sentry.io/product/releases/)

### GitHub
- [Create Pull Request](https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request)

### Anthropic
- [Messages API](https://docs.anthropic.com/en/api/messages)

## 🎯 Acceptance Criteria

✅ **Signature Verification**: Rejects invalid Sentry webhook signatures  
✅ **Deterministic Routing**: Resolves correct repo/commit from releases and tags  
✅ **Daytona Lifecycle**: Creates ephemeral sandboxes with auto-stop  
✅ **Repro + Patch Loop**: Reproduces bugs, applies fixes, validates with tests  
✅ **Guardrails**: Enforces path restrictions and line limits  
✅ **PR Creation**: Opens GitHub PRs with formatted descriptions  

## 🚧 Limitations (MVP)

- No multi-service orchestration UI
- No persistent database (logs only)
- Simple service discovery via tags/config
- Single repository per webhook

## 📝 License

MIT

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.

---

**Built with**: FastAPI • Daytona • Claude • GitHub API
