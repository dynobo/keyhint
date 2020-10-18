"""Handler responsible for attaching screenshot(s) to session data."""

# Standard
import re

# Own
from ..data_model import HintsData
from .abstract_handler import AbstractHandler


class SelectHintsHandler(AbstractHandler):
    """Reads information from application specific json file."""

    # Container for data object
    data: HintsData

    def handle(self, data: HintsData) -> HintsData:
        """Take multimon screenshots and add those images to session data.

        Args:
            AbstractHandler (class): self
            data (HintsData): Central data object

        Returns
            HintsData: Central data object

        """
        self._logger.debug("Loading hints data...")

        # Try to find hints for current application in all hints
        data.hints = [
            h
            for h in data.hints
            if re.search(h["regex_process"], data.app_process, re.IGNORECASE)
            and re.search(h["regex_title"], data.app_title, re.IGNORECASE)
        ]

        if self._next_handler:
            return super().handle(data)
