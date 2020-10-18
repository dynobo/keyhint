"""Helper functions not really tied to the application."""

# Standard
import logging
import os
import subprocess
import re
import platform
from typing import Tuple, Union
from pathlib import Path


def init_logging(name: str, log_level: int = logging.DEBUG) -> logging.Logger:
    """Initialize Logger with formatting and desired level.

    Arguments
        log_level {logging._Level} -- Desired loglevel

    Returns
        logging.Logger -- Formatted logger with desired level

    """
    platform_system = platform.system()
    if platform_system == "Windows":
        logging.basicConfig(
            filename="keyhint.log",
            filemode="w",
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%H:%M:%S",
            level=log_level,
        )
    else:
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%H:%M:%S",
            level=log_level,
        )

    logger = logging.getLogger(name)
    return logger


def get_active_window_info(platform_os) -> Tuple[str, str]:
    """Gather information about active window, distinquishs between os."""
    app_process: str = ""
    app_title: str = ""

    if platform_os == "Linux":
        app_process, app_title = get_active_window_info_x()
    elif platform_os == "Windows":
        app_process, app_title = get_active_window_info_win()
    return app_process, app_title


def get_active_window_info_win() -> Tuple[str, str]:  # pylint: disable=R0914
    """Read app_process and app_title on X based Linux systems."""
    app_title = ""
    app_process = ""

    from ctypes import (  # type: ignore # noqa
        windll,
        create_unicode_buffer,
        create_string_buffer,
        c_ulong,
        sizeof,
        wintypes,
        byref,
    )

    # Get handle and title of active window
    handle_window = windll.user32.GetForegroundWindow()
    length = windll.user32.GetWindowTextLengthW(handle_window)
    uc_buf = create_unicode_buffer(length + 1)
    windll.user32.GetWindowTextW(handle_window, uc_buf, length + 1)
    if uc_buf.value:
        app_title = uc_buf.value

    # Get Process ID from window handle
    pid = wintypes.DWORD()
    windll.user32.GetWindowThreadProcessId(handle_window, byref(pid))

    # Get Process name from Process ID
    h_module = c_ulong()
    count = c_ulong()
    str_buf = create_string_buffer(30)

    h_process = windll.kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
    if h_process:
        windll.psapi.EnumProcessModules(
            h_process, byref(h_module), sizeof(h_module), byref(count)
        )
        windll.psapi.GetModuleBaseNameA(
            h_process, h_module.value, str_buf, sizeof(uc_buf)
        )
        windll.kernel32.CloseHandle(h_process)
        app_process = "".join(
            [b.decode("utf-8") for b in str_buf if b.decode("utf-8") != "\x00"]
        )

    return app_process, app_title


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


def remove_emojis(text: str) -> str:
    """Strip emojis from string."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F926-\U0001F937"
        "\U00010000-\U0010FFFF"
        "\u200D"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u23CF"
        "\u23E9"
        "\u231A"
        "\u3030"
        "\uFE0F"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(r"", text)


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
    platform_system = platform.system()  # 'Linux', 'Darwin' or 'Windows'

    config_path: Union[Path, None] = None

    if platform_system == "Linux":
        xdg_conf = os.getenv("XDG_CONFIG_HOME", None)
        if xdg_conf:
            config_path = Path(xdg_conf)
        else:
            config_path = Path.home() / ".config"
    elif platform_system == "Darwin":
        pass
    elif platform_system == "Windows":
        config_path = Path.home() / "AppData" / "Roaming"

    return config_path
