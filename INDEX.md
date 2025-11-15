# SafeRunner Documentation Index

Welcome to SafeRunner! This index will help you find the right documentation for your needs.

## 🚀 Getting Started

**New to SafeRunner? Start here:**

1. **[README.md](README.md)** - Overview, features, and basic setup
2. **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide
3. **[CHECKLIST.md](CHECKLIST.md)** - Step-by-step setup checklist

## 📚 Core Documentation

### For Users

- **[README.md](README.md)** - Main documentation
  - What is SafeRunner?
  - Key features
  - Installation instructions
  - Basic usage
  - Configuration

- **[QUICKSTART.md](QUICKSTART.md)** - Quick setup guide
  - Prerequisites
  - Installation steps
  - Configuration
  - Testing
  - Troubleshooting

- **[CHECKLIST.md](CHECKLIST.md)** - Setup checklist
  - Account setup
  - Installation verification
  - Configuration validation
  - Testing steps
  - Go-live checklist

### For Developers

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design
  - Component overview
  - Data flow
  - Security model
  - Performance characteristics
  - Extension points

- **[SYSTEM_FLOW.md](SYSTEM_FLOW.md)** - End-to-end flow
  - Step-by-step process
  - Visual diagrams
  - Timeline and duration
  - Error handling
  - Monitoring points

- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Implementation details
  - Deliverables checklist
  - API usage examples
  - Testing guide
  - Customization options

### For Operations

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment
  - Deployment options (systemd, Docker, cloud)
  - Security best practices
  - Monitoring and logging
  - Scaling considerations
  - Troubleshooting

## 📁 Code Documentation

### Main Components

| File | Purpose | Key Functions |
|------|---------|---------------|
| `control/server.py` | Webhook server | `sentry_webhook()`, `verify_sentry_signature()` |
| `control/worker.py` | Orchestration | `process_sentry_alert()` |
| `control/routing.py` | Repo resolution | `resolve_route()`, `get_release_commits()` |
| `control/daytona_client.py` | Sandbox management | `create_sandbox()`, `exec_command()`, `clone_repo()` |
| `control/patcher.py` | Patch generation | `generate_patch()`, `validate_patch()` |
| `control/github_api.py` | GitHub integration | `create_pull_request()`, `format_pr_body()` |

### Configuration Files

| File | Purpose |
|------|---------|
| `.env.example` | Environment variable template |
| `services.yaml` | Service routing configuration |
| `requirements.txt` | Python dependencies |
| `Makefile` | Common commands |

### Sandbox Files

| File | Purpose |
|------|---------|
| `sandbox/Dockerfile.ci` | Base image for snapshots |
| `sandbox/requirements.txt` | Test dependencies |

### Scripts

| File | Purpose |
|------|---------|
| `scripts/make_snapshot.sh` | Create Daytona snapshot |
| `scripts/dev_setup.sh` | Development environment setup |
| `scripts/test_integration.sh` | Integration testing |

### Examples

| File | Purpose |
|------|---------|
| `examples/test_webhook.py` | Test webhook locally |
| `examples/sample_buggy_app.py` | Sample application with bugs |
| `examples/test_sample_app.py` | Sample test file |

### Tests

| File | Purpose |
|------|---------|
| `tests/test_patcher.py` | Unit tests for patcher |

## 🎯 Quick Links by Task

### I want to...

#### Set up SafeRunner
→ [QUICKSTART.md](QUICKSTART.md) + [CHECKLIST.md](CHECKLIST.md)

#### Understand how it works
→ [ARCHITECTURE.md](ARCHITECTURE.md) + [SYSTEM_FLOW.md](SYSTEM_FLOW.md)

#### Deploy to production
→ [DEPLOYMENT.md](DEPLOYMENT.md)

