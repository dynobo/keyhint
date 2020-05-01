# Standard

# Extra
import pytest

# Own
from .context import pyshortcut



def test_core_return_code():
    """Does the program quit correctely?"""
    assert pyshortcut.main() == 0

