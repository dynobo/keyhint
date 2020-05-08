"""Top level logic of keyhint. Entry point for module."""

# Standard
import logging

# Own
from . import helpers
from .handlers.abstract_handler import AbstractHandler
from .handlers.detect_application_handler import DetectApplicationHandler
from .handlers.load_hints_handler import LoadHintsHandler
from .handlers.show_hints_handler import ShowHintsHandler
from .data_model import HintsData

# Basic information, e.g used in setup.py or in error report
__author__ = "dynobo"
__email__ = "dynobo@mailbox.org"
__repo__ = "https://github.com/dynobo/keyhint"
__version__ = "0.1.0"


def client_code(handler: AbstractHandler, data: HintsData) -> HintsData:
    """Wrap Chain of Responsibility classes.

    Arguments
        handler {AbstractHandler} -- Most outer handler
        data {HintsData} -- keyhint's session data

    Returns
        HintsData -- Keyhint's session data processed by handler

    """
    data = handler.handle(data)
    return data


def main():
    """Orchestrates the sequence of execution from start to end."""
    logger = helpers.init_logging(__name__, logging.DEBUG, to_file=False)
    logger.info("Starting keyhint v%s ...", __version__)

    try:
        # Central data model
        data = HintsData()

        # Define handlers
        detect_application = DetectApplicationHandler()
        # load_index = LoadIndexHandler()
        load_hints = LoadHintsHandler()
        show_hints = ShowHintsHandler()

        # Define chain of handlers
        detect_application.set_next(load_hints).set_next(show_hints)

        # Run chain of handlers
        data = client_code(detect_application, data)
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


if __name__ == "__main__":
    main()
