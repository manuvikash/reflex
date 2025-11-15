"""Gemini-based patch generation with safety guardrails."""
import logging
import os
import re
from typing import Optional, Dict, Any

import google.generativeai as genai

logger = logging.getLogger(__name__)


class PatcherError(Exception):
    """Custom exception for patcher errors."""
    pass


class Patcher:
    """Generate and validate patches using Gemini."""
    
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
    
    def __init__(self):
        """Initialize Gemini client."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Initialize model
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(self.model_name)
    
    def generate_patch(
        self,
        error_message: str,
        stack_trace: str,
        repo_context: str = "",
        test_output: str = "",
        previous_patch_feedback: Optional[str] = None,
    ) -> str:
        """
        Generate a minimal unified diff patch using Gemini.
        
        Args:
            error_message: The error message from Sentry
            stack_trace: Stack trace from the error
            repo_context: Additional context about the repository
            test_output: Output from failed test run
            previous_patch_feedback: Feedback from previous patch attempt
        
        Returns:
            Unified diff as a string
        """
        system_prompt = """You are a senior software engineer tasked with generating minimal bug fixes.

CRITICAL REQUIREMENTS:
1. Return ONLY a unified diff format patch (git diff output)
2. Keep changes minimal - fix only what's broken
3. Only modify files in src/, tests/, app/, or lib/ directories
4. Cap the patch to ~80 lines total
5. If a test is missing or needs adjustment, include that in the patch
6. Use proper unified diff format with file paths, line numbers, and +/- markers
7. Start your response with ```diff and end with ```
8. Ensure the context lines (unchanged lines around the change) match EXACTLY what's in the file

PATCH FORMAT:
```diff
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -10,7 +10,7 @@
 context line
-old line
+new line
 context line
```

Focus on the root cause. Do not add unnecessary logging or comments."""

        user_prompt = f"""Fix this bug:

ERROR: {error_message}

STACK TRACE:
{stack_trace}

TEST OUTPUT:
{test_output}

{f"REPO CONTEXT: {repo_context}" if repo_context else ""}

{f"PREVIOUS ATTEMPT FAILED: {previous_patch_feedback}" if previous_patch_feedback else ""}

Generate a minimal unified diff patch to fix this issue."""

        try:
            
            # Combine system and user prompts for Gemini
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Add timeout to prevent hanging
            import socket
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(60)  # 60 second timeout
            
            try:
                response = self.model.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=4096,
                        temperature=0.2,
                    ),
                    safety_settings=[
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    ],
                    request_options={"timeout": 60}
                )
            finally:
                socket.setdefaulttimeout(original_timeout)
            
            # Check if response was blocked
            if not response.candidates:
                logger.error("Gemini returned no candidates")
                raise PatcherError("Gemini API returned no response candidates")
            
            candidate = response.candidates[0]
            
            # Check finish reason
            if candidate.finish_reason != 1:  # 1 = STOP (normal completion)
                logger.error(f"Gemini stopped unexpectedly (finish_reason={candidate.finish_reason})")
                raise PatcherError(f"Gemini stopped unexpectedly (finish_reason={candidate.finish_reason})")
            
            # Extract text from response
            content = response.text
            
            # Extract diff from code block
            patch = self._extract_diff(content)
            
            return patch
            
        except Exception as e:
            logger.error(f"Failed to generate patch: {e}")
            raise PatcherError(f"Gemini API error: {e}")
    
    def _extract_diff(self, content: str) -> str:
        """Extract unified diff from Gemini's response."""
        # Look for diff code block
        diff_match = re.search(r"```diff\n(.*?)\n```", content, re.DOTALL)
        if diff_match:
            patch = diff_match.group(1)
        else:
            # Fallback: look for any code block
            code_match = re.search(r"```\n(.*?)\n```", content, re.DOTALL)
            if code_match:
                patch = code_match.group(1)
            # Last resort: return content as-is if it looks like a diff
            elif content.strip().startswith("---") or content.strip().startswith("diff"):
                patch = content.strip()
            else:
                raise PatcherError("Could not extract diff from Gemini response")
        
        # Clean up the patch:
        # 1. Remove trailing whitespace from each line
        lines = patch.split('\n')
        lines = [line.rstrip() for line in lines]
        
        # 2. Remove empty lines at the end
        while lines and not lines[-1]:
            lines.pop()
        
        # 3. Rejoin with newlines and add final newline
        patch = '\n'.join(lines) + '\n'
        
        return patch
    
    def validate_patch(self, patch: str) -> bool:
        """
        Validate patch against safety guardrails.
        
        Args:
            patch: Unified diff content
        
        Returns:
            True if patch is safe to apply
        
        Raises:
            PatcherError if patch violates guardrails
        """
        lines = patch.splitlines()
        
        # Check line count
        if len(lines) > self.MAX_PATCH_LINES:
            raise PatcherError(
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
                    raise PatcherError(f"Forbidden path in patch: {path}")
            
            # Check for parent directory traversal
            if ".." in path:
                raise PatcherError(f"Parent traversal in patch: {path}")
            
            # Check if path matches allowed patterns
            allowed = any(re.match(pattern, path) for pattern in self.ALLOWED_PATTERNS)
            if not allowed:
                logger.debug(f"Path {path} doesn't match allowed patterns, but proceeding")
        
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
