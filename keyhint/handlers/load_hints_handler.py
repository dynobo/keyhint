"""Handler responsible for attaching screenshot(s) to session data."""

# Standard
import re
import yaml

# Own
from ..data_model import HintsData
from .. import helpers
from .abstract_handler import AbstractHandler


class LoadHintsHandler(AbstractHandler):
    """Reads information from application specific json file."""

    # Container for data object
    data: HintsData
    hints: dict
    app_hints: dict

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

        # Load hints for all applications from yaml file
        self.hints = self._load_yaml()

        # Try to find hints for current application in all hints
        self.app_hints = self._get_app_hints()

        # if found, update in data object
        if self.app_hints:
            self.data.app_name = self.app_hints["name"]
            self.data.app_wm_class_regex = self.app_hints["wm_class"]

            # and try to find app context
            context = self._get_app_context_hints()

            # If found, put all infos in data object
            if context:
                self.data.hints = context["hints"]
                self.data.context_wm_name_regex = context["wm_name_regex"]
                self.data.context_name = context["name"]

        # replace missing data, in case app or context wasn't found
        self._replace_data_if_unkown()

        if self._next_handler:
            return super().handle(self.data)
        return self.data

    def _load_yaml(self):
        data = {}
        with open(self.data.data_path / "hints.yaml") as file:
            try:
                data = yaml.safe_load(file)
            except yaml.YAMLError as exc:
                self._logger.error("Exception while loading hints.yaml!")
                self._logger.error(exc)
        return data

    def _get_app_hints(self) -> dict:
        """Identify active application by searching wm_class in all hints."""
        for app_hints in self.hints["applications"]:
            self._logger.debug(
                "Checking '%s' of '%s'...", app_hints["wm_class"], app_hints["name"],
            )
            if app_hints["wm_class"].lower() == self.data.wm_class.lower():
                self._logger.info("Application '%s' is active...", app_hints["name"])
                return app_hints
            self._logger.debug("This application is not open...")
        return {}

    def _get_app_context_hints(self) -> dict:
        """Identify active context by comparing wm_name to regex in hints file."""
        for context in self.app_hints["contexts"]:
            self._logger.debug(
                "Applying regex '%s' for '%s'...",
                context["wm_name_regex"],
                context["name"],
            )
            if re.search(context["wm_name_regex"], self.data.context_wm_name_regex):
                self._logger.info("Context '%s' is active...", context["name"])
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
