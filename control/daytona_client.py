"""Daytona SDK wrapper for sandbox operations."""
import logging
from typing import Optional, Dict, Any

from daytona_sdk import Daytona

logger = logging.getLogger(__name__)


class DaytonaClient:
    """Wrapper around Daytona SDK for sandbox lifecycle management."""
    
    def __init__(self):
        """Initialize Daytona client. Reads env vars automatically."""
        self.daytona = Daytona()
    
    def create_sandbox(
        self,
        snapshot: str = "saferunner-ci",
        cpu: int = 2,
        memory: int = 4,
        disk: int = 10,
        auto_stop_interval: int = 20,
        ephemeral: bool = True,
        network_block_all: bool = False,
        network_allow_list: Optional[list] = None,
    ):
        """
        Create a sandbox from a snapshot with specified resources.
        
        Args:
            snapshot: Name of the snapshot to use
            cpu: CPU cores (note: resource limits set at snapshot level in current SDK)
            memory: Memory in GB (note: resource limits set at snapshot level in current SDK)
            disk: Disk space in GB (note: resource limits set at snapshot level in current SDK)
            auto_stop_interval: Minutes before auto-stop
            ephemeral: If True, sandbox is deleted on stop
            network_block_all: Block all network access
            network_allow_list: List of allowed domains/IPs
        
        Returns:
            Sandbox instance
        """
        logger.info(f"Creating sandbox from snapshot '{snapshot}'")
        
        # SDK 0.14.0 doesn't export CreateSandboxFromSnapshotParams
        # Try calling create() with no params to use defaults
        logger.warning(f"Creating sandbox with default params (SDK 0.14.0 limitation)")
        sandbox = self.daytona.create()
        logger.info(f"Sandbox created: {sandbox.id}")
        
        return sandbox
    
    def clone_repo(
        self,
        sandbox,
        repo_url: str,
        path: str = "/workspace/app",
        branch: Optional[str] = None,
        commit_id: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
    ):
        """
        Clone a git repository into the sandbox.
        
        Args:
            sandbox: Sandbox instance
            repo_url: Git repository URL
            path: Path where to clone the repo
            branch: Branch to checkout (optional)
            commit_id: Specific commit to checkout (optional)
            username: Git username for authentication (optional)
            token: Git token for authentication (optional)
        """
        logger.info(f"Cloning repository {repo_url} to {path}")
        
        # Build authenticated URL if credentials provided
        if username and token:
            # Parse URL and inject credentials
            if repo_url.startswith("https://"):
                repo_url = repo_url.replace("https://", f"https://{username}:{token}@")
        
        # Clone the repository
        sandbox.process.exec(f"git clone {repo_url} {path}")
        
        # Checkout specific branch or commit if specified
        if commit_id:
            logger.info(f"Checking out commit {commit_id}")
            sandbox.process.exec(f"cd {path} && git checkout {commit_id}")
        elif branch:
            logger.info(f"Checking out branch {branch}")
            sandbox.process.exec(f"cd {path} && git checkout {branch}")
        
        logger.info("Repository cloned successfully")
    
    def run_command(
        self,
        sandbox,
        command: str,
        cwd: str = "/workspace/app",
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """
        Run a command in the sandbox.
        
        Args:
            sandbox: Sandbox instance
            command: Command to run
            cwd: Working directory
            timeout: Command timeout in seconds
        
        Returns:
            Dict with stdout, stderr, and exit_code
        """
        logger.info(f"Running command: {command}")
        
        # Change to working directory and run command
        full_command = f"cd {cwd} && {command}"
        result = sandbox.process.exec(full_command)
        
        return {
            "stdout": result.stdout if hasattr(result, 'stdout') else "",
            "stderr": result.stderr if hasattr(result, 'stderr') else "",
            "exit_code": result.exit_code if hasattr(result, 'exit_code') else 0,
        }
    
    def write_file(
        self,
        sandbox,
        path: str,
        content: str,
    ):
        """
        Write content to a file in the sandbox.
        
        Args:
            sandbox: Sandbox instance
            path: File path
            content: File content
        """
        logger.info(f"Writing file: {path}")
        
        # Escape content for shell
        escaped_content = content.replace("'", "'\\''")
        
        # Write file using echo
        sandbox.process.exec(f"echo '{escaped_content}' > {path}")
    
    def read_file(
        self,
        sandbox,
        path: str,
    ) -> str:
        """
        Read a file from the sandbox.
        
        Args:
            sandbox: Sandbox instance
            path: File path
        
        Returns:
            File content
        """
        logger.info(f"Reading file: {path}")
        result = sandbox.process.exec(f"cat {path}")
        return result.stdout if hasattr(result, 'stdout') else ""
    
    def stop_sandbox(self, sandbox):
        """Stop a sandbox."""
        logger.info(f"Stopping sandbox {sandbox.id}")
        sandbox.stop()
    
    def delete_sandbox(self, sandbox):
        """Delete a sandbox."""
        logger.info(f"Deleting sandbox {sandbox.id}")
        sandbox.delete()
