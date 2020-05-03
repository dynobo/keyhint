"""Handler responsible for attaching screenshot(s) to session data."""
# Standard
import json
import os
import subprocess

# Own
from ..data_model import ShortCutsData
from .abstract_handler import AbstractHandler


class LoadIndexHandler(AbstractHandler):
    def handle(self, request: ShortCutsData) -> ShortCutsData:
        """Take multimon screenshots and add those images to session data.

        Arguments:
            AbstractHandler {class} -- self
            request {NormcapData} -- NormCap's session data

        Returns:
            NormcapData -- Enriched NormCap's session data
        """
        self._logger.debug("Loading index data...")

        # TODO: parametrize data_path
        p = request.data_path / "index.json"
        with open(request.data_path / "index.json") as f:
            request.index = json.load(f)

        if self._next_handler:
            return super().handle(request)
        else:
            return request
