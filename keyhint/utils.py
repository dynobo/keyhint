import ast
import os
import re
import subprocess
from pathlib import Path, PosixPath
from typing import Iterable, List, Tuple, Union

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


def get_active_window_info_wayland():
    app_command = 'gdbus call -e -d org.gnome.Shell -o /org/gnome/Shell -m org.gnome.Shell.Eval global.get_window_actors\(\)[`gdbus call -e -d org.gnome.Shell -o /org/gnome/Shell -m org.gnome.Shell.Eval global.get_window_actors\(\).findIndex\(a\=\>a.meta_window.has_focus\(\)===true\) | cut -d"\'" -f 2`].get_meta_window\(\).get_wm_class\(\)'
    app_process = subprocess.Popen(
        app_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    app_retval = app_process.stdout.read()
    app_retcode = app_process.wait()

    app_tuple_string = app_retval.decode("utf-8").strip()
    # We now have a string that looks like:
    # (true, "\"Qur'an App"\")

    app_tuple_string = app_tuple_string.replace("(true", "(True")
    app_tuple_string = app_tuple_string.replace("(false", "(False")
    # We now have a string that looks like a python tuple:
    # (True, "\"Qur'an App"\")

    app_tuple = ast.literal_eval(app_tuple_string)
    app = app_tuple[1]
    # We now have a string with quotes in it that looks like:
    # "Qur'an App"

    app = ast.literal_eval(app)
    # We now have a string that looks like:
    # Qur'an App
    return app


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
    app_title = app_process = ""

    match = re.search(r'WM_NAME\(\w+\) = "(?P<name>.+)"', stdout)
    if match is not None:
        app_title = match.group("name")

    match = re.search(r'WM_CLASS\(\w+\) =.*"(?P<class>.+?)"$', stdout)
    if match is not None:
        app_process = match.group("class")

    return app_process, app_title


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
