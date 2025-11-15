"""Routing logic to resolve repo, commit, and path from Sentry payload."""
import logging
import os
from dataclasses import dataclass
from typing import Dict, Any, Optional

import requests
import yaml

logger = logging.getLogger(__name__)


@dataclass
class RouteInfo:
    """Information about where to run the reproduction."""
    repo_url: str
    commitish: str
    subpath: str
    test_command: str


def load_services_config() -> Dict[str, Any]:
    """Load services.yaml fallback configuration."""
    config_path = "services.yaml"
    if not os.path.exists(config_path):
        return {}
    
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load services.yaml: {e}")
        return {}


def get_release_commits(release: str, org_slug: str, project_slug: str) -> Optional[str]:
    """
    Query Sentry API to get commits associated with a release.
    Returns the first commit SHA if available.
    """
    sentry_auth_token = os.getenv("SENTRY_AUTH_TOKEN")
    if not sentry_auth_token:
        logger.warning("SENTRY_AUTH_TOKEN not set, cannot fetch release commits")
        return None
    
    url = f"https://sentry.io/api/0/projects/{org_slug}/{project_slug}/releases/{release}/commits/"
    headers = {"Authorization": f"Bearer {sentry_auth_token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        commits = response.json()
        
        if commits and len(commits) > 0:
            commit_id = commits[0].get("id")
            logger.info(f"Found commit {commit_id} for release {release}")
            return commit_id
        
    except Exception as e:
        logger.warning(f"Failed to fetch release commits: {e}")
    
    return None


def resolve_route(payload: Dict[str, Any]) -> RouteInfo:
    """
    Resolve repository, commit, and path from Sentry payload.
    
    Priority:
    1. Event tags (service, repo, monorepo_path)
    2. Release mapping (query Sentry API for commits)
    3. Fallback to services.yaml config
    4. Default to main branch
    """
    event = payload.get("data", {}).get("event", {})
    
    # Parse tags - they can be either a list of dicts or a list of lists
    raw_tags = event.get("tags", [])
    tags = {}
    
    if raw_tags and isinstance(raw_tags, list):
        if isinstance(raw_tags[0], dict):
            # Format: [{"key": "service", "value": "my-service"}, ...]
            tags = {tag.get("key"): tag.get("value") for tag in raw_tags}
        elif isinstance(raw_tags[0], list):
            # Format: [["service", "my-service"], ["repo", "owner/repo"], ...]
            tags = {tag[0]: tag[1] for tag in raw_tags if len(tag) >= 2}
    
    # Try to get from tags first
    service = tags.get("service")
    repo = tags.get("repo")
    monorepo_path = tags.get("monorepo_path", "")
    
    # Default values
    github_owner = os.getenv("GITHUB_OWNER", "")
    github_repo = os.getenv("GITHUB_REPO", "")
    github_token = os.getenv("GITHUB_TOKEN", "")
    
    commitish = "main"
    test_command = "pytest -q"
    
    # If repo is in tags, use it
    if repo:
        if github_token:
            repo_url = f"https://{github_token}@github.com/{repo}.git"
        else:
            repo_url = f"https://github.com/{repo}.git"
        
        logger.info(f"Using repo from tags: {repo}")
    else:
        # Try release mapping
        release = event.get("release")
        if release:
            project = payload.get("data", {}).get("project")
            if project:
                org_slug = project.get("organization", {}).get("slug")
                project_slug = project.get("slug")
                
                if org_slug and project_slug:
                    commit = get_release_commits(release, org_slug, project_slug)
                    if commit:
                        commitish = commit
                        logger.info(f"Resolved commit {commit} from release {release}")
        
        # Fallback to services.yaml or env vars
        services_config = load_services_config()
        
        if service and service in services_config:
            config = services_config[service]
            repo = config.get("repo", f"{github_owner}/{github_repo}")
            monorepo_path = config.get("path", "")
            test_command = config.get("test_command", "pytest -q")
            logger.info(f"Using config for service {service}: {repo}")
        else:
            repo = f"{github_owner}/{github_repo}"
            logger.info(f"Using default repo from env: {repo}")
        
        if github_token:
            repo_url = f"https://{github_token}@github.com/{repo}.git"
        else:
            repo_url = f"https://github.com/{repo}.git"
    
    return RouteInfo(
        repo_url=repo_url,
        commitish=commitish,
        subpath=monorepo_path,
        test_command=test_command
    )
