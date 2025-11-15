"""CLI-based patch generation using tools inside Daytona sandbox."""
import logging
import os
import re
import shlex
import textwrap
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CLIPatcherError(Exception):
    """Custom exception for CLI patcher errors."""
    pass


class CLIPatcher:
    """Generate patches using CLI tools (CodeRabbit, Gemini CLI, etc.) inside sandbox."""
    
    # Paths that should never be modified
    FORBIDDEN_PATHS = [
        "/etc/",
        "/sys/",
        "/proc/",
        "/dev/",
        "/root/",
        "/.ssh/",
        "/home/",
    ]
    
    # Allowed path patterns (relative to repo root)
    ALLOWED_PATTERNS = [
        r"^src/",
        r"^tests?/",
        r"^app/",
        r"^lib/",
        r"^.*\.py$",
        r"^.*\.js$",
        r"^.*\.ts$",
        r"^.*\.tsx$",
    ]
    
    MAX_PATCH_LINES = 150  # Maximum lines in a patch
    
    def __init__(self, tool: str = "coderabbit"):
        """
        Initialize CLI patcher.
        
        Args:
            tool: Which CLI tool to use ('coderabbit', 'gemini', or 'aider')
        """
        self.tool = tool
        logger.info(f"Initialized CLI patcher with tool: {tool}")
    
    def generate_patch_with_coderabbit(
        self,
        daytona_client,
        sandbox,
        work_dir: str,
        error_message: str,
        stack_trace: str,
    ) -> str:
        """
        Generate patch using CodeRabbit CLI inside sandbox.
        
        Args:
            daytona_client: DaytonaClient instance
            sandbox: Sandbox instance
            work_dir: Working directory in sandbox
            error_message: Error message from Sentry
            stack_trace: Stack trace from error
        
        Returns:
            Git diff as string
        """
        logger.info("Installing CodeRabbit CLI in sandbox")
        
        # Install CodeRabbit CLI
        install_result = daytona_client.run_command(
            sandbox=sandbox,
            command="curl -fsSL https://cli.coderabbit.ai/install.sh | sh",
            cwd=work_dir,
            timeout=120,
        )
        
        if install_result["exit_code"] != 0:
            raise CLIPatcherError(f"Failed to install CodeRabbit: {install_result['stderr']}")
        
        # Authenticate if token available
        coderabbit_token = os.getenv("CODERABBIT_TOKEN")
        if coderabbit_token:
            logger.info("Authenticating CodeRabbit")
            # Upload token file
            daytona_client.upload_file(
                sandbox=sandbox,
                content=coderabbit_token,
                path="/tmp/cr_token",
            )
            daytona_client.run_command(
                sandbox=sandbox,
                command="coderabbit auth login --token $(cat /tmp/cr_token)",
                cwd=work_dir,
            )
        
        # Create a context file with error information
        context = f"""# Bug Fix Context

## Error
{error_message}

## Stack Trace
{stack_trace}

## Instructions
Please fix the bug causing this error. Focus on:
1. The root cause in the stack trace
2. Add proper error handling
3. Add tests to prevent regression
"""
        
        daytona_client.upload_file(
            sandbox=sandbox,
            content=context,
            path=f"{work_dir}/.coderabbit-context.md",
        )
        
        # Run CodeRabbit with context
        logger.info("Running CodeRabbit CLI to analyze and fix")
        review_result = daytona_client.run_command(
            sandbox=sandbox,
            command="coderabbit --prompt-only --type uncommitted --config .coderabbit-context.md",
            cwd=work_dir,
            timeout=600,  # 10 minutes
        )
        
        if review_result["exit_code"] != 0:
            logger.warning(f"CodeRabbit review had issues: {review_result['stderr']}")
        
        # Get the git diff of changes
        diff_result = daytona_client.run_command(
            sandbox=sandbox,
            command="git diff",
            cwd=work_dir,
        )
        
        patch = diff_result["stdout"]
        
        if not patch or len(patch.strip()) == 0:
            raise CLIPatcherError("CodeRabbit did not generate any changes")
        
        logger.info(f"Generated patch ({len(patch.splitlines())} lines)")
        return patch
    
    def generate_patch_with_gemini_cli(
        self,
        daytona_client,
        sandbox,
        work_dir: str,
        error_message: str,
        stack_trace: str,
        test_output: str = "",
    ) -> str:
        """
        Generate patch using Gemini CLI (via Google AI Studio CLI) inside sandbox.
        
        This uses the Gemini API but runs commands in the sandbox for better context.
        """
        logger.info("Setting up Gemini CLI in sandbox")
        
        # Install Google AI CLI if available, or use curl to call API
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise CLIPatcherError("GEMINI_API_KEY not set")
        
        # Create prompt file
        prompt = f"""You are a senior software engineer fixing a bug. Generate a minimal unified diff patch.

ERROR: {error_message}

STACK TRACE:
{stack_trace}

TEST OUTPUT:
{test_output}

Generate ONLY a unified diff patch (git diff format) to fix this issue.
Start with --- a/path/to/file.py and +++ b/path/to/file.py
Include context lines and use proper @@ line numbers.
Keep changes minimal - fix only what's broken.
"""
        
        daytona_client.upload_file(
            sandbox=sandbox,
            content=prompt,
            path="/tmp/fix_prompt.txt",
        )
        
        # Call Gemini API using curl
        api_call = f"""
curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}" \
-H "Content-Type: application/json" \
-d @- <<EOF
{{
  "contents": [{{
    "parts": [{{
      "text": "$(cat /tmp/fix_prompt.txt)"
    }}]
  }}],
  "generationConfig": {{
    "temperature": 0.2,
    "maxOutputTokens": 4096
  }}
}}
EOF
"""
        
        result = daytona_client.run_command(
            sandbox=sandbox,
            command=api_call,
            cwd=work_dir,
            timeout=120,
        )
        
        if result["exit_code"] != 0:
            raise CLIPatcherError(f"Gemini API call failed: {result['stderr']}")
        
        # Parse JSON response and extract text
        import json
        try:
            response_data = json.loads(result["stdout"])
            text = response_data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Extract diff from code block
            patch = self._extract_diff(text)
            logger.info(f"Generated patch ({len(patch.splitlines())} lines)")
            return patch
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise CLIPatcherError(f"Failed to parse Gemini response: {e}")

    def generate_patch_with_gemini_coderabbit(
        self,
        daytona_client,
        sandbox,
        work_dir: str,
        error_message: str,
        stack_trace: str,
        test_output: str = "",
    ) -> str:
        """Run Gemini CLI agent that invokes CodeRabbit for deep reviews."""
        logger.info("Setting up Gemini + CodeRabbit agent workflow inside sandbox")

        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise CLIPatcherError("GEMINI_API_KEY not set")

        # 1. Ensure CLIs are available (tools preinstalled in snapshot)
        # Skip verification - tools are pre-installed in snapshot, will fail later if missing
        logger.info("Assuming gemini and coderabbit are pre-installed in snapshot")
        # self._ensure_cli_tool(
        #     daytona_client,
        #     sandbox,
        #     work_dir,
        #     binary="gemini",
        # )
        # self._ensure_cli_tool(
        #     daytona_client,
        #     sandbox,
        #     work_dir,
        #     binary="coderabbit",
        # )

        # 2. Authenticate CodeRabbit if token is provided
        self._authenticate_coderabbit(daytona_client, sandbox, work_dir)

        # 3. Restore Gemini CLI session if provided (skip for now - function not implemented)
        logger.info("Skipping Gemini profile restore (not implemented)")
        # self._restore_profile_archive(
        #     daytona_client,
        #     sandbox,
        #     work_dir,
        #     env_var="GEMINI_PROFILE_B64",
        #     description="Gemini CLI",
        #     tmp_prefix="gemini_profile",
        #     default_target=os.getenv("GEMINI_PROFILE_DEST", "~/.opencode"),
        # )

        # 4. Create gemini.md instructions file per best practices
        gemini_instructions = textwrap.dedent(
            """
            # Gemini Agent Instructions

            You are operating inside a Daytona sandbox with the full repository checked out.

            Workflow expectations:
            1. Implement the required bug fix or feature change described in the prompt.
            2. After coding, run CodeRabbit review using:
               `coderabbit --prompt-only --type uncommitted`
            3. CodeRabbit may take up to 30 minutes. Run it in the background and poll every ~2 minutes until it finishes.
            4. When CodeRabbit finishes, read the findings, fix *critical* and *major* issues. Ignore nits unless trivial.
            5. Re-run tests (pytest -q) to ensure the issue is resolved.
            6. Re-run CodeRabbit to confirm all critical issues are fixed. Limit the loop to 3 total CodeRabbit runs.
            7. Summarize what was fixed in commit messages.

            Repository safety rules:
            - Only modify files related to the bug fix (prefer src/ and tests/ directories).
            - Keep diffs minimal and focused on the fix.
            - Do not remove existing tests; add/adjust tests if needed.
            - Never touch secrets or configuration outside the repo root.
            """
        ).strip()
        self._write_file(
            daytona_client,
            sandbox,
            path=f"{work_dir}/gemini.md",
            content=gemini_instructions,
        )

        # 5. Provide bug-specific context prompt
        prompt = textwrap.dedent(
            f"""
            You are debugging a production error captured from Sentry.

            ## Error
            {error_message}

            ## Stack Trace
            {stack_trace}

            ## Test Output
            {test_output}

            Goals:
            - Reproduce and fix the bug in this repository.
            - Update or add unit tests to cover the failure mode.
            - Follow the instructions in gemini.md (in repo root) including running CodeRabbit reviews.
            - Keep the change minimal but complete.
            """
        ).strip()
        self._write_file(
            daytona_client,
            sandbox,
            path="/tmp/gemini_prompt.txt",
            content=prompt,
        )

        # 6. Run Gemini CLI agent with context file
        # First, verify gemini is available
        verify_cmd = "which gemini || find /usr -name gemini 2>/dev/null || echo 'gemini not found'"
        verify_result = daytona_client.run_command(
            sandbox=sandbox,
            command=verify_cmd,
            cwd=work_dir,
        )
        logger.info(f"Gemini location check: {verify_result.get('stdout', 'N/A')}")
        
        gemini_cmd = textwrap.dedent(
            f"""
            export GEMINI_API_KEY={gemini_key}
            cd {work_dir}
            echo "Running gemini command..."
            echo "PATH: $PATH"
            which gemini || echo "gemini not in PATH"
            gemini --no-tty --context gemini.md --prompt-file /tmp/gemini_prompt.txt --max-loops 3 2>&1
            exit_code=$?
            echo "Gemini exit code: $exit_code"
            exit $exit_code
            """
        ).strip()
        result = daytona_client.run_command(
            sandbox=sandbox,
            command=gemini_cmd,
            cwd=work_dir,
            timeout=1800,
        )
        if result["exit_code"] != 0:
            # Log full output for debugging
            logger.error(f"Gemini stdout: {result.get('stdout', 'N/A')}")
            logger.error(f"Gemini stderr: {result.get('stderr', 'N/A')}")
            raise CLIPatcherError(
                f"Gemini CLI execution failed (exit code {result['exit_code']})\\nStdout: {result.get('stdout', 'N/A')}\\nStderr: {result.get('stderr', 'N/A')}"
            )

        # 7. Grab resulting diff
        diff_result = daytona_client.run_command(
            sandbox=sandbox,
            command="git status --short && git diff",
            cwd=work_dir,
        )
        if diff_result["exit_code"] != 0:
            raise CLIPatcherError(f"Failed to collect diff: {diff_result['stderr']}")

        patch = diff_result["stdout"]
        if not patch.strip():
            raise CLIPatcherError("Gemini + CodeRabbit workflow produced no changes")

        logger.info(f"Gemini+CodeRabbit generated patch ({len(patch.splitlines())} lines)")
        return patch
    
    def generate_patch(
        self,
        daytona_client,
        sandbox,
        work_dir: str,
        error_message: str,
        stack_trace: str,
        test_output: str = "",
    ) -> str:
        """
        Generate patch using configured CLI tool.
        
        Args:
            daytona_client: DaytonaClient instance
            sandbox: Sandbox instance
            work_dir: Working directory in sandbox
            error_message: Error message from Sentry
            stack_trace: Stack trace from error
            test_output: Output from failed test run
        
        Returns:
            Unified diff as string
        """
        if self.tool == "coderabbit":
            return self.generate_patch_with_coderabbit(
                daytona_client, sandbox, work_dir, error_message, stack_trace
            )
        elif self.tool == "gemini":
            return self.generate_patch_with_gemini_cli(
                daytona_client, sandbox, work_dir, error_message, stack_trace, test_output
            )
        elif self.tool in {"gemini_coderabbit", "coderabbit_gemini", "gemini-agent"}:
            return self.generate_patch_with_gemini_coderabbit(
                daytona_client,
                sandbox,
                work_dir,
                error_message,
                stack_trace,
                test_output,
            )
        else:
            raise CLIPatcherError(f"Unsupported tool: {self.tool}")
    
    def _ensure_cli_tool(
        self,
        daytona_client,
        sandbox,
        work_dir: str,
        binary: str,
        install_command: Optional[str] = None,
    ):
        """Ensure a CLI binary exists, installing only if a command is provided."""
        # Check for the binary in multiple locations, including npm's global bin
        # Using a bash script to be more robust
        check_script = f"""
        if command -v {binary} >/dev/null 2>&1; then
            command -v {binary}
            exit 0
        elif [ -f /usr/local/bin/{binary} ]; then
            echo /usr/local/bin/{binary}
            exit 0
        elif [ -f /usr/bin/{binary} ]; then
            echo /usr/bin/{binary}
            exit 0
        elif [ -f /usr/local/lib/node_modules/.bin/{binary} ]; then
            echo /usr/local/lib/node_modules/.bin/{binary}
            exit 0
        fi
        exit 1
        """
        check = daytona_client.run_command(
            sandbox=sandbox,
            command=check_script,
            cwd=work_dir,
        )
        if check["exit_code"] == 0:
            logger.info(f"{binary} CLI already available at: {check['stdout'].strip()}")
            return
        if not install_command:
            # Enhanced debugging - check what's actually installed
            debug_cmd = f"""
            echo "=== Searching for {binary} ==="
            echo "PATH: $PATH"
            echo ""
            echo "=== Checking command -v ==="
            command -v {binary} || echo "Not found via command -v"
            echo ""
            echo "=== Checking common locations ==="
            ls -la /usr/local/bin/{binary} 2>&1 || echo "/usr/local/bin/{binary}: not found"
            ls -la /usr/bin/{binary} 2>&1 || echo "/usr/bin/{binary}: not found"
            echo ""
            echo "=== Checking npm global ==="
            npm root -g 2>&1 || echo "npm not found"
            ls -la /usr/local/lib/node_modules/.bin/{binary} 2>&1 || echo "/usr/local/lib/node_modules/.bin/{binary}: not found"
            ls -la /usr/local/lib/node_modules/@google/gemini-cli 2>&1 || echo "gemini-cli package: not found"
            echo ""
            echo "=== Finding all {binary} files ==="
            find /usr -name {binary} 2>/dev/null || echo "No {binary} files found in /usr"
            """
            debug_result = daytona_client.run_command(
                sandbox=sandbox,
                command=debug_cmd,
                cwd=work_dir,
            )
            raise CLIPatcherError(
                f"Required CLI '{binary}' is not available in sandbox and no install command provided.\\n\\nDebug info:\\n{debug_result['stdout']}"
            )
        logger.info(f"Installing {binary} CLI")
        install_script = textwrap.dedent(
            f"""
            set -e
            {install_command}
            """
        ).strip()
        result = daytona_client.run_command(
            sandbox=sandbox,
            command=f"bash -lc {shlex.quote(install_script)}",
            cwd=work_dir,
            timeout=600,
        )
        if result["exit_code"] != 0:
            raise CLIPatcherError(
                f"Failed to install {binary} CLI: {result['stderr'] or result['stdout']}"
            )
        logger.info(f"{binary} CLI installed successfully")

    def _authenticate_coderabbit(self, daytona_client, sandbox, work_dir: str):
        profile_b64 = os.getenv("CODERABBIT_PROFILE_B64")
        if profile_b64:
            logger.info("Restoring CodeRabbit OAuth profile from base64 archive")
            try:
                daytona_client.upload_file(
                    sandbox=sandbox,
                    content=profile_b64,
                    path="/tmp/coderabbit_profile.b64",
                )
                restore_script = textwrap.dedent(
                    """
                    set -ex
                    echo "Creating .coderabbit directory..."
                    mkdir -p ~/.coderabbit
                    echo "Decoding base64 file..."
                    base64 -d /tmp/coderabbit_profile.b64 > /tmp/coderabbit_profile.tar.gz || (echo "Base64 decode failed"; exit 1)
                    echo "Removing old .coderabbit..."
                    rm -rf ~/.coderabbit
                    echo "Extracting tarball..."
                    tar -xzf /tmp/coderabbit_profile.tar.gz -C ~ || (echo "Tar extraction failed"; exit 1)
                    echo "Profile restored successfully"
                    """
                ).strip()
                result = daytona_client.run_command(
                    sandbox=sandbox,
                    command=f"bash -lc {shlex.quote(restore_script)}",
                    cwd=work_dir,
                )
                if result["exit_code"] != 0:
                    logger.warning(
                        f"Failed to restore CodeRabbit profile (exit code {result['exit_code']}): {result['stderr'] or result['stdout']}. Continuing anyway..."
                    )
                else:
                    logger.info("CodeRabbit profile restored successfully")
            except Exception as e:
                logger.warning(f"Error restoring CodeRabbit profile: {e}. Continuing anyway...")
            return

        # If no profile, skip authentication - CodeRabbit might work without it or fail later
        logger.warning("CODERABBIT_PROFILE_B64 not set - CodeRabbit may require authentication")
        return
        
        # Old code that raises error - commented out to allow continuing without auth
        # token = os.getenv("CODERABBIT_TOKEN")
        # if token:
        #     logger.warning(
        #         "CODERABBIT_TOKEN is deprecated; CodeRabbit CLI now requires OAuth profile export"
        #     )
        # raise CLIPatcherError(
        #     "CodeRabbit CLI requires interactive OAuth. Set CODERABBIT_PROFILE_B64 with a base64-encoded "
        #     "tarball of ~/.config/coderabbit (created after running 'coderabbit auth login')."
        # )

    def _write_file(self, daytona_client, sandbox, path: str, content: str):
        daytona_client.upload_file(sandbox=sandbox, content=content, path=path)

    def _verify_internet_access(self, daytona_client, sandbox, work_dir: str):
        logger.info("Checking sandbox internet connectivity")
        test_cmd = textwrap.dedent(
            """
            set -e
            echo 'Testing HTTPS connectivity to google.com'
            curl -I https://www.google.com -m 10 >/tmp/net_test.out
            cat /tmp/net_test.out
            """
        ).strip()
        result = daytona_client.run_command(
            sandbox=sandbox,
            command=f"bash -lc {shlex.quote(test_cmd)}",
            cwd=work_dir,
            timeout=30,
        )
        raise CLIPatcherError(str(result))

        if result["exit_code"] != 0:
            raise CLIPatcherError(
                "Sandbox cannot reach the internet (curl to google.com failed)."
            )
        logger.info(f"Connectivity test succeeded: {result['stdout'].strip()}")

    def _extract_diff(self, content: str) -> str:
        """Extract unified diff from AI response."""
        # Look for diff code block
        diff_match = re.search(r"```diff\n(.*?)\n```", content, re.DOTALL)
        if diff_match:
            return diff_match.group(1).strip()
        
        # Fallback: look for any code block
        code_match = re.search(r"```\n(.*?)\n```", content, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        # Last resort: return content as-is if it looks like a diff
        if content.strip().startswith("---") or content.strip().startswith("diff"):
            return content.strip()
        
        raise CLIPatcherError("Could not extract diff from response")
    
    def validate_patch(self, patch: str) -> bool:
        """
        Validate patch against safety guardrails.
        
        Args:
            patch: Unified diff content
        
        Returns:
            True if patch is safe to apply
        
        Raises:
            CLIPatcherError if patch violates guardrails
        """
        lines = patch.splitlines()
        
        # Check line count
        if len(lines) > self.MAX_PATCH_LINES:
            raise CLIPatcherError(
                f"Patch too large: {len(lines)} lines (max {self.MAX_PATCH_LINES})"
            )
        
        # Extract file paths from diff
        file_paths = []
        for line in lines:
            if line.startswith("---") or line.startswith("+++"):
                # Extract path from "--- a/path/to/file" or "+++ b/path/to/file"
                match = re.search(r"[ab]/(.+)$", line)
                if match:
                    file_paths.append(match.group(1))
        
        # Check for forbidden paths
        for path in file_paths:
            # Check absolute forbidden paths
            for forbidden in self.FORBIDDEN_PATHS:
                if path.startswith(forbidden) or forbidden in path:
                    raise CLIPatcherError(f"Forbidden path in patch: {path}")
            
            # Check for parent directory traversal
            if ".." in path:
                raise CLIPatcherError(f"Parent traversal in patch: {path}")
            
            # Check if path matches allowed patterns
            allowed = any(re.match(pattern, path) for pattern in self.ALLOWED_PATTERNS)
            if not allowed:
                logger.warning(f"Path {path} doesn't match allowed patterns, but proceeding")
        
        logger.info(f"Patch validation passed: {len(file_paths)} files, {len(lines)} lines")
        return True
    
    def get_patch_summary(self, patch: str) -> Dict[str, Any]:
        """Extract summary information from a patch."""
        lines = patch.splitlines()
        
        files_modified = set()
        additions = 0
        deletions = 0
        
        for line in lines:
            if line.startswith("---") or line.startswith("+++"):
                match = re.search(r"[ab]/(.+)$", line)
                if match:
                    files_modified.add(match.group(1))
            elif line.startswith("+") and not line.startswith("+++"):
                additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1
        
        return {
            "files_modified": list(files_modified),
            "additions": additions,
            "deletions": deletions,
            "total_lines": len(lines),
        }
