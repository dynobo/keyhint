import importlib.resources
import logging
import os
import re
import subprocess
import traceback
from pathlib import Path, PosixPath
from typing import Iterable, List, Tuple, Union

import yaml

logger = logging.getLogger(__name__)


def _load_yaml(file: Union[PosixPath, str], from_resources=False) -> dict:
    try:
        if from_resources:
            text = importlib.resources.read_text("keyhint.config", file)
            result = yaml.safe_load(text)
        else:
            with open(file) as f:
                result = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(exc)
        result = {}
    return result


def _discover_hint_files() -> Iterable[Path]:
    files = importlib.resources.contents("keyhint.config")
    yaml_files = [f for f in files if f.endswith(".yaml")]
    return yaml_files


def load_default_hints() -> List[dict]:
    files = _discover_hint_files()
    hints = [_load_yaml(f, True) for f in files]
    hints = sorted(hints, key=lambda k: k["title"])
    return hints


def load_user_hints() -> List[dict]:
    config_path = get_users_config_path()
    files = (config_path / "keyhint").glob("*.yaml")
    hints = [_load_yaml(f) for f in files]
    hints = sorted(hints, key=lambda k: k["title"])
    return hints


def load_hints() -> List[dict]:
    hints = load_default_hints()
    user_hints = load_user_hints()

    for user_hint in user_hints:
        existed = False
        for hint in hints:
            # Update default hints by user hint (if existing)
            if hint["id"] == user_hint["id"]:
                hint.update(user_hint)
                existed = True
                break
        # If it didn't exist, append as new
        if not existed:
            hints.append(user_hint)

    return hints


def replace_keys(text: str) -> str:
    if text in ["PageUp", "PageDown"]:
        text = text.replace("Page", "Page ")

    text = text.replace("Down", "↓")
    text = text.replace("Up", "↑")
    text = text.replace("Left", "←")
    text = text.replace("Right", "→")
    # text = text.replace("Enter", "↵")
    return text


def get_active_window_info_wayland():
    # https://gist.github.com/rbreaves/257c3edfa301786e66e964d7ac036269
    def _get_cmd_result(cmd):
        stdout_bytes: bytes = subprocess.check_output(cmd, shell=True)
        stdout = stdout_bytes.decode()
        match = re.search(r"'(.+)'", stdout)
        return match.groups()[0].strip('"')

    cmd_eval = (
        "gdbus call -e -d org.gnome.Shell -o /org/gnome/Shell -m org.gnome.Shell.Eval"
    )
    cmd_win_idx = (
        ' "global.get_window_actors().findIndex(a=>a.meta_window.has_focus()===true)"'
    )
    window_idx = _get_cmd_result(cmd_eval + cmd_win_idx)

    cmd_wm_class = (
        f' "global.get_window_actors()[{window_idx}].get_meta_window().get_wm_class()"'
    )
    wm_class = _get_cmd_result(cmd_eval + cmd_wm_class)

    cmd_wm_title = (
        f' "global.get_window_actors()[{window_idx}].get_meta_window().get_title()"'
    )
    title = _get_cmd_result(cmd_eval + cmd_wm_title)

    return wm_class, title


def get_active_window_info_x() -> Tuple[str, str]:
    """Read app_process and app_title on X based Linux systems."""
    # Query id of active window
    stdout_bytes: bytes = subprocess.check_output(
        "xprop -root _NET_ACTIVE_WINDOW", shell=True
    )
    stdout = stdout_bytes.decode()

    # Identify id of active window in output
    match = re.search(r"^_NET_ACTIVE_WINDOW.* ([\w]+)$", stdout)
    if match is None:
        # Stop, if there is not active window detected
        return "", ""
    window_id: str = match.group(1)

    # Query app_title and app_process
    stdout_bytes = subprocess.check_output(
        f"xprop -id {window_id} WM_NAME WM_CLASS", shell=True
    )
    stdout = stdout_bytes.decode()

    # Extract app_title and app_process from output
    title = wm_class = ""

    match = re.search(r'WM_NAME\(\w+\) = "(?P<name>.+)"', stdout)
    if match is not None:
        title = match.group("name")

    match = re.search(r'WM_CLASS\(\w+\) =.*"(?P<class>.+?)"$', stdout)
    if match is not None:
        wm_class = match.group("class")

    return wm_class, title


def is_using_wayland():
    """Check if we are running on Wayland DE.
    Returns
        [bool] -- {True} if probably Wayland
    """
    result = False
    if "WAYLAND_DISPLAY" in os.environ:
        result = True
    return result


def get_users_config_path() -> Union[Path, None]:
    """Retrieve path for config files.
    Returns
        Path -- Root of config folder
    """
    config_path: Union[Path, None] = None

    xdg_conf = os.getenv("XDG_CONFIG_HOME", None)
    if xdg_conf:
        config_path = Path(xdg_conf)
    else:
        config_path = Path.home() / ".config"

    return config_path


def detect_active_window():
    wm_class = window_title = None

    try:
        if is_using_wayland():
            wm_class, window_title = get_active_window_info_wayland()
        else:
            wm_class, window_title = get_active_window_info_x()
    except Exception:
        logger.error("Traceback:\n" + traceback.format_tb())
        logger.error(
            "Couldn't detect active application window."
            "KeyHint currently should support Wayland and X. If you are using one "
            "of those and see this error, please create and issue incl. the tracebackk "
            "above on https://github.com/dynobo/keyhint/issues."
        )

    logger.debug(
        f"Detected wm_class: '{wm_class}'. Detected window_title: '{window_title}'."
    )
    return wm_class, window_title


if __name__ == "__main__":
    load_hints()