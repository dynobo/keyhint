"""Top level logic of keyhint. Entry point for module."""

# Standard
import logging
import sys

# Own
from . import helpers
from .handlers.abstract_handler import AbstractHandler
from .handlers.detect_application_handler import DetectApplicationHandler
from .handlers.select_hints_handler import SelectHintsHandler
from .handlers.load_configs_handler import LoadConfigsHandler
from .handlers.show_hints_handler import ShowHintsHandler
from .data_model import HintsData

# Basic information, e.g used in setup.py or in error report
__author__ = "dynobo"
__email__ = "dynobo@mailbox.org"
__repo__ = "https://github.com/dynobo/keyhint"
__version__ = "0.1.2"


def client_code(handler: AbstractHandler, data: HintsData) -> HintsData:
    """Wrap Chain of Responsibility classes.

    Args:
        handler (AbstractHandler): Most outer handler
        data (HintsData) -- Central data object

    Returns:
        HintsData: Central data object processed by handler

    """
    data = handler.handle(data)
    return data


def main(testrun=False):
    """Orchestrates the sequence of execution from start to end."""
    logger = helpers.init_logging(__name__, logging.ERROR, to_file=False)
    logger.info("Starting keyhint v%s ...", __version__)

    try:
        # Central data model
        data = HintsData()
        data.testrun = testrun

        # Define handlers
        load_configs = LoadConfigsHandler()
        detect_app = DetectApplicationHandler()
        select_hints = SelectHintsHandler()
        show_hints = ShowHintsHandler()

        # Define chain of handlers
        load_configs.set_next(detect_app).set_next(select_hints).set_next(show_hints)

        # Run chain of handlers
        data = client_code(load_configs, data)
        logger.debug("Final Datamodel:%s", data)
        logger.info("Finished successfully.")

    except Exception as error:  # noqa
        # Print useful information for reporting
        logger.error("================ An error occured! ============")
        logger.error("Stacktrace:")
        logger.exception(error)
        logger.error("Datamodel on Error:%s", data)
        logger.error("keyhint Version: %s", __version__)
        logger.error(
            "If you like, submit an error report on %s/issues .", __repo__,
        )
        logger.error("If you do so, please include the information above.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
