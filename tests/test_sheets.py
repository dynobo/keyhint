"""Test the utility functions."""

from pathlib import Path

from keyhint import sheets


def test_load_default_sheets():
    """Test loading of toml files shipped with package."""
    default_sheets = sheets.load_default_sheets()
    toml_files = (Path(__file__).parent.parent / "keyhint" / "config").glob("*.toml")

    assert len(default_sheets) == len(list(toml_files))