#### Configure service routing
→ [README.md#configuration](README.md) + `services.yaml`

#### Test the webhook
→ `examples/test_webhook.py`

#### Debug an issue
→ [QUICKSTART.md#troubleshooting](QUICKSTART.md) + [DEPLOYMENT.md#troubleshooting](DEPLOYMENT.md)

#### Customize the system
→ [ARCHITECTURE.md#extension-points](ARCHITECTURE.md) + [PROJECT_SUMMARY.md#customization](PROJECT_SUMMARY.md)

#### Monitor in production
→ [DEPLOYMENT.md#monitoring--logging](DEPLOYMENT.md)

#### Understand the API calls
→ [PROJECT_SUMMARY.md#api-usage](PROJECT_SUMMARY.md)

#### See the complete flow
→ [SYSTEM_FLOW.md](SYSTEM_FLOW.md)

## 📖 Documentation by Role

### Product Manager / Stakeholder
1. [README.md](README.md) - Overview and features
2. [SYSTEM_FLOW.md](SYSTEM_FLOW.md) - How it works
3. [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - What's implemented

### Developer / Engineer
1. [QUICKSTART.md](QUICKSTART.md) - Get started quickly
2. [ARCHITECTURE.md](ARCHITECTURE.md) - System design
3. [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Implementation details
4. Code files in `control/` directory

### DevOps / SRE
1. [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment options
2. [CHECKLIST.md](CHECKLIST.md) - Setup verification
3. [ARCHITECTURE.md#monitoring](ARCHITECTURE.md) - Monitoring

### QA / Tester
1. [QUICKSTART.md](QUICKSTART.md) - Setup test environment
2. `examples/` - Test utilities
3. `tests/` - Unit tests

## 🔍 Documentation by Topic

### Security
- [ARCHITECTURE.md#security-model](ARCHITECTURE.md)
- [DEPLOYMENT.md#security-best-practices](DEPLOYMENT.md)
- `control/server.py` - Signature verification
- `control/patcher.py` - Guardrails

### Configuration
- [README.md#configuration](README.md)
- `.env.example` - Environment variables
- `services.yaml` - Service routing

### API Integration
- [PROJECT_SUMMARY.md#api-usage](PROJECT_SUMMARY.md)
- `control/daytona_client.py` - Daytona SDK
- `control/patcher.py` - Anthropic API
- `control/github_api.py` - GitHub API

### Testing
- [QUICKSTART.md#testing](QUICKSTART.md)
- `examples/test_webhook.py`
- `tests/test_patcher.py`
- `scripts/test_integration.sh`

### Troubleshooting
- [QUICKSTART.md#troubleshooting](QUICKSTART.md)
- [DEPLOYMENT.md#troubleshooting](DEPLOYMENT.md)
- [CHECKLIST.md#troubleshooting](CHECKLIST.md)

## 📊 Diagrams and Visuals

- **System Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Complete Flow**: [SYSTEM_FLOW.md](SYSTEM_FLOW.md)
- **File Structure**: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

## 🔗 External Resources

### Daytona
- [Official Documentation](https://docs.daytona.io)
- [SDK Reference](https://docs.daytona.io/api)
- [Sandbox API](https://docs.daytona.io/api/sandbox)

### Sentry
- [Issue Alerts](https://docs.sentry.io/product/alerts/alert-types/#issue-alerts)
- [Webhooks](https://docs.sentry.io/product/integrations/integration-platform/webhooks/)
- [Releases](https://docs.sentry.io/product/releases/)

### Anthropic (Claude)
- [Messages API](https://docs.anthropic.com/en/api/messages)
- [Models Overview](https://docs.anthropic.com/en/docs/models-overview)

### GitHub
- [REST API](https://docs.github.com/en/rest)
- [Pull Requests](https://docs.github.com/en/rest/pulls/pulls)

## 🆘 Getting Help

### Common Issues
1. Check [QUICKSTART.md#troubleshooting](QUICKSTART.md)
2. Review [CHECKLIST.md](CHECKLIST.md) for missed steps
3. See [DEPLOYMENT.md#troubleshooting](DEPLOYMENT.md)

### Still Stuck?
1. Check server logs
2. Verify environment variables
3. Test individual components
4. Open a GitHub issue

## 📝 Contributing

Want to improve SafeRunner?

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system
2. Check [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for implementation details
3. Add tests for new features
4. Update relevant documentation
5. Submit a pull request

## 🗂️ File Organization

```
saferunner/
├── 📘 Documentation (you are here)
│   ├── INDEX.md              ← You are here
│   ├── README.md             ← Start here
│   ├── QUICKSTART.md         ← Setup guide
│   ├── CHECKLIST.md          ← Setup checklist
│   ├── ARCHITECTURE.md       ← System design
│   ├── SYSTEM_FLOW.md        ← Process flow
│   ├── PROJECT_SUMMARY.md    ← Implementation
│   └── DEPLOYMENT.md         ← Production guide
│
├── 💻 Source Code
│   └── control/              ← Main application
│       ├── server.py
│       ├── worker.py
│       ├── daytona_client.py
│       ├── patcher.py
│       ├── github_api.py
│       └── routing.py
│
├── 🧪 Testing
│   ├── tests/                ← Unit tests
│   └── examples/             ← Examples & utilities
│
├── 🔧 Configuration
│   ├── .env.example          ← Environment template
│   ├── services.yaml         ← Service routing
│   └── requirements.txt      ← Dependencies
│
├── 🐳 Sandbox
│   └── sandbox/              ← Docker & dependencies
│
└── 📜 Scripts
    └── scripts/              ← Automation scripts
```

## 🎓 Learning Path

### Beginner
1. Read [README.md](README.md)
2. Follow [QUICKSTART.md](QUICKSTART.md)
3. Use [CHECKLIST.md](CHECKLIST.md)
4. Test with `examples/test_webhook.py`

### Intermediate
1. Study [ARCHITECTURE.md](ARCHITECTURE.md)
2. Review [SYSTEM_FLOW.md](SYSTEM_FLOW.md)
3. Explore code in `control/`
4. Customize `services.yaml`

### Advanced
1. Read [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
2. Study [DEPLOYMENT.md](DEPLOYMENT.md)
3. Implement custom extensions
4. Contribute improvements

## 📅 Version History

- **v1.0.0** (2024) - Initial release
  - Complete implementation
  - Full documentation
  - Production ready

## 📄 License

MIT - See repository for details

---

**Need help finding something?** Use your editor's search (Ctrl+F / Cmd+F) to search across all documentation files.

**Quick command reference:**
```bash
make install    # Install dependencies
make snapshot   # Create Daytona snapshot
make server     # Start webhook server
make test       # Run tests
make clean      # Clean up
```

**Happy bug fixing! 🤖**
