# Standard

# Extra
import pytest

# Own
from .context import keyhint


def test_helpers_get_something():
    """Does the function retrieve what's expected?"""
    assert keyhint.helpers.get_something() == "Hello You!"
