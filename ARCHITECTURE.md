# SafeRunner Architecture

## System Overview

SafeRunner is a microservice that automates bug fixing by integrating Sentry error monitoring, Daytona sandboxes, Claude AI, and GitHub.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Production App                            │
│                    (with Sentry SDK)                            │
└────────────────────────────┬────────────────────────────────────┘
                             │ Error occurs
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Sentry.io                                │
│  • Captures error                                               │
│  • Triggers issue alert                                         │
│  • Sends webhook with HMAC signature                           │
└────────────────────────────┬────────────────────────────────────┘
                             │ POST /webhooks/sentry
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SafeRunner Server                             │
│                      (FastAPI)                                  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Verify HMAC-SHA256 signature                         │  │
│  │  2. Parse webhook payload                                │  │
│  │  3. Queue background task                                │  │
│  │  4. Return 200 OK immediately                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ Background task
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Worker Process                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ROUTING (routing.py)                                    │  │
│  │  • Check event tags (service, repo, monorepo_path)      │  │
│  │  • Query Sentry Releases API for commit SHA             │  │
│  │  • Fallback to services.yaml config                     │  │
│  │  • Default to main branch                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  SANDBOX CREATION (daytona_client.py)                   │  │
│  │  • Create from snapshot "saferunner-ci"                 │  │
│  │  • Set resources: 2 CPU, 4GB RAM, 10GB disk            │  │
│  │  • Enable ephemeral mode (auto-delete on stop)         │  │
│  │  • Set auto-stop: 20 minutes                           │  │
│  │  • Optional: network restrictions                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  REPRODUCTION (daytona_client.py)                       │  │
│  │  • Clone repo via Git (HTTPS with token)                │  │
│  │  • Checkout specific commit/branch                      │  │
│  │  • Run test command (pytest -q)                         │  │
│  │  • Capture stdout/stderr                                │  │
│  │  • Verify tests fail (reproduce bug)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  PATCH GENERATION (patcher.py)                          │  │
│  │  • Call Claude Sonnet 4.5 API                           │  │
│  │  • Provide: error, stack trace, test output            │  │
│  │  • Request: minimal unified diff                        │  │
│  │  • Extract diff from response                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  VALIDATION (patcher.py)                                │  │
│  │  • Check line count (max 150 lines)                     │  │
│  │  • Verify paths (only src/, tests/, app/, lib/)        │  │
│  │  • Block forbidden paths (/etc, /root, etc.)           │  │
│  │  • Reject parent traversal (..)                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  APPLICATION (daytona_client.py)                        │  │
│  │  • Write patch to /tmp/patch.diff                       │  │
│  │  • Run: git apply --whitespace=fix                      │  │
│  │  • Verify application succeeded                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  VERIFICATION (daytona_client.py)                       │  │
│  │  • Re-run test command                                  │  │
│  │  • Check exit code == 0                                 │  │
│  │  • Abort if tests still fail                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  PR CREATION (github_api.py)                            │  │
│  │  • Configure git user                                    │  │
│  │  • Create branch: saferunner/fix-{id}-{timestamp}      │  │
│  │  • Commit changes                                        │  │
│  │  • Push to GitHub                                        │  │
│  │  • Create PR via REST API                               │  │
│  │  • Format body with issue details                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CLEANUP (daytona_client.py)                            │  │
│  │  • Stop sandbox                                          │  │
│  │  • Ephemeral sandbox auto-deleted                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                          GitHub                                  │
│  • New branch created                                           │
│  • Pull request opened                                          │
│  • Team notified for review                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Webhook Server (`control/server.py`)

**Responsibilities:**
- Receive Sentry webhooks
- Verify HMAC-SHA256 signatures
- Queue background processing
- Return fast responses (< 1s)

**Security:**
- HMAC signature verification prevents unauthorized requests
- Only processes valid Sentry Internal Integration webhooks

**Endpoints:**
- `GET /health` - Health check
- `POST /webhooks/sentry` - Webhook receiver

### 2. Routing (`control/routing.py`)

**Responsibilities:**
- Resolve repository URL
- Determine commit/branch
- Find monorepo subpath
- Select test command

**Resolution Priority:**
1. **Event tags** - Explicit tags in Sentry event
2. **Release mapping** - Query Sentry API for release commits
3. **Config file** - `services.yaml` fallback
4. **Defaults** - Environment variables

**Data Flow:**
```python
Sentry Event → Tags → Release API → services.yaml → Defaults
                ↓
        RouteInfo(repo_url, commitish, subpath, test_command)
```

### 3. Daytona Client (`control/daytona_client.py`)

**Responsibilities:**
- Manage sandbox lifecycle
- Execute commands safely
- Handle Git operations
- Provide preview links

**Sandbox Configuration:**
```python
{
    "snapshot": "saferunner-ci",
    "ephemeral": True,
    "auto_stop_interval": 20,  # minutes
    "resources": {
        "cpu": 2,
        "memory": 4,  # GB
        "disk": 10    # GB
    }
}
```

**Safety Features:**
- Ephemeral sandboxes (auto-delete)
- Resource limits
- Auto-stop on idle
- Optional network restrictions

### 4. Patcher (`control/patcher.py`)

**Responsibilities:**
- Generate patches via Claude
- Validate patch safety
- Extract diff from responses
- Provide patch summaries

**Claude Prompt Strategy:**
```
System: You are a senior engineer. Return ONLY unified diff.
        Keep changes minimal. Cap to ~80 lines.
        Only modify src/, tests/, app/, lib/.

User: Fix this bug:
      ERROR: {error_message}
      STACK TRACE: {stack_trace}
      TEST OUTPUT: {test_output}
```

