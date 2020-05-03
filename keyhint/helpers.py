# Standard
import logging
import subprocess
import re
import collections

# Extra


def get_active_window_info():

    root = subprocess.Popen(
        ["xprop", "-root", "_NET_ACTIVE_WINDOW"], stdout=subprocess.PIPE
    )
    stdout, stderr = root.communicate()

    m = re.search(b"^_NET_ACTIVE_WINDOW.* ([\w]+)$", stdout)

    if m != None:
        window_id = m.group(1)
        window = subprocess.Popen(
            ["xprop", "-id", window_id, "WM_NAME", "WM_CLASS"], stdout=subprocess.PIPE
        )
        stdout, stderr = window.communicate()
    else:
        return None

    wm_name = wm_class = None

    match = re.search(b'WM_NAME\(\w+\) = "(?P<name>.+)"', stdout)
    if match != None:
        wm_name = match.group("name").decode("utf8")

    match = re.search(b'WM_CLASS\(\w+\) = "(?P<class>.+?)"', stdout)
    if match != None:
        wm_class = match.group("class").decode("utf8")

    return wm_name, wm_class


def get_something():
    logger = logging.getLogger(__name__)
    logger.info("Logging from subroutine")
    return "Hello You!"


def init_logging(name: str, log_level: int, to_file: bool = False) -> logging.Logger:
    """Initialize Logger with formatting and desired level.

    Arguments:
        log_level {logging._Level} -- Desired loglevel
        to_file {bool} -- Log also to file on disk, 

    Returns:
        logging.Logger -- Formatted logger with desired level
    """
    if to_file:
        logging.basicConfig(
            filename="pyshortcut.log",
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
