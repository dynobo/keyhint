"""Handler responsible for attaching screenshot(s) to session data."""

# Standard
import json

# Own
from ..data_model import HintsData
from .abstract_handler import AbstractHandler


class LoadIndexHandler(AbstractHandler):
    """Load app index from json into central data object."""

    def handle(self, data: HintsData) -> HintsData:
        """Take multimon screenshots and add those images to session data.

        Arguments
            AbstractHandler {class} -- self
            data {NormcapData} -- NormCap's session data

        Returns
            NormcapData -- Enriched NormCap's session data

        """
        self._logger.debug("Loading index data...")

        # TODO: parametrize data_path
        with open(data.data_path / "index.json") as file:
            data.index = json.load(file)

        if self._next_handler:
            return super().handle(data)
        return data
