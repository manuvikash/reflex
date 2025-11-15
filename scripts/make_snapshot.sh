#!/bin/bash
# Create Daytona snapshot from Dockerfile

set -e

echo "Creating Daytona snapshot 'saferunner-ci' from Dockerfile..."

cd "$(dirname "$0")/.."

# Build and create snapshot using Daytona CLI
# The snapshot name is a positional argument, not a flag
daytona snapshot create saferunner-ci \
  --dockerfile ./sandbox/Dockerfile.ci \
  --context ./sandbox

echo "✅ Snapshot 'saferunner-ci' created successfully"
echo "You can now use this snapshot to create sandboxes"
