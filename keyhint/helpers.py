"""Helper functions not really tied to the application."""

# Standard
import logging
import os
import subprocess
import re
from typing import Tuple


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

    return wm_class, wm_name


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

    match = re.search(r'WM_CLASS\(\w+\) = "(?P<class>.+?)"', stdout)
    if match is not None:
        wm_class = match.group("class")

    return wm_class, wm_name


def test_for_wayland():
    """Check if we are running on Wayland DE.

    Returns
        [bool] -- {True} if probably Wayland

    """
    result = False
    if "WAYLAND_DISPLAY" in os.environ:
        result = True
    return result
