"""Worker orchestration for processing Sentry alerts."""
import logging
import time
from datetime import datetime
from typing import Dict, Any

from control.daytona_client import DaytonaClient
from control.github_api import GitHubClient, GitHubAPIError
from control.patcher import Patcher, PatcherError
from control.routing import resolve_route

logger = logging.getLogger(__name__)


def process_sentry_alert(payload: Dict[str, Any]):
    """
    Main orchestration function for processing a Sentry alert.
    
    Steps:
    1. Extract issue information from payload
    2. Resolve repository and commit via routing
    3. Create Daytona sandbox
    4. Clone repository and reproduce bug
    5. Generate patch using Gemini
    6. Apply patch and re-run tests
    7. Create GitHub PR if tests pass
    8. Cleanup sandbox
    """
    start_time = time.time()
    sandbox = None
    
    try:
        # Extract issue information
        data = payload.get("data", {})
        issue = data.get("issue", {})
        event = data.get("event", {})
        
        issue_id = issue.get("id", "unknown")
        issue_title = issue.get("title", "Unknown issue")
        issue_url = issue.get("permalink", "")
        
        logger.info(f"Processing Sentry issue {issue_id}: {issue_title}")
        
        # Extract error details
        error_message = event.get("title", "")
        exception = event.get("exception", {})
        
        stack_trace = ""
        if exception and "values" in exception:
            for exc_value in exception["values"]:
                if "stacktrace" in exc_value:
                    frames = exc_value["stacktrace"].get("frames", [])
                    for frame in frames:
                        filename = frame.get("filename", "")
                        function = frame.get("function", "")
                        lineno = frame.get("lineno", "")
                        context = frame.get("context_line", "")
                        stack_trace += f"  File {filename}, line {lineno}, in {function}\n"
                        if context:
                            stack_trace += f"    {context}\n"
        
        # Resolve routing
        logger.info("Resolving repository and commit")
        route = resolve_route(payload)
        logger.info(f"Route: {route.repo_url} @ {route.commitish}, path: {route.subpath}")
        
        # Initialize clients
        daytona = DaytonaClient()
        patcher = Patcher()
        github = GitHubClient()
        
        # Create sandbox
        logger.info("Creating Daytona sandbox")
        sandbox = daytona.create_sandbox(
            snapshot="saferunner-ci",
            cpu=2,
            memory=4,
            disk=10,
            auto_stop_interval=20,
            ephemeral=True,
        )
        
        # Clone repository
        logger.info("Cloning repository")
        daytona.clone_repo(
            sandbox=sandbox,
            repo_url=route.repo_url,
            path="/workspace/app",
            branch=route.commitish if route.commitish != "main" else None,
            commit_id=route.commitish if len(route.commitish) == 40 else None,
        )
        
        # Determine working directory
        work_dir = "/workspace/app"
        if route.subpath:
            work_dir = f"{work_dir}/{route.subpath}"
        
        # Run initial tests to reproduce the bug
        logger.info("Running tests to reproduce bug")
        test_result = daytona.run_command(
            sandbox=sandbox,
            command=route.test_command,
            cwd=work_dir,
            timeout=300,
        )
        
        initial_test_output = test_result["stdout"] + test_result["stderr"]
        
        if test_result["exit_code"] == 0:
            logger.warning("Tests passed on initial run - bug may not be reproducible")
            # Continue anyway to generate a patch
        
        # Generate patch using Gemini
        logger.info("Generating patch with Gemini")
        patch = patcher.generate_patch(
            error_message=error_message,
            stack_trace=stack_trace,
            test_output=initial_test_output,
        )
        
        # Validate patch
        logger.info("Validating patch")
        patcher.validate_patch(patch)
        patch_summary = patcher.get_patch_summary(patch)
        
        logger.info(f"Patch summary: {patch_summary}")
        
        # Apply patch
        logger.info("Applying patch")
        
        # Write patch to file
        daytona.exec_command(
            sandbox=sandbox,
            command=f"cat > /tmp/patch.diff << 'EOF'\n{patch}\nEOF",
            cwd=work_dir,
        )
        
        # Apply with git
        apply_result = daytona.exec_command(
            sandbox=sandbox,
            command="git apply --whitespace=fix /tmp/patch.diff",
            cwd=work_dir,
        )
        
        if apply_result["exit_code"] != 0:
            logger.error(f"Failed to apply patch: {apply_result['stderr']}")
            raise PatcherError(f"Patch application failed: {apply_result['stderr']}")
        
        logger.info("Patch applied successfully")
        
        # Re-run tests
        logger.info("Re-running tests")
        retest_result = daytona.exec_command(
            sandbox=sandbox,
            command=route.test_command,
            cwd=work_dir,
            timeout=300,
        )
        
        if retest_result["exit_code"] != 0:
            logger.error("Tests still failing after patch")
            logger.error(f"Test output: {retest_result['stdout']}")
            raise PatcherError("Tests failed after applying patch")
        
        logger.info("Tests passed after patch! ✅")
        
        # Create branch name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"saferunner/fix-{issue_id}-{timestamp}"
        
        # Configure git in sandbox
        daytona.exec_command(
            sandbox=sandbox,
            command='git config user.email "saferunner@bot.com"',
            cwd=work_dir,
        )
        daytona.exec_command(
            sandbox=sandbox,
            command='git config user.name "SafeRunner Bot"',
            cwd=work_dir,
        )
        
        # Create branch and commit
        daytona.exec_command(
            sandbox=sandbox,
            command=f"git checkout -b {branch_name}",
            cwd=work_dir,
        )
        
        daytona.exec_command(
            sandbox=sandbox,
            command="git add -A",
            cwd=work_dir,
        )
        
        commit_message = f"Fix: {issue_title}\n\nSentry Issue: {issue_id}\nAuto-generated by SafeRunner"
        daytona.exec_command(
            sandbox=sandbox,
            command=f'git commit -m "{commit_message}"',
            cwd=work_dir,
        )
        
        # Push to GitHub
        logger.info(f"Pushing branch {branch_name}")
        push_result = daytona.exec_command(
            sandbox=sandbox,
            command=f"git push origin {branch_name}",
            cwd=work_dir,
            timeout=120,
        )
        
        if push_result["exit_code"] != 0:
            logger.error(f"Failed to push branch: {push_result['stderr']}")
            raise GitHubAPIError(f"Failed to push branch: {push_result['stderr']}")
        
        # Create pull request
        logger.info("Creating GitHub pull request")
        pr_title = f"🤖 Fix: {issue_title}"
        pr_body = github.format_pr_body(
            issue_id=str(issue_id),
            issue_title=issue_title,
            sentry_url=issue_url,
            patch_summary=patch_summary,
        )
        
        pr = github.create_pull_request(
            title=pr_title,
            body=pr_body,
            head_branch=branch_name,
            base_branch="main",
        )
        
        logger.info(f"Pull request created: {pr['html_url']}")
        
        # Optional: Get preview link for reporting
        preview = daytona.get_preview_link(sandbox, 8000)
        if preview:
            logger.info(f"Preview available at: {preview['url']}")
            logger.info(f"Preview token: {preview['token']}")
        
        elapsed = time.time() - start_time
        logger.info(f"Successfully processed issue {issue_id} in {elapsed:.1f}s")
        logger.info(f"PR: {pr['html_url']}")
        
    except PatcherError as e:
        logger.error(f"Patcher error: {e}")
    except GitHubAPIError as e:
        logger.error(f"GitHub API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing alert: {e}", exc_info=True)
    finally:
        # Cleanup sandbox
        if sandbox:
            logger.info("Cleaning up sandbox")
            try:
                daytona = DaytonaClient()
                daytona.stop_sandbox(sandbox)
            except Exception as e:
                logger.error(f"Failed to cleanup sandbox: {e}")
