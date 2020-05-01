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
    logger = helpers.init_logging(__name__, logging.DEBUGi, to_file=False)
    logger.info("Starting pyshortcuts v%s ...", __version__)
    window_title = helpers.get_active_window_title()
    logger.info("Active Window Title: %s", window_title)
    shortcuts = Shortcuts()
    shortcuts.set_application(window_title)

    return 0


if __name__ == "__main__":
    main()
