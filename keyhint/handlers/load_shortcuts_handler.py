"""Handler responsible for attaching screenshot(s) to session data."""
# Standard
import json
import os
import subprocess
import re

# Own
from ..data_model import ShortCutsData
from .abstract_handler import AbstractHandler


class LoadShortcutsHandler(AbstractHandler):
    def handle(self, request: ShortCutsData) -> ShortCutsData:
        """Take multimon screenshots and add those images to session data.

        Arguments:
            AbstractHandler {class} -- self
            request {NormcapData} -- NormCap's session data

        Returns:
            NormcapData -- Enriched NormCap's session data
        """
        self._logger.debug("Loading index data...")

        app = self._get_app(request)
        request.app_name = app["name"]
        request.app_wm_class_regex = app["wm_class"]

        with open(request.data_path / app["json"]) as f:
            app_shortcuts = json.load(f)

        context = self._get_context_shortcuts(request.wm_name, app_shortcuts)
        request.shortcuts = context["shortcuts"]
        request.context_wm_name_regex = context["wm_name"]
        request.context_name = context["context"]

        if self._next_handler:
            return super().handle(request)
        else:
            return request

    def _get_app(self, request):
        for app in request.index:
            self._logger.debug(
                "Applying regex '%s' for '%s'...", app["wm_class"], app["name"]
            )
            if re.search(app["wm_class"], request.wm_class):
                self._logger.debug("'%s' is open!", app["name"])
                return app
            else:
                self._logger.debug("This application is not open!")
        return None

    def _get_context_shortcuts(self, wm_name, app_shortcuts):
        for context in app_shortcuts:
            self._logger.debug(
                "Applying regex '%s' for '%s'...",
                context["wm_name"],
                context["context"],
            )
            if re.search(context["wm_name"], wm_name):
                self._logger.debug("'%s' is active!", context["context"])
                return context
            else:
                self._logger.debug("This context is not active!")
        return None
