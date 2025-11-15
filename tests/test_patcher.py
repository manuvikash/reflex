"""Tests for patch generation and validation."""
import pytest
from control.patcher import Patcher, PatcherError


def test_validate_patch_line_limit():
    """Test that patches exceeding line limit are rejected."""
    patcher = Patcher()
    
    # Create a patch with too many lines
    large_patch = "--- a/test.py\n+++ b/test.py\n"
    large_patch += "\n".join([f"+line {i}" for i in range(200)])
    
    with pytest.raises(PatcherError, match="too large"):
        patcher.validate_patch(large_patch)


def test_validate_patch_forbidden_paths():
    """Test that patches touching forbidden paths are rejected."""
    patcher = Patcher()
    
    forbidden_patch = """--- a/etc/passwd
+++ b/etc/passwd
@@ -1,1 +1,1 @@
-root:x:0:0:root:/root:/bin/bash
+root:x:0:0:hacked:/root:/bin/bash
"""
    
    with pytest.raises(PatcherError, match="Forbidden path"):
        patcher.validate_patch(forbidden_patch)


def test_validate_patch_parent_traversal():
    """Test that patches with parent traversal are rejected."""
    patcher = Patcher()
    
    traversal_patch = """--- a/../../../etc/passwd
+++ b/../../../etc/passwd
@@ -1,1 +1,1 @@
-test
+hacked
"""
    
    with pytest.raises(PatcherError, match="Parent traversal"):
        patcher.validate_patch(traversal_patch)


def test_get_patch_summary():
    """Test patch summary extraction."""
    patcher = Patcher()
    
    patch = """--- a/src/main.py
+++ b/src/main.py
@@ -10,7 +10,7 @@
 def hello():
-    print("Hello")
+    print("Hello, World!")
     return True
--- a/tests/test_main.py
+++ b/tests/test_main.py
@@ -5,4 +5,5 @@
 def test_hello():
+    assert hello() == True
     pass
"""
    
    summary = patcher.get_patch_summary(patch)
    
    assert len(summary["files_modified"]) == 2
    assert "src/main.py" in summary["files_modified"]
    assert "tests/test_main.py" in summary["files_modified"]
    assert summary["additions"] == 2
    assert summary["deletions"] == 1


def test_extract_diff_from_code_block():
    """Test extracting diff from markdown code block."""
    patcher = Patcher()
    
    content = """Here's the fix:

```diff
--- a/test.py
+++ b/test.py
@@ -1,1 +1,1 @@
-old
+new
```

This should work!"""
    
    diff = patcher._extract_diff(content)
    assert "--- a/test.py" in diff
    assert "+new" in diff
    assert "This should work" not in diff
