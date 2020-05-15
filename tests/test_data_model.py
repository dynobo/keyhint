# Standard
from pathlib import Path
import yaml

# Own
from .context import keyhint

config_dir = Path(__file__).parent.parent / "keyhint" / "config"


def test_validate_yaml():
    """Are default config/hints files valid yaml files?"""
    hints_file = config_dir / "hints.yaml"
    config_file = config_dir / "config.yaml"
    failed = 0

    for yaml_file in [hints_file, config_file]:
        with open(yaml_file) as file:
            try:
                _ = yaml.safe_load(file)
            except yaml.YAMLError:
                failed += 1

    assert hints_file.exists()
    assert config_file.exists()
    assert failed == 0


def test_data_string_representation():
    data = keyhint.data_model.HintsData()
    data_str = data.__repr__()
    should_contain = [
        "<dataclass>",
        "testrun:",
        "app_process:",
        "app_title:",
        "config_path:",
        "hints:",
        "config:",
        "platform_os:",
        "</dataclass>",
    ]
    assert all([s in data_str for s in should_contain])
