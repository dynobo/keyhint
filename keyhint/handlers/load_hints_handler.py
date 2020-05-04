"""Handler responsible for attaching screenshot(s) to session data."""

# Standard
import json
import re

# Own
from ..data_model import HintsData
from .. import helpers
from .abstract_handler import AbstractHandler


class LoadHintsHandler(AbstractHandler):
    """Reads information from application specific json file."""

    # Container for data object
    data: HintsData

    def handle(self, data: HintsData) -> HintsData:
        """Take multimon screenshots and add those images to session data.

        Arguments
            AbstractHandler {class} -- self
            data {NormcapData} -- NormCap's session data

        Returns
            NormcapData -- Enriched NormCap's session data

        """
        self._logger.debug("Loading index data...")
        self.data = data

        # Try to find active window in app index json
        app = self._get_app()

        # if found, update in data object
        if app:
            self.data.app_name = app["name"]
            self.data.app_wm_class_regex = app["wm_class"]

            with open(self.data.data_path / app["json"]) as file:
                app_hints = json.load(file)

            context = self._get_context_hints(self.data.wm_name, app_hints)
            if context:
                self.data.hints = context["hints"]
                self.data.context_wm_name_regex = context["wm_name"]
                self.data.context_name = context["context"]

        # replace missing data, in case app or context wasn't found
        self._replace_data_if_unkown()

        if self._next_handler:
            return super().handle(self.data)
        return self.data

    def _get_app(self) -> dict:
        """Identify active application by comparing wm_class to regex in index file."""
        for app in self.data.index:
            self._logger.debug(
                "Applying regex '%s' for '%s'...", app["wm_class"], app["name"]
            )
            if re.search(app["wm_class"], self.data.wm_class):
                self._logger.info("Application '%s' is active...", app["name"])
                return app
            self._logger.debug("This application is not open...")
        return {}

    def _get_context_hints(self, wm_name: str, app_hints: dict) -> dict:
        """Identify active context by comparing wm_name to regex in hints file."""
        for context in app_hints:
            self._logger.debug(
                "Applying regex '%s' for '%s'...",
                context["wm_name"],
                context["context"],
            )
            if re.search(context["wm_name"], wm_name):
                self._logger.info("Context '%s' is active...", context["context"])
                return context
            self._logger.debug("This context is not active!")
        return {}

    def _replace_data_if_unkown(self):
        """Replace missing hint information with useful message.

        If no hints are found, the app/context to display is replaced
        by a "Not Found" message and instead of hints, the window
        information is added.

        """
        if not self.data.app_name:
            self.data.app_name = "Application unknown!"

        if not self.data.hints:
            self.data.context_name = "no hints found"

            self.data.wm_name = helpers.remove_emojis(self.data.wm_name)

            self.data.hints = {
                "Properties of active Window": {
                    "wm_class": self.data.wm_class,
                    "wm_name": self.data.wm_name,
                },
            }