**Guardrails:**
- Max 150 lines per patch
- Only allowed paths (src/, tests/, app/, lib/)
- No forbidden paths (/etc, /root, /sys, etc.)
- No parent traversal (..)
- Unified diff format validation

### 5. GitHub Client (`control/github_api.py`)

**Responsibilities:**
- Create branches
- Commit changes
- Push to remote
- Open pull requests
- Request reviewers

**PR Format:**
```markdown
## 🤖 Automated Fix for Sentry Issue

**Issue:** [Title](URL)
**Sentry ID:** `12345`

### Changes
- Files modified: 2
- Additions: +5 lines
- Deletions: -2 lines

### Modified Files
- `src/main.py`
- `tests/test_main.py`

### Testing
✅ Tests passed in isolated Daytona sandbox
```

### 6. Worker (`control/worker.py`)

**Responsibilities:**
- Orchestrate entire flow
- Handle errors gracefully
- Log progress
- Cleanup resources

**Error Handling:**
- Catches `PatcherError` for patch failures
- Catches `GitHubAPIError` for PR failures
- Always cleans up sandbox in `finally` block
- Logs all errors with context

## Data Models

### RouteInfo
```python
@dataclass
class RouteInfo:
    repo_url: str        # Git clone URL with token
    commitish: str       # Branch name or commit SHA
    subpath: str         # Monorepo path (empty for root)
    test_command: str    # Command to run tests
```

### Sentry Webhook Payload
```json
{
  "action": "triggered",
  "data": {
    "issue": {
      "id": "12345",
      "title": "Error message",
      "permalink": "https://sentry.io/..."
    },
    "event": {
      "event_id": "abc123",
      "title": "Error message",
      "release": "v1.0.0",
      "tags": [
        {"key": "service", "value": "my-api"},
        {"key": "repo", "value": "org/repo"}
      ],
      "exception": {...}
    }
  }
}
```

## Security Model

### Defense in Depth

1. **Network Layer**
   - HMAC signature verification
   - HTTPS only in production
   - Rate limiting (recommended)

2. **Sandbox Layer**
   - Isolated ephemeral environments
   - Resource quotas
   - Network restrictions (optional)
   - Auto-stop and auto-delete

3. **Code Layer**
   - Path validation
   - Line count limits
   - Forbidden path blocking
   - No arbitrary command execution

4. **Git Layer**
   - Token-based authentication
   - Branch naming convention
   - Commit signing (optional)

### Threat Model

**Mitigated Threats:**
- ✅ Unauthorized webhooks (signature verification)
- ✅ Path traversal attacks (validation)
- ✅ Resource exhaustion (quotas + auto-stop)
- ✅ System file modification (path restrictions)
- ✅ Network attacks (optional blocking)

**Remaining Risks:**
- ⚠️ Malicious patches from Claude (human review required)
- ⚠️ Test command injection (whitelist commands)
- ⚠️ Credential exposure (use secrets management)

## Performance Characteristics

### Latency
- Webhook response: < 100ms
- Total processing: 2-5 minutes
  - Sandbox creation: 30-60s
  - Git clone: 10-30s
  - Test run: 30-120s
  - Claude API: 10-30s
  - PR creation: 5-10s

### Scalability
- Horizontal: Run multiple server instances
- Vertical: Increase sandbox resources
- Bottleneck: Daytona sandbox creation rate

### Resource Usage
- Server: ~100MB RAM, minimal CPU
- Sandbox: 2 CPU, 4GB RAM, 10GB disk per job
- Network: ~100MB per job (git clone + dependencies)

## Monitoring & Observability

### Logs
- Structured logging with timestamps
- Log levels: INFO, WARNING, ERROR
- Context: issue_id, sandbox_id, repo

### Metrics (Recommended)
- Webhooks received
- Webhooks processed successfully
- Patches generated
- PRs created
- Processing time (p50, p95, p99)
- Sandbox creation time
- Test pass rate

### Alerts (Recommended)
- Webhook signature failures
- Sandbox creation failures
- High processing time (> 10 min)
- PR creation failures

## Deployment Architecture

### Development
```
Local Machine
├── FastAPI server (port 8000)
├── ngrok tunnel (HTTPS)
└── Daytona sandboxes (cloud)
```

### Production
```
Cloud Platform (AWS/GCP/Azure)
├── Load Balancer (HTTPS)
├── SafeRunner Instances (auto-scaling)
│   ├── FastAPI server
│   └── Worker threads
├── Secrets Manager
│   ├── DAYTONA_API_KEY
│   ├── GITHUB_TOKEN
│   └── ANTHROPIC_API_KEY
└── Daytona Sandboxes (ephemeral)
```

## Extension Points

### Custom Routing
Implement custom routing logic in `routing.py`:
```python
def custom_route_resolver(payload):
    # Your logic here
    return RouteInfo(...)
```

### Custom Patch Validation
Add custom validators in `patcher.py`:
```python
def validate_custom_rules(patch):
    # Your validation logic
    pass
```

### Custom PR Formatting
Extend `github_api.py`:
```python
def format_pr_body_custom(issue, patch, extra_data):
    # Your formatting logic
    return body
```

## Future Enhancements

1. **Database** - Store run history and metrics
2. **UI Dashboard** - View processing status
3. **Multi-repo** - Handle multiple repos per webhook
4. **Rollback** - Auto-revert failed PRs
5. **Learning** - Improve patches based on feedback
6. **Integration Tests** - Run full test suite before PR
7. **Cost Tracking** - Monitor Daytona/Claude usage
8. **Slack Notifications** - Alert team of PRs
