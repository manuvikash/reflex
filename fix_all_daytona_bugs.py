#!/usr/bin/env python3
"""Fix all daytona_sdk import bugs."""
import os
import sys
import site

# Find the site-packages directory
site_packages = site.getsitepackages()
print(f"Searching in site-packages: {site_packages}")

# Look for daytona_sdk in venv
venv_site_packages = None
for sp in site_packages:
    if 'venv' in sp or 'site-packages' in sp:
        venv_site_packages = sp
        break

# Also check sys.path for venv location
if not venv_site_packages:
    for path in sys.path:
        if 'venv' in path and 'site-packages' in path:
            venv_site_packages = path
            break

if not venv_site_packages:
    print("❌ Could not find venv site-packages")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

sdk_dir = os.path.join(venv_site_packages, 'daytona_sdk')

if not os.path.exists(sdk_dir):
    print(f"❌ Directory not found: {sdk_dir}")
    sys.exit(1)

print(f"✓ Found SDK directory: {sdk_dir}\n")

# List of files to fix and their replacements
fixes = [
    {
        'file': '__init__.py',
        'replacements': [
            ('from daytona_api_client import WorkspaceState as SandboxState',
             'from daytona_api_client import SandboxState'),
        ]
    },
    {
        'file': 'sandbox.py',
        'replacements': [
            ('from daytona_api_client import WorkspaceInfo as ApiSandboxInfo',
             'from daytona_api_client import SandboxInfo as ApiSandboxInfo'),
            ('from daytona_api_client import WorkspaceState',
             'from daytona_api_client import SandboxState'),
        ]
    },
    {
        'file': 'daytona.py',
        'replacements': [
            ('from daytona_api_client import WorkspaceState',
             'from daytona_api_client import SandboxState'),
            ('self.sandbox_api.create_workspace(',
             'self.sandbox_api.create_sandbox('),
            ('self.workspace_api',
             'self.sandbox_api'),
        ]
    },
]

total_fixes = 0

for fix_info in fixes:
    file_path = os.path.join(sdk_dir, fix_info['file'])

    if not os.path.exists(file_path):
        print(f"⚠️  Skipping {fix_info['file']} (not found)")
        continue

    print(f"📝 Processing {fix_info['file']}...")

    try:
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()

        original_content = content
        file_fixes = 0

        # Apply all replacements
        for old_text, new_text in fix_info['replacements']:
            if old_text in content:
                content = content.replace(old_text, new_text)
                file_fixes += 1
                print(f"   ✓ Fixed: {old_text[:60]}...")

        # Write back if changes were made
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"   ✅ Saved {file_fixes} fix(es) to {fix_info['file']}\n")
            total_fixes += file_fixes
        else:
            print(f"   ℹ️  No fixes needed in {fix_info['file']}\n")

    except Exception as e:
        print(f"   ❌ Error processing {fix_info['file']}: {e}\n")

print("=" * 60)
if total_fixes > 0:
    print(f"✅ Applied {total_fixes} fix(es) total!")
    print("\nNow try running: make server")
else:
    print("ℹ️  No fixes were needed (already fixed or different SDK version)")
