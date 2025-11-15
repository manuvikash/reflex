"""Worker orchestration for processing Sentry alerts."""
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any

from control.daytona_client import DaytonaClient
from control.github_api import GitHubClient, GitHubAPIError
from control.patcher import Patcher, PatcherError
from control.cli_patcher import CLIPatcher, CLIPatcherError
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
        
        logger.info(f"🚀 Processing issue {issue_id}: {issue_title}")
        
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
        route = resolve_route(payload)
        logger.info(f"📦 Repository: {route.repo_url.split('/')[-1]} @ {route.commitish[:8]}")
        
        # Initialize clients
        daytona = DaytonaClient()
        github = GitHubClient()
        
        # Choose patcher based on environment variable
        patcher_mode = os.getenv("PATCHER_MODE", "api")  # 'api' or 'cli'
        patcher_tool = os.getenv("PATCHER_TOOL", "coderabbit")  # 'coderabbit', 'gemini', etc.
        
        if patcher_mode == "cli":
            patcher = CLIPatcher(tool=patcher_tool)
            use_cli_patcher = True
        else:
            patcher = Patcher()
            use_cli_patcher = False
        
        # Create sandbox
        logger.info("🐳 Creating sandbox...")
        sandbox = daytona.create_sandbox(
            snapshot="saferunner-ci",
            cpu=2,
            memory=4,
            disk=10,
            auto_stop_interval=20,
            ephemeral=True,
        )
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
        
        # List repository structure to understand what we're working with
        daytona.run_command(
            sandbox=sandbox,
            command="find . -type f -name '*.py' | head -20 > /tmp/repo_files.txt 2>&1",
            cwd=work_dir,
            timeout=30,
        )
        repo_files = daytona.read_file(sandbox, "/tmp/repo_files.txt")
        
        # Run initial tests to reproduce the bug
        logger.info("🧪 Running tests...")
        daytona.run_command(
            sandbox=sandbox,
            command=f"{route.test_command} > /tmp/test_output.txt 2>&1; echo $? > /tmp/test_exit_code.txt",
            cwd=work_dir,
            timeout=300,
        )
        
        # Read the test output from file since run_command doesn't return it
        initial_test_output = daytona.read_file(sandbox, "/tmp/test_output.txt")
        test_exit_code_str = daytona.read_file(sandbox, "/tmp/test_exit_code.txt").strip()
        test_exit_code = int(test_exit_code_str) if test_exit_code_str.isdigit() else 1
        
        if test_exit_code == 0:
            logger.warning("⚠️  Tests passed - bug may not be reproducible")
            # Continue anyway to generate a patch
        else:
            logger.info(f"❌ Tests failed (exit code {test_exit_code})")
        
        # Retry loop for patch generation and application
        max_retries = 3
        retry_count = 0
        feedback = None
        retest_exit_code = 1
        retest_output = ""  # Initialize to avoid UnboundLocalError
        
        while retry_count < max_retries and retest_exit_code != 0:
            retry_count += 1
            logger.info(f"🤖 Generating patch (attempt {retry_count}/{max_retries})...")
            
            # Generate patch
            if use_cli_patcher:
                patch = patcher.generate_patch(
                    daytona_client=daytona,
                    sandbox=sandbox,
                    work_dir=work_dir,
                    error_message=error_message,
                    stack_trace=stack_trace,
                    test_output=initial_test_output,
                )
            else:
                # Include repo file list in context
                repo_context = f"Available Python files (use these exact paths):\n{repo_files}"
                patch = patcher.generate_patch(
                    error_message=error_message,
                    stack_trace=stack_trace,
                    test_output=initial_test_output,
                    repo_context=repo_context,
                    previous_patch_feedback=feedback,
                )
            
            # Validate patch
            patcher.validate_patch(patch)
            patch_summary = patcher.get_patch_summary(patch)
            
            logger.info(f"📝 Patch: {patch_summary['additions']}+ {patch_summary['deletions']}- across {len(patch_summary['files_modified'])} file(s)")
            
            if use_cli_patcher:
                logger.info("✓ Files modified via CLI patcher")
            else:
                # Apply patch using new method that verifies via git status
                logger.info("📄 Applying patch...")
                
                # Apply patch and check status
                try:
                    status = daytona.apply_patch_file(sandbox, work_dir, patch)
                except Exception as e:
                    logger.error(f"Git apply failed: {e}")
                    # Get the actual file content to help Gemini
                    import re
                    file_match = re.search(r'--- a/(.+)', patch)
                    if file_match:
                        failed_file = file_match.group(1).strip()
                        # Try multiple possible paths
                        possible_paths = [
                            f"{work_dir}/{failed_file}",
                            f"/workspace/app/{failed_file}",
                            failed_file if failed_file.startswith('/') else None
                        ]
                        
                        actual_content = None
                        for path in possible_paths:
                            if path:
                                try:
                                    actual_content = daytona.read_file(sandbox, path)
                                    if actual_content:
                                        logger.info(f"Found file at: {path}")
                                        break
                                except Exception as read_err:
                                    logger.debug(f"Failed to read {path}: {read_err}")
                                    continue
                        
                        if actual_content:
                            feedback = f"Git apply failed with error: {e}\n\nThe actual content of {failed_file}:\n```python\n{actual_content}\n```\n\nPlease generate a patch that matches the actual file content exactly. Ensure context lines match precisely and the patch uses Unix line endings (LF)."
                        else:
                            # File doesn't exist - provide list of actual files
                            feedback = f"Git apply failed with error: {e}\n\nThe file {failed_file} was not found. Available Python files in the repo:\n{repo_files}\n\nPlease use the correct file path from this list."
                    else:
                        feedback = f"Git apply failed: {e}"
                    continue
                
                # Verify files were modified
                if status.file_status and len(status.file_status) > 0:
                    modified_files = ', '.join([getattr(f, 'file_path', getattr(f, 'name', str(f))).split('/')[-1] for f in status.file_status[:3]])
                    logger.info(f"✓ Modified {len(status.file_status)} file(s): {modified_files}{'...' if len(status.file_status) > 3 else ''}")
                else:
                    logger.error("❌ No files modified")
                    feedback = "The patch failed to apply. No files were modified. Please check the file paths and ensure the context lines match exactly."
                    continue
            
            # Re-run tests
            logger.info("🧪 Re-running tests...")
            daytona.run_command(
                sandbox=sandbox,
                command=f"{route.test_command} > /tmp/retest_output.txt 2>&1; echo $? > /tmp/retest_exit_code.txt",
                cwd=work_dir,
                timeout=300,
            )
            
            # Read the retest output from file
            retest_output = daytona.read_file(sandbox, "/tmp/retest_output.txt")
            retest_exit_code_str = daytona.read_file(sandbox, "/tmp/retest_exit_code.txt").strip()
            retest_exit_code = int(retest_exit_code_str) if retest_exit_code_str.isdigit() else 1
            
            if retest_exit_code != 0:
                logger.warning(f"❌ Tests still failing (attempt {retry_count}/{max_retries})")
                feedback = f"The patch was applied but tests are still failing. Test output:\n{retest_output}\n\nPlease fix the issue."
            else:
                logger.info("✅ Tests passed!")
        
        if retest_exit_code != 0:
            logger.error(f"❌ Tests failed after {max_retries} attempts")
            raise PatcherError(f"Tests failed after {max_retries} patch attempts")
        
        # Create branch name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"saferunner/fix-{issue_id}-{timestamp}"
        
        # Configure git in sandbox
        daytona.run_command(
            sandbox=sandbox,
            command='git config user.email "saferunner@bot.com"',
            cwd=work_dir,
        )
        daytona.run_command(
            sandbox=sandbox,
            command='git config user.name "SafeRunner Bot"',
            cwd=work_dir,
        )
        
        # Create branch and commit
        daytona.run_command(
            sandbox=sandbox,
            command=f"git checkout -b {branch_name}",
            cwd=work_dir,
        )
        
        daytona.run_command(
            sandbox=sandbox,
            command="git add -A",
            cwd=work_dir,
        )
        
        commit_message = f"Fix: {issue_title}\n\nSentry Issue: {issue_id}\nAuto-generated by SafeRunner"
        daytona.run_command(
            sandbox=sandbox,
            command=f'git commit -m "{commit_message}"',
            cwd=work_dir,
        )
        
        # Push to GitHub
        logger.info("📤 Pushing to GitHub...")
        push_result = daytona.run_command(
            sandbox=sandbox,
            command=f"git push origin {branch_name}",
            cwd=work_dir,
            timeout=120,
        )
        
        if push_result["exit_code"] != 0:
            logger.error(f"❌ Push failed: {push_result['stderr']}")
            raise GitHubAPIError(f"Failed to push branch: {push_result['stderr']}")
        
        # Create pull request
        logger.info("📝 Creating pull request...")
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
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Success! PR created in {elapsed:.1f}s: {pr['html_url']}")
        
    except (PatcherError, CLIPatcherError) as e:
        logger.error(f"Patcher error: {e}")
    except GitHubAPIError as e:
        logger.error(f"GitHub API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing alert: {e}", exc_info=True)
    finally:
        # Cleanup sandbox
        if sandbox:
            logger.info("🧹 Cleaning up...")
            try:
                daytona = DaytonaClient()
                daytona.stop_sandbox(sandbox)
            except Exception as e:
                logger.error(f"Cleanup failed: {e}")
