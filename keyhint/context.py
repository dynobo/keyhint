"""Functions to provide info about the context in which keyhint was started."""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import traceback

logger = logging.getLogger("keyhint")


def is_using_wayland() -> bool:
    """Check if we are running on Wayland DE.

    Returns:
        [bool] -- {True} if probably Wayland
    """
    return "WAYLAND_DISPLAY" in os.environ


def get_gnome_version() -> str:
    """Detect Gnome version of current session.

    Returns:
        Version string or '(n/a)'.
    """
    if not shutil.which("gnome-shell"):
        return "(n/a)"

    try:
        output = subprocess.check_output(
            ["gnome-shell", "--version"],  # noqa: S607
            shell=False,  # noqa: S603
            text=True,
        )
        if result := re.search(r"\s+([\d\.]+)", output.strip()):
            gnome_version = result.groups()[0]
    except Exception as e:
        logger.warning("Exception when trying to get gnome version from cli %s", e)
        return "(n/a)"
    else:
        return gnome_version


def is_flatpak_package() -> bool:
    """Check if the application is running inside a flatpak package."""
    return os.getenv("FLATPAK_ID") is not None


def get_kde_version() -> str:
    """Detect KDE platform version of current session.

    Returns:
        Version string or '(n/a)'.
    """
    if not shutil.which("plasma-desktop"):
        return "(n/a)"

    try:
        output = subprocess.check_output(
            ["plasma-desktop", "--version"],  # noqa: S607
            shell=False,  # noqa: S603
            text=True,
        )
        if result := re.search(r"Platform:\s+([\d+\.]+)", output.strip()):
            kde_version = result.groups()[0]
    except Exception as e:
        logger.warning("Exception when trying to get kde version from cli %s", e)
        return "(n/a)"
    else:
        return kde_version


def get_desktop_environment() -> str:
    """Detect used desktop environment."""
    kde_full_session = os.environ.get("KDE_FULL_SESSION", "").lower()
    xdg_current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    desktop_session = os.environ.get("DESKTOP_SESSION", "").lower()
    gnome_desktop_session_id = os.environ.get("GNOME_DESKTOP_SESSION_ID", "")
    hyprland_instance_signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")

    if gnome_desktop_session_id == "this-is-deprecated":
        gnome_desktop_session_id = ""

    de = "not detected"

    if gnome_desktop_session_id or "gnome" in xdg_current_desktop:
        de = f"Gnome v{get_gnome_version()}"
    if kde_full_session or "kde-plasma" in desktop_session:
        de = f"KDE v{get_kde_version()}"
    if "sway" in xdg_current_desktop or "sway" in desktop_session:
        de = "Sway"
    if "unity" in xdg_current_desktop:
        de = "Unity"
    if hyprland_instance_signature:
        de = "Hyprland"
    if "awesome" in xdg_current_desktop:
        de = "Awesome"

    return de


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
        logger.error(  # noqa: TRY400  # the stacktrace should be before message
            "Couldn't detect active application window.\n"
            "KeyHint supports Wayland and Xorg.\n"
            "For Wayland, the installation of the 'Window Calls' gnome extension is "
            "required:\nhttps://extensions.gnome.org/extension/4724/window-calls\n"
            "For Xorg, the 'xprop' command is required. Check your system repository "
            "to identify its package.\n"
            "If you met the prerequisites but still see this, please create an issue "
            "incl. the traceback above on:\nhttps://github.com/dynobo/keyhint/issues"
        )
        sys.exit(1)

    logger.debug("Detected wm_class: '%s'.", wm_class)
    logger.debug("Detected window_title: '%s'.", window_title)

    if "" in [wm_class, window_title]:
        logger.error(
            "Couldn't detect active window! Please report this error "
            "together with information about your OS and display server on "
            "https://github.com/dynobo/keyhint/issues"
        )

    return wm_class, window_title
