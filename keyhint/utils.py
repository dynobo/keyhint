import importlib
import os
import re
import subprocess
from pathlib import Path, PosixPath
from typing import Iterable, List, Tuple, Union

import yaml


def _load_yaml_file(file: str) -> dict:
    try:
        text = importlib.resources.read_text("keyhint.config", file)
        result = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        print(exc)
        result = {}
    return result


def _discover_hint_files() -> Iterable[Path]:
    f = importlib.resources.read_text("keyhint.config", "all.yaml")
    all_files = yaml.safe_load(f)

    return all_files["hint-files"]


def load_hints() -> List[dict]:
    files = _discover_hint_files()
    hints = [_load_yaml_file(f) for f in files]
    hints = sorted(hints, key=lambda k: k["title"])
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


if __name__ == "__main__":
    load_hints()
