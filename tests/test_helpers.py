"""Test helper methods."""

# Standard
import logging

# Own
from .context import keyhint


def test_helpers_init_logging():
    """Test if function returns a logger."""
    assert isinstance(keyhint.helpers.init_logging("test_logger"), logging.Logger)
