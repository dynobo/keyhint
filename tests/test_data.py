# Standard
from pathlib import Path
import json

# Extra
import pytest

# Own
from .context import pyshortcuts

data_path = Path(__file__).parent.parent / "data"


def test_validate_json():
    """Are all files in the data folder valid json files?"""
    json_files = list(data_path.glob("*.json"))
    failed = 0

    for json_file in json_files:
        try:
            with open(json_file) as f:
                data = json.load(f)
        except Exception:
            failed += 1

    assert failed == 0
