# Standard
import logging

# Extra

# Own
from . import helpers

__author__ = "dynobo"
__email__ = "dynobo@mailbox.org"
__version__ = "0.1.0"

def main():
    logger = helpers.init_logging(__name__, logging.INFO, to_file=False)
    logger.info("Starting NormCap v%s ...", __version__)
    some_text = helpers.get_something()
    logger.info("Sample output: %s", some_text)
    return 0

if __name__ == "__main__":
    main()
