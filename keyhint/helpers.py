"""Helper functions not really tied to the application."""

# Standard
import logging
import os
import subprocess
import re
import platform
from typing import Tuple, Union
from pathlib import Path


def init_logging(
    name: str, log_level: int = logging.DEBUG, to_file: bool = False
) -> logging.Logger:
    """Initialize Logger with formatting and desired level.

    Arguments
        log_level {logging._Level} -- Desired loglevel
        to_file {bool} -- Log also to file on disk

    Returns
        logging.Logger -- Formatted logger with desired level

    """
    if to_file:
        logging.basicConfig(
            filename="keyhints.log",
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
    wm_class: str = ""
    wm_name: str = ""

    if platform_os == "Linux":
        wm_class, wm_name = get_active_window_info_x()

    return wm_class.lower(), wm_name.lower()


def get_active_window_info_x() -> Tuple[str, str]:
    """Read wm_class and wm_name on X based Linux systems."""
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

    # Query wm_name and wm_class
    stdout_bytes = subprocess.check_output(
        f"xprop -id {window_id} WM_NAME WM_CLASS", shell=True
    )
    stdout = stdout_bytes.decode()

    # Extract wm_name and wm_class from output
    wm_name = wm_class = ""

    match = re.search(r'WM_NAME\(\w+\) = "(?P<name>.+)"', stdout)
    if match is not None:
        wm_name = match.group("name")

    match = re.search(r'WM_CLASS\(\w+\) =.*"(?P<class>.+?)"$', stdout)
    if match is not None:
        wm_class = match.group("class")

    return wm_class, wm_name


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
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u200d"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\u3030"
        "\ufe0f"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(r"", text)


def test_for_wayland():
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
    platform_system = platform.system()  #'Linux', 'Darwin' or 'Windows'

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
