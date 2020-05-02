# Standard

# Extra
import pytest

# Own
from .context import pyshortcuts


def test_helpers_get_something():
    """Does the function retrieve what's expected?"""
    assert pyshortcuts.helpers.get_something() == "Hello You!"
