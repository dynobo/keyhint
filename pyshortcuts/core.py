# Standard
import logging

# Extra

# Own
from . import helpers
from .shortcuts import Shortcuts

__author__ = "dynobo"
__email__ = "dynobo@mailbox.org"
__version__ = "0.1.0"


def main():
    logger = helpers.init_logging(__name__, logging.DEBUG, to_file=False)
    logger.info("Starting pyshortcuts v%s ...", __version__)
    wm_name, wm_class = helpers.get_active_window_info()
    logger.info(
        "Active window name: '%s', active window class: '%s'", wm_name, wm_class
    )
    shortcuts = Shortcuts()
    keys = shortcuts.get_shortcuts(wm_name, wm_class)
    logger.info("Current contexts' shortcuts:\n%s", keys)
    return 0


if __name__ == "__main__":
    main()
