"""Functions to provide info about the context in which keyhint was started."""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
from datetime import datetime

logger = logging.getLogger("keyhint")


def is_using_wayland() -> bool:
    """Check if we are running on Wayland DE.

    Returns:
        [bool] -- {True} if probably Wayland
    """
    return "WAYLAND_DISPLAY" in os.environ


def has_xprop() -> bool:
    """Check if xprop is installed.

    Returns:
        [bool] -- {True} if xprop is installed
    """
    return shutil.which("xprop") is not None


def get_gnome_version() -> str:
    """Detect Gnome version of current session.

    Returns:
        Version string or '(n/a)'.
    """
    if not shutil.which("gnome-shell"):
        return "(n/a)"

    try:
        output = subprocess.check_output(  # noqa: S603
            ["gnome-shell", "--version"],  # noqa: S607
            shell=False,
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
    if not shutil.which("plasmashell"):
        return "(n/a)"

    try:
        output = subprocess.check_output(  # noqa: S603
            ["plasmashell", "--version"],  # noqa: S607
            shell=False,
            text=True,
        )
        if result := re.search(r"([\d+\.]+)", output.strip()):
            kde_version = result.groups()[0]
    except Exception as e:
        logger.warning("Exception when trying to get kde version from cli %s", e)
        return "(n/a)"
    else:
        return kde_version


def get_desktop_environment_and_version() -> tuple[str, str]:
    """Detect used desktop environment."""
    kde_full_session = os.environ.get("KDE_FULL_SESSION", "").lower()
    xdg_current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    desktop_session = os.environ.get("DESKTOP_SESSION", "").lower()
    gnome_desktop_session_id = os.environ.get("GNOME_DESKTOP_SESSION_ID", "")
    hyprland_instance_signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")

    if gnome_desktop_session_id == "this-is-deprecated":
        gnome_desktop_session_id = ""

    de = "(DE not detected)"
    version = "(version not detected)"

    if gnome_desktop_session_id or "gnome" in xdg_current_desktop:
        de = "Gnome"
        version = get_gnome_version()
    if kde_full_session or "kde-plasma" in desktop_session:
        de = "KDE"
        version = get_kde_version()
    if "sway" in xdg_current_desktop or "sway" in desktop_session:
        de = "Sway"
    if "unity" in xdg_current_desktop:
        de = "Unity"
    if hyprland_instance_signature:
        de = "Hyprland"
    if "awesome" in xdg_current_desktop:
        de = "Awesome"

    return de, version


def has_window_calls_extension() -> bool:
    cmd_introspect = (
        "gdbus introspect --session --dest org.gnome.Shell "
        "--object-path /org/gnome/Shell/Extensions/Windows "
    )
    stdout_bytes = subprocess.check_output(cmd_introspect, shell=True)  # noqa: S602
    stdout = stdout_bytes.decode("utf-8")
    return all(["List" in stdout, "GetTitle" in stdout])


def get_active_window_via_window_calls() -> tuple[str, str]:
    """Retrieve active window class and active window title on Gnome + Wayland.

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


def get_active_window_via_kwin() -> tuple[str, str]:
    """Retrieve active window class and active window title on KDE + Wayland.

    Returns:
        Tuple(str, str): window class, window title
    """
    kwin_script = textwrap.dedent("""
        console.info("keyhint test");
        client = workspace.activeClient;
        title = client.caption;
        wm_class = client.resourceClass;
        console.info(`keyhint_out: wm_class=${wm_class}, window_title=${title}`);
        """)

    with tempfile.NamedTemporaryFile(suffix=".js", delete=False) as fh:
        fh.write(kwin_script.encode())
        cmd_load = (
            "gdbus call --session --dest org.kde.KWin "
            "--object-path /Scripting "
            f"--method org.kde.kwin.Scripting.loadScript '{fh.name}'"
        )
        logger.debug("cmd_load: %s", cmd_load)
        stdout = subprocess.check_output(cmd_load, shell=True).decode()  # noqa: S602

    logger.debug("loadScript output: %s", stdout)
    script_id = stdout.strip().strip("()").split(",")[0]

    since = str(datetime.now())

    cmd_run = (
        "gdbus call --session --dest org.kde.KWin "
        f"--object-path /{script_id} "
        "--method org.kde.kwin.Script.run"
    )
    subprocess.check_output(cmd_run, shell=True)  # noqa: S602

    cmd_unload = (
        "gdbus call --session --dest org.kde.KWin "
        "--object-path /Scripting "
        f"--method org.kde.kwin.Scripting.unloadScript {script_id}"
    )
    subprocess.check_output(cmd_unload, shell=True)  # noqa: S602

    # Unfortunately, we can read script output from stdout, because of a KDE bug:
    # https://bugs.kde.org/show_bug.cgi?id=445058
    # The output has to be read through journalctl instead. A timestamp for
    # filtering speeds up the process.
    log_lines = (
        subprocess.check_output(  # noqa: S602
            f'journalctl --user -o cat --since "{since}"',
            shell=True,
        )
        .decode()
        .split("\n")
    )
    logger.debug("Journal message: %s", log_lines)
    result_line = [m for m in log_lines if "keyhint_out" in m][-1]
    match = re.search(r"keyhint_out: wm_class=(.+), window_title=(.+)", result_line)
    if match:
        wm_class = match.group(1)
        title = match.group(2)
    else:
        logger.warning("Could not extract window info from KWin log!")
        wm_class = title = ""

    return wm_class, title


def get_active_window_via_xprop() -> tuple[str, str]:
    """Retrieve active window class and active window title on Xorg desktops.

    Returns:
        Tuple(str, str): window class, window title
    """
    # Query id of active window
    stdout_bytes: bytes = subprocess.check_output(  # noqa: S602
        "xprop -root _NET_ACTIVE_WINDOW",  # noqa: S607
        shell=True,
    )
    stdout = stdout_bytes.decode()

    # Identify id of active window in output
    match = re.search(r"^_NET_ACTIVE_WINDOW.* ([\w]+)$", stdout)
    if match is None:
        # Stop, if there is not active window detected
        return "", ""
    window_id: str = match.group(1)

    # Query app_title and app_process
    stdout_bytes = subprocess.check_output(  # noqa: S602
        f"xprop -id {window_id} WM_NAME WM_CLASS",
        shell=True,
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
