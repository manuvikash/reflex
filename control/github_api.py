"""GitHub API client for creating pull requests."""
import logging
import os
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    pass


class GitHubClient:
    """Client for GitHub REST API operations."""
    
    def __init__(self):
        """Initialize GitHub client."""
        self.token = os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GITHUB_TOKEN not set")
        
        self.owner = os.getenv("GITHUB_OWNER")
        self.repo = os.getenv("GITHUB_REPO")
        
        if not self.owner or not self.repo:
            raise ValueError("GITHUB_OWNER and GITHUB_REPO must be set")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    def create_branch(self, branch_name: str, base_sha: str) -> bool:
        """
        Create a new branch from a base commit.
        
        Args:
            branch_name: Name of the new branch
            base_sha: SHA of the commit to branch from
        
        Returns:
            True if successful
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/git/refs"
        
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha,
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code == 201:
                logger.info(f"Created branch {branch_name}")
                return True
            elif response.status_code == 422:
                logger.warning(f"Branch {branch_name} already exists")
                return True
            else:
                logger.error(f"Failed to create branch: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating branch: {e}")
            return False
    
    def get_default_branch_sha(self) -> Optional[str]:
        """Get the SHA of the default branch HEAD."""
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/git/refs/heads/main"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                sha = data["object"]["sha"]
                logger.info(f"Default branch SHA: {sha}")
                return sha
            else:
                # Try 'master' as fallback
                url = f"{self.base_url}/repos/{self.owner}/{self.repo}/git/refs/heads/master"
                response = requests.get(url, headers=self.headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    sha = data["object"]["sha"]
                    logger.info(f"Default branch SHA: {sha}")
                    return sha
                
                logger.error(f"Failed to get default branch SHA: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting default branch SHA: {e}")
            return None
    
    def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        draft: bool = False,
        reviewers: Optional[list] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a pull request.
        
        Args:
            title: PR title
            body: PR description
            head_branch: Branch with changes
            base_branch: Target branch (default: main)
            draft: Create as draft PR
            reviewers: List of GitHub usernames to request reviews from
        
        Returns:
            PR data dict with 'number', 'html_url', etc.
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/pulls"
        
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "draft": draft,
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code == 201:
                pr_data = response.json()
                pr_number = pr_data["number"]
                pr_url = pr_data["html_url"]
                
                logger.info(f"Created PR #{pr_number}: {pr_url}")
                
                # Request reviewers if specified
                if reviewers:
                    self._request_reviewers(pr_number, reviewers)
                
                return {
                    "number": pr_number,
                    "html_url": pr_url,
                    "state": pr_data["state"],
                    "created_at": pr_data["created_at"],
                }
            else:
                logger.error(f"Failed to create PR: {response.status_code} {response.text}")
                raise GitHubAPIError(f"Failed to create PR: {response.text}")
                
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            raise GitHubAPIError(f"Error creating PR: {e}")
    
    def _request_reviewers(self, pr_number: int, reviewers: list):
        """Request reviews from specified users."""
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/pulls/{pr_number}/requested_reviewers"
        
        data = {"reviewers": reviewers}
        
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code == 201:
                logger.info(f"Requested reviews from {reviewers}")
            else:
                logger.warning(f"Failed to request reviewers: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Error requesting reviewers: {e}")
    
    def format_pr_body(
        self,
        issue_id: str,
        issue_title: str,
        sentry_url: str,
        patch_summary: Dict[str, Any],
        ai_reasoning: str = "",
    ) -> str:
        """
        Format a PR body with relevant information.
        
        Args:
            issue_id: Sentry issue ID
            issue_title: Sentry issue title
            sentry_url: URL to Sentry issue
            patch_summary: Summary of the patch changes
            ai_reasoning: AI's explanation of the fix
        
        Returns:
            Formatted PR body
        """
        body = f"""## 🤖 Automated Fix for Sentry Issue

**Issue:** [{issue_title}]({sentry_url})  
**Sentry ID:** `{issue_id}`

### Changes
- **Files modified:** {len(patch_summary.get('files_modified', []))}
- **Additions:** +{patch_summary.get('additions', 0)} lines
- **Deletions:** -{patch_summary.get('deletions', 0)} lines

### Modified Files
"""
        
        for file_path in patch_summary.get("files_modified", []):
            body += f"- `{file_path}`\n"
        
        if ai_reasoning:
            body += f"\n### Analysis\n{ai_reasoning}\n"
        
        body += """
### Testing
✅ Tests passed in isolated Daytona sandbox

---
*This PR was automatically generated by SafeRunner*
"""
        
        return body
