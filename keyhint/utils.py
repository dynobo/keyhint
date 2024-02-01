"""Various utility functions."""

import json
import logging
import os
import re
import subprocess
import traceback
from pathlib import Path

import toml

logger = logging.getLogger(__name__)

CONFIG_PATH = __file__.rstrip("utils.py") + "config"


def _load_toml(file_path: str | os.PathLike) -> dict:
    """Load a toml file from resource path or other path.

    Args:
        file_path: Filename in resources, or complete path to file.
        from_resources: Set to true to load from resource. Defaults
            to False.

    Returns:
        [description]
    """
    try:
        result = toml.load(str(Path(file_path).resolve()))
    except Exception as exc:
        print(exc)  # noqa: T201
        result = {}
    return result


def load_default_sheets() -> list[dict]:
    """Load default keyhints from toml files shipped with the package.

    Returns:
        List[dict]: List of application keyhints and meta info.
    """
    sheets = [_load_toml(f) for f in Path(CONFIG_PATH).glob("*.toml")]
    sheets = sorted(sheets, key=lambda k: k["title"])
    return sheets  # noqa: RET504


def load_user_sheets() -> list[dict]:
    """Load cheatsheets from toml files in the users .config/keyhint/ directory.

    Returns:
        List[dict]: List of application keyhints and meta info.
    """
    if config_path := get_users_config_path():
        files = (config_path / "keyhint").glob("*.toml")
        sheets = [_load_toml(f) for f in files]
        sheets = sorted(sheets, key=lambda k: k["title"])
    else:
        sheets = []
    return sheets


def _expand_includes(sheets: list[dict]) -> list[dict]:
    new_sheets = []
    for s in sheets:
        if includes := s.get("include", []):
            for include in includes:
                included_sheets = [c for c in sheets if c["id"] == include]
                if not included_sheets:
                    message = (
                        f"Cheatsheet ID '{included_sheets}' "
                        f"included by '{s['id']}' not found!"
                    )
                    raise ValueError(message)
                included_sheet = included_sheets[0]
                included_sheet["section"] = {
                    f"{included_sheet['title']} - {k}": v
                    for k, v in included_sheet["section"].items()
                }
                s["section"].update(included_sheets[0]["section"])
        new_sheets.append(s)
    return new_sheets


def _remove_empty_sections(sheets: list[dict]) -> list[dict]:
    for sheet in sheets:
        sheet["section"] = {k: v for k, v in sheet["section"].items() if v}
    return sheets


def load_sheets() -> list[dict]:
    """Load unified default keyhints and keyhints from user config.

    First the default keyhints are loaded, then they are update (added/overwritten)
    by the keyhints loaded from user config.

    Returns:
        List[dict]: List of application keyhints and meta info.
    """
    sheets = load_default_sheets()
    user_sheets = load_user_sheets()

    for user_sheet in user_sheets:
        existed = False
        for sheet in sheets:
            # Update default sheet by user sheet (if existing)
            if sheet["id"] == user_sheet["id"]:
                user_sheet_sections = user_sheet.pop("section")
                sheet.update(user_sheet)
                sheet["section"].update(user_sheet_sections)
                existed = True
                break
        # If it didn't exist, append as new
        if not existed:
            sheets.append(user_sheet)

    sheets = _expand_includes(sheets)
    sheets = _remove_empty_sections(sheets)
    return sheets  # noqa: RET504


def replace_keys(text: str) -> str:
    """Replace key names by corresponding unicode symbol.

    Args:
        text (str): Text with key names.

    Returns:
        str: Text where some key names have been replaced by unicode symbol.
    """
    if text in {"PageUp", "PageDown"}:
        text = text.replace("Page", "Page ")

    text = text.replace("Down", "↓")
    text = text.replace("Up", "↑")
    text = text.replace("Left", "←")
    text = text.replace("Right", "→")
    text = text.replace("Direction", "←↓↑→")
    text = text.replace("PlusMinus", "±")
    text = text.replace("Plus", "＋")  # noqa: RUF001
    text = text.replace("Minus", "−")  # noqa: RUF001
    text = text.replace("Slash", "/")

    return text  # noqa: RET504


def get_active_window_info_wayland() -> tuple[str, str]:
    """Retrieve active window class and active window title on Wayland.

    Inspired by https://gist.github.com/rbreaves/257c3edfa301786e66e964d7ac036269

    Returns:
        Tuple(str, str): window class, window title
    """

    def _get_cmd_result(cmd: str) -> str:
        stdout_bytes: bytes = subprocess.check_output(cmd, shell=True)  # noqa: S602
        stdout = stdout_bytes.decode("utf-8")
        if match := re.search(r"'(.+)'", stdout):
            return match.groups()[0].strip('"')
        return ""

    cmd_windows_list = (
        "gdbus call --session --dest org.gnome.Shell "
        "--object-path /org/gnome/Shell/Extensions/Windows "
        "--method org.gnome.Shell.Extensions.Windows.List"
    )
    stdout = _get_cmd_result(cmd_windows_list)
    windows = json.loads(stdout)
    focused_window = next(filter(lambda x: x["focus"], windows))
    wm_class = focused_window["wm_class"]

    cmd_windows_get_title = (
        "gdbus call --session --dest org.gnome.Shell "
        "--object-path /org/gnome/Shell/Extensions/Windows "
        "--method org.gnome.Shell.Extensions.Windows.GetTitle "
        f"{focused_window['id']}"
    )
    title = _get_cmd_result(cmd_windows_get_title)

    return wm_class, title


def get_active_window_info_x() -> tuple[str, str]:
    """Retrieve active window class and active window title on Xorg desktops.

    Returns:
        Tuple(str, str): window class, window title
    """
    # Query id of active window
    stdout_bytes: bytes = subprocess.check_output(
        "xprop -root _NET_ACTIVE_WINDOW",  # noqa: S607
        shell=True,  # noqa: S602
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
        f"xprop -id {window_id} WM_NAME WM_CLASS",
        shell=True,  # noqa: S602
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

    Returns:
        [bool] -- {True} if probably Wayland
    """
    return "WAYLAND_DISPLAY" in os.environ


def get_users_config_path() -> Path | None:
    """Retrieve path for config files.

    Returns:
        Path -- Root of config folder
    """
    if xdg_conf := os.getenv("XDG_CONFIG_HOME", None):
        return Path(xdg_conf)

    return Path.home() / ".config"


def detect_active_window() -> tuple[str, str]:
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
        logger.exception(
            "Couldn't detect active application window."
            "KeyHint supports Wayland and X.\n"
            "For Wayland, the installation of the 'Window Calls' gnome extension is "
            "required: https://extensions.gnome.org/extension/4724/window-calls/\n"
            "For Xorg, the 'xprop' command is required, check your systems repository "
            "to identify its package.\n"
            "If you met the prerequisites but still see this, please create an issue"
            "incl. the traceback above on https://github.com/dynobo/keyhint/issues."
        )

    logger.debug(
        "Detected wm_class: '%s'. Detected window_title: '%s'", wm_class, window_title
    )
    if "" in [wm_class, window_title]:
        logger.error(
            "Couldn't detect active window! Please report this error "
            "together with information about your OS and display server on "
            "https://github.com/dynobo/keyhint/issues"
        )

    return wm_class, window_title


if __name__ == "__main__":
    load_sheets()
