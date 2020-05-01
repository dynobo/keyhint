# Standard

# Extra
import pytest

# Own
from .context import pyshortcut



def test_helpers_get_something():
    """Does the function retrieve what's expected?"""
    assert pyshortcut.helpers.get_something() == "Hello You!"

