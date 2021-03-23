from pathlib import Path, PosixPath
from typing import Iterable, Union, List
import yaml


def _load_yaml_file(file: Union[str, PosixPath]) -> dict:
    with open(file, "r") as stream:
        try:
            result = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            result = {}
        return result


def _discover_hint_files() -> Iterable[Path]:
    config_dir = Path.cwd() / "keyhint" / "config"
    yaml_files = config_dir.glob("*.yaml")
    return yaml_files


def load_hints() -> List[dict]:
    files = _discover_hint_files()
    hints = [_load_yaml_file(f) for f in files]
    return hints


def replace_keys(text: str) -> str:
    text = text.upper()
    text = text.replace("DOWN", "🠣")
    text = text.replace("UP", "🠡")
    text = text.replace("LEFT", "🠠")
    text = text.replace("RIGHT", "🠢")
    text = text.replace("SHIFT", "⇧")
    text = text.replace("ENTER", "↵")
    text = text.replace("CTRL", "ctrl")
    text = text.replace("ALT", "alt")
    text = text.replace("SUPER", "super")
    text = text.replace("TAB", "tab")
    return text


if __name__ == "__main__":
    load_hints()