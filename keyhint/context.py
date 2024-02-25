"""Various utility functions."""

import json
import logging
import os
import re
import subprocess
import traceback

logger = logging.getLogger(__name__)


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

    focused_windows = list(filter(lambda x: x["focus"], windows))
    if not focused_windows:
        return "", ""

    focused_window = focused_windows[0]
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
