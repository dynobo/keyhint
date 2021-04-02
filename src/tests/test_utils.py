"""Test the utility functions."""

from pathlib import Path

from keyhint import utils


def test_load_default_hints():
    """Test loading of yaml files shipped with package."""
    hints = utils.load_default_hints()
    yaml_files = (Path(__file__).parent.parent / "keyhint" / "config").glob("*.yaml")

    assert len(hints) == len(list(yaml_files))
