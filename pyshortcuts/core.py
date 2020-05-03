# Standard
import logging

# Extra

# Own
from . import helpers
from .shortcuts import Shortcuts
from .display import Display
from .handlers.abstract_handler import AbstractHandler
from .handlers.active_window_handler import ActiveWindowHandler
from .handlers.load_index_handler import LoadIndexHandler
from .handlers.load_shortcuts_handler import LoadShortcutsHandler
from .handlers.show_window_handler import ShowWindowHandler
from .data_model import ShortCutsData

__author__ = "dynobo"
__email__ = "dynobo@mailbox.org"
__version__ = "0.1.0"


def client_code(handler: AbstractHandler, data: ShortCutsData) -> ShortCutsData:
    """Wrapper around Chain of Responsibility classes.

    Arguments:
        handler {Handler} -- Most outer handler
        normcap_data {NormcapData} -- NormCap's session data

    Returns:
        NormcapData -- Enriched NormCap's session data
    """
    result = handler.handle(data)
    return result


def main():
    logger = helpers.init_logging(__name__, logging.DEBUG, to_file=False)
    logger.info("Starting pyshortcuts v%s ...", __version__)

    # Central data model
    data = ShortCutsData()

    # Define handlers
    active_window = ActiveWindowHandler()
    load_index = LoadIndexHandler()
    load_shortcuts = LoadShortcutsHandler()
    show_window = ShowWindowHandler()
    active_window.set_next(load_index).set_next(load_shortcuts).set_next(show_window)

    data = client_code(active_window, data)
    print(data)

    return 0


if __name__ == "__main__":
    main()
