"""
Test file for sample_buggy_app.py
These tests will fail initially and pass after SafeRunner fixes the bugs.
"""
import pytest
from sample_buggy_app import divide, calculate_average, get_user_name


def test_divide_normal():
    """Test normal division."""
    assert divide(10, 2) == 5.0
    assert divide(15, 3) == 5.0


def test_divide_by_zero():
    """Test division by zero handling."""
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide(10, 0)


def test_calculate_average_normal():
    """Test normal average calculation."""
    assert calculate_average([1, 2, 3, 4, 5]) == 3.0
    assert calculate_average([10, 20]) == 15.0


def test_calculate_average_empty():
    """Test empty list handling."""
    with pytest.raises(ValueError, match="Cannot calculate average of empty list"):
        calculate_average([])


def test_get_user_name_normal():
    """Test normal user name retrieval."""
    user = {"first_name": "John", "last_name": "Doe"}
    assert get_user_name(user) == "John Doe"


def test_get_user_name_missing_keys():
    """Test missing keys handling."""
    with pytest.raises(ValueError, match="Missing required user fields"):
        get_user_name({"first_name": "John"})
    
    with pytest.raises(ValueError, match="Missing required user fields"):
        get_user_name({"last_name": "Doe"})
