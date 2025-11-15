"""Daytona SDK wrapper for sandbox operations."""
import logging
from typing import Optional, Dict, Any

from daytona import Daytona, CreateSandboxFromSnapshotParams

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
        params = CreateSandboxFromSnapshotParams(
            snapshot=snapshot,
            auto_stop_interval=auto_stop_interval,
            ephemeral=ephemeral,
        )
        sandbox = self.daytona.create(params)
        logger.info(f"✓ Sandbox ready: {sandbox.id}")
        
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
        Clone a git repository into the sandbox using Daytona's Git API.
        
        Args:
            sandbox: Sandbox instance
            repo_url: Git repository URL (can include embedded credentials)
            path: Path where to clone the repo
            branch: Branch to checkout (optional)
            commit_id: Specific commit to checkout (optional)
            username: Git username for authentication (optional)
            token: Git token for authentication (optional)
        """
        # Parse credentials from URL if embedded
        import re
        clean_url = repo_url
        url_username = username
        url_token = token
        
        # Check if URL has embedded credentials (https://user:token@github.com/...)
        match = re.match(r'https://([^:]+):([^@]+)@(.+)', repo_url)
        if match:
            url_username = match.group(1)
            url_token = match.group(2)
            clean_url = f"https://{match.group(3)}"
        
        logger.info(f"📥 Cloning {clean_url.split('/')[-1]}...")
        
        # Use Daytona's Git API with clean URL and separate credentials
        sandbox.git.clone(
            url=clean_url,
            path=path,
            branch=branch,
            commit_id=commit_id,
            username=url_username,
            password=url_token
        )
    
    def upload_file(
        self,
        sandbox,
        content: str,
        path: str,
    ):
        """
        Upload a file to the sandbox.
        
        Args:
            sandbox: Sandbox instance
            content: File content as string
            path: Destination path in sandbox
        """
        sandbox.fs.upload_file(content.encode('utf-8'), path)
    
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
        # Change to working directory and run command
        full_command = f"cd {cwd} && {command}"
        result = sandbox.process.exec(full_command)
        
        # Try to get output - the result object might have different attribute names
        stdout = ""
        stderr = ""
        exit_code = 0
        
        if hasattr(result, 'stdout'):
            stdout = result.stdout or ""
        if hasattr(result, 'stderr'):
            stderr = result.stderr or ""
        if hasattr(result, 'exit_code'):
            exit_code = result.exit_code
        elif hasattr(result, 'code'):
            exit_code = result.code
        
        # Some SDKs return the output as a string directly
        if not stdout and isinstance(result, str):
            stdout = result
        
        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
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
        Read a file from the sandbox using the filesystem API.
        
        Args:
            sandbox: Sandbox instance
            path: File path
        
        Returns:
            File content
        """
        try:
            # Use the filesystem API to download the file
            content_bytes = sandbox.fs.download_file(path)
            return content_bytes.decode('utf-8')
        except Exception as e:
            logger.debug(f"Failed to read {path}: {e}")
            return ""
    
    def apply_patch_file(self, sandbox, repo_path: str, patch_content: str):
        """
        Apply a patch by parsing it and using the FS API to modify files directly.
        This avoids git apply formatting issues.
        """
        import re
        
        # Parse patch to extract changes
        # Match: --- a/filepath \n +++ b/filepath \n @@ ... @@ \n context/changes
        file_pattern = r'--- a/(.+?)\n\+\+\+ b/.+?\n((?:@@.*?@@\n(?:(?!---).)*)+)'
        
        files_modified = []
        
        for match in re.finditer(file_pattern, patch_content, re.DOTALL):
            file_path = match.group(1).strip()
            hunks = match.group(2)
            
            full_path = f"{repo_path}/{file_path}"
            
            # Read current file
            try:
                content = self.read_file(sandbox, full_path)
            except Exception as e:
                logger.error(f"Cannot read {file_path}: {e}")
                raise Exception(f"File not found: {file_path}")
            
            # Parse hunks and build old->new mappings
            hunk_pattern = r'@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@\n(.*?)(?=@@|$)'
            
            modified = False
            for hunk_match in re.finditer(hunk_pattern, hunks, re.DOTALL):
                old_start = int(hunk_match.group(1))
                hunk_content = hunk_match.group(5)
                
                # Split into lines and extract changes
                lines = hunk_content.rstrip('\n').split('\n')
                
                # Build old and new content from the hunk
                old_lines = []
                new_lines = []
                
                for line in lines:
                    if not line:
                        continue
                    
                    first_char = line[0] if line else ''
                    rest = line[1:] if len(line) > 1 else ''
                    
                    if first_char == '-':
                        # Deletion
                        old_lines.append(rest)
                    elif first_char == '+':
                        # Addition
                        new_lines.append(rest)
                    elif first_char == ' ':
                        # Context line - appears in both
                        old_lines.append(rest)
                        new_lines.append(rest)
                    else:
                        # Line without prefix - treat as context
                        old_lines.append(line)
                        new_lines.append(line)
                
                # Build search and replace strings
                old_text = '\n'.join(old_lines)
                new_text = '\n'.join(new_lines)
                
                if old_text in content:
                    content = content.replace(old_text, new_text, 1)
                    modified = True
                else:
                    logger.warning(f"Could not find exact match for hunk at line {old_start} in {file_path}")
            
            if modified:
                # Write modified content
                self.write_file(sandbox, full_path, content)
                files_modified.append(file_path)
            else:
                logger.error(f"No changes applied to {file_path}")
        
        if not files_modified:
            raise Exception("No files were modified by the patch")
        
        # Verify with git status
        status = sandbox.git.status(repo_path)
        
        return status
    
    def stop_sandbox(self, sandbox):
        """Stop a sandbox."""
        sandbox.stop()
    
    def delete_sandbox(self, sandbox):
        """Delete a sandbox."""
        sandbox.delete()
    
    def get_git_status(self, sandbox, repo_path: str):
        """Get Git repository status using Daytona's Git API."""
        return sandbox.git.status(repo_path)
    
    def git_add_all(self, sandbox, repo_path: str):
        """Stage all changes using Daytona's Git API."""
        status = sandbox.git.status(repo_path)
        if status.file_status:
            files = [f.path for f in status.file_status]
            sandbox.git.add(repo_path, files)
        return status
    
    def git_commit(self, sandbox, repo_path: str, message: str, author: str = "SafeRunner Bot", email: str = "saferunner@bot.com"):
        """Create a commit using Daytona's Git API."""
        return sandbox.git.commit(
            path=repo_path,
            message=message,
            author=author,
            email=email
        )
    
    def git_push(self, sandbox, repo_path: str, username: Optional[str] = None, password: Optional[str] = None):
        """Push changes using Daytona's Git API."""
        sandbox.git.push(repo_path, username=username, password=password)

