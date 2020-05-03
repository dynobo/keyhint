"""Handler responsible for attaching screenshot(s) to session data."""
# Standard
import json
import os
import subprocess
import re

# Own
from ..data_model import HintsData
from .abstract_handler import AbstractHandler


class LoadHintsHandler(AbstractHandler):
    def handle(self, data: HintsData) -> HintsData:
        """Take multimon screenshots and add those images to session data.

        Arguments:
            AbstractHandler {class} -- self
            data {NormcapData} -- NormCap's session data

        Returns:
            NormcapData -- Enriched NormCap's session data
        """
        self._logger.debug("Loading index data...")

        app = self._get_app(data)
        if app:
            data.app_name = app["name"]
            data.app_wm_class_regex = app["wm_class"]

            with open(data.data_path / app["json"]) as f:
                app_shortcuts = json.load(f)

            context = self._get_context_shortcuts(data.wm_name, app_shortcuts)
            data.shortcuts = context["shortcuts"]
            data.context_wm_name_regex = context["wm_name"]
            data.context_name = context["context"]

        if self._next_handler:
            return super().handle(data)
        else:
            return data

    def _get_app(self, data):
        for app in data.index:
            self._logger.debug(
                "Applying regex '%s' for '%s'...", app["wm_class"], app["name"]
            )
            if re.search(app["wm_class"], data.wm_class):
                self._logger.info("Application '%s' is active...", app["name"])
                return app
            else:
                self._logger.debug("This application is not open...")
        return None

    def _get_context_shortcuts(self, wm_name, app_shortcuts):
        for context in app_shortcuts:
            self._logger.debug(
                "Applying regex '%s' for '%s'...",
                context["wm_name"],
                context["context"],
            )
            if re.search(context["wm_name"], wm_name):
                self._logger.info("Context '%s' is active...", context["context"])
                return context
            else:
                self._logger.debug("This context is not active!")
        return None
