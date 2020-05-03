# Standard
import logging

# Extra

# Own
from . import helpers
from .handlers.abstract_handler import AbstractHandler
from .handlers.detect_application_handler import DetectApplicationHandler
from .handlers.load_index_handler import LoadIndexHandler
from .handlers.load_hints_handler import LoadHintsHandler
from .handlers.show_hints_handler import ShowHintsHandler
from .data_model import HintsData

__author__ = "dynobo"
__email__ = "dynobo@mailbox.org"
__repo__ = "https://github.com/dynobo/keyhint"
__version__ = "0.1.0"


def client_code(handler: AbstractHandler, data: HintsData) -> HintsData:
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
    logger.info("Starting keyhint v%s ...", __version__)

    try:
        # Central data model
        data = HintsData()

        # Define handlers
        detect_application = DetectApplicationHandler()
        load_index = LoadIndexHandler()
        load_hints = LoadHintsHandler()
        show_hints = ShowHintsHandler()

        # Define chain of handlers
        detect_application.set_next(load_index).set_next(load_hints).set_next(
            show_hints
        )

        # Run chain of handlers
        data = client_code(detect_application, data)
        logger.debug("Final Datamodel:%s", data)

    except Exception as error:
        logger.error("================ An error occured! ============")
        logger.error("Stacktrace:")
        logger.exception(error)
        logger.error("Datamodel on Error:%s", data)
        logger.error("keyhint Version: %s", __version__)
        logger.error(
            "If you like, submit an error report on %s/issues .", __repo__,
        )
        logger.error("If you do so, please include the information above.")

    logger.info("Finished successfully.")
    return 0


if __name__ == "__main__":
    main()
