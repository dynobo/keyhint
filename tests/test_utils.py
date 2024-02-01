"""Test the utility functions."""

from pathlib import Path

from keyhint import utils


def test_load_default_sheets():
    """Test loading of toml files shipped with package."""
    sheets = utils.load_default_sheets()
    toml_files = (Path(__file__).parent.parent / "keyhint" / "config").glob("*.toml")

    assert len(sheets) == len(list(toml_files))
