"""Various utility functions."""

import json
import logging
import os
import re
import subprocess
import traceback
from pathlib import Path
from typing import List, Tuple, Union

import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = __file__.rstrip("utils.py") + "config"


def _load_yaml(file: Union[str, os.PathLike]) -> dict:
    """Safely load a yaml file from resource path or other path.

    Args:
        file (Union[Path, str]): Filename in resources, or complete path to file.
        from_resources (bool, optional): Set to true to load from resource. Defaults
            to False.

    Returns:
        dict: [description]
    """
    try:
        with open(file, "r", encoding="utf-8") as stream:
            result = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        result = {}
    return result


def load_default_hints() -> List[dict]:
    """Load default keyhints from yaml files shipped with the package.

    Returns:
        List[dict]: List of application keyhints and metainfos.
    """
    hints = [_load_yaml(f) for f in Path(CONFIG_PATH).glob("*.yaml")]
    hints = sorted(hints, key=lambda k: k["title"])
    return hints


def load_user_hints() -> List[dict]:
    """Load keyhints from yaml files in the users .config/keyhint/ directory.

    Returns:
        List[dict]: List of application keyhints and metainfos.
    """
    if config_path := get_users_config_path():
        files = (config_path / "keyhint").glob("*.yaml")
        hints = [_load_yaml(f) for f in files]
        hints = sorted(hints, key=lambda k: k["title"])
    else:
        hints = []
    return hints


def _expand_includes(hints: List[dict]) -> List[dict]:
    new_hints = []
    for h in hints:
        if includes := h.get("include", []):
            for include in includes:
                included_hints = [h for h in hints if h["id"] == include]
                if not included_hints:
                    raise ValueError(
                        f"Hint ID '{included_hints}' included by '{h['id']}' not found!"
                    )
                included_hint = included_hints[0]
                included_hint["hints"] = {
                    f"{included_hint['title']} - {k}": v
                    for k, v in included_hint["hints"].items()
                }
                h["hints"].update(included_hints[0]["hints"])
        new_hints.append(h)
    return new_hints


def _remove_empty_sections(hints: List[dict]) -> List[dict]:
    for hint in hints:
        hint["hints"] = {k: v for k, v in hint["hints"].items() if v}
    return hints


def load_hints() -> List[dict]:
    """Load unified default keyhints and keyhints from user config.

    First the default keyhints are loaded, then they are update (added/overwritten)
    by the keyhints loaded from user config.

    Returns:
        List[dict]: List of application keyhints and metainfos.
    """
    hints = load_default_hints()
    user_hints = load_user_hints()

    for user_hint in user_hints:
        existed = False
        for hint in hints:
            # Update default hints by user hint (if existing)
            if hint["id"] == user_hint["id"]:
                user_hint_hints = user_hint.pop("hints")
                hint.update(user_hint)
                hint["hints"].update(user_hint_hints)
                existed = True
                break
        # If it didn't exist, append as new
        if not existed:
            hints.append(user_hint)

    hints = _expand_includes(hints)
    hints = _remove_empty_sections(hints)
    return hints


def replace_keys(text: str) -> str:
    """Replace key names by corresponding unicode symbol.

    Args:
        text (str): Text with key names.

    Returns:
        str: Text where some key names have been replaced by unicode symbole.
    """
    if text in {"PageUp", "PageDown"}:
        text = text.replace("Page", "Page ")

    text = text.replace("Down", "↓")
    text = text.replace("Up", "↑")
    text = text.replace("Left", "←")
    text = text.replace("Right", "→")
    text = text.replace("Direction", "←↓↑→")
    text = text.replace("PlusMinus", "±")
    text = text.replace("Plus", "＋")
    text = text.replace("Minus", "−")
    text = text.replace("Slash", "/")
    return text


def get_active_window_info_wayland() -> Tuple[str, str]:
    """Retrieve active window class and active window title on Wayland.

    Inspired by https://gist.github.com/rbreaves/257c3edfa301786e66e964d7ac036269

    Returns:
        Tuple(str, str): window class, window title
    """

    def _get_cmd_result(cmd: str) -> str:
        stdout_bytes: bytes = subprocess.check_output(cmd, shell=True)
        stdout = stdout_bytes.decode("utf-8")
        if match := re.search(r"'(.+)'", stdout):
            return match.groups()[0].strip('"')
        return ""

    cmd_windows_list = (
        "gdbus call --session --dest org.gnome.Shell "
        + "--object-path /org/gnome/Shell/Extensions/Windows "
        + "--method org.gnome.Shell.Extensions.Windows.List"
    )
    stdout = _get_cmd_result(cmd_windows_list)
    windows = json.loads(stdout)
    focused_window = list(filter(lambda x: x["focus"], windows))[0]
    wm_class = focused_window["wm_class"]

    cmd_windows_gettitle = (
        "gdbus call --session --dest org.gnome.Shell "
        + "--object-path /org/gnome/Shell/Extensions/Windows "
        + "--method org.gnome.Shell.Extensions.Windows.GetTitle "
        + f"{focused_window['id']}"
    )
    title = _get_cmd_result(cmd_windows_gettitle)

    return wm_class, title


def get_active_window_info_x() -> Tuple[str, str]:
    """Retrieve active window class and active window title on Xorg desktops.

    Returns:
        Tuple(str, str): window class, window title
    """
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


def is_using_wayland() -> bool:
    """Check if we are running on Wayland DE.

    Returns
        [bool] -- {True} if probably Wayland
    """
    return "WAYLAND_DISPLAY" in os.environ


def get_users_config_path() -> Union[Path, None]:
    """Retrieve path for config files.

    Returns
        Path -- Root of config folder
    """
    if xdg_conf := os.getenv("XDG_CONFIG_HOME", None):
        return Path(xdg_conf)

    return Path.home() / ".config"


def detect_active_window() -> Tuple[str, str]:
    """Get class and title of active window.

    Identify the OS and display server and pick the method accordingly.

    Returns:
        Tuple[str, str]: [description]
    """
    wm_class = window_title = ""

    try:
        if is_using_wayland():
            wm_class, window_title = get_active_window_info_wayland()
        else:
            wm_class, window_title = get_active_window_info_x()
    except Exception:
        traceback.print_stack()
        logger.error(
            "Couldn't detect active application window."
            "KeyHint supports Wayland and X.\n"
            "For Wayland, the installation of the 'Window Calls' gnome extension is "
            "required: https://extensions.gnome.org/extension/4724/window-calls/\n"
            "For Xorg, the 'xprop' command is required, check your systems repository "
            "to identify its package.\n"
            "If you met the prerequisits but still see this, please create an issue"
            "incl. the traceback above on https://github.com/dynobo/keyhint/issues."
        )

    logger.debug(
        f"Detected wm_class: '{wm_class}'. Detected window_title: '{window_title}'."
    )
    if "" in [wm_class, window_title]:
        logger.error(
            "Couldn't detect active window! Please report this errror "
            "together with information about your OS and display server on "
            "https://github.com/dynobo/keyhint/issues"
        )

    return wm_class, window_title


if __name__ == "__main__":
    load_hints()
