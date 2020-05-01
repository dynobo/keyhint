# Standard
import logging

# Extra


def get_something():
    logger = logging.getLogger(__name__)
    logger.info("Logging from subroutine")
    return "Hello You!"


def init_logging(name: str, log_level: int, to_file: bool = False) -> logging.Logger:
    """Initialize Logger with formatting and desired level.

    Arguments:
        log_level {logging._Level} -- Desired loglevel
        to_file {bool} -- Log also to file on disk

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
