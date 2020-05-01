## Standard
import logging
import re
import json
from pathlib import Path

# Extra


class Shortcuts:
    data_path = Path(__file__).parent.parent / "data"
    apps_index = {}
    app = {}
    app_shortcuts = []
    context_shortcuts = {}

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        with open(self.data_path / "index.json") as f:
            self.apps_index = json.load(f)

    def get_shortcuts(self, wm_name, wm_class):
        self.app = self._get_app(wm_class)
        self.app_shortcuts = self._get_app_shortcuts()
        self.app_context_shortcuts = self._get_context_shortcuts(wm_name)
        return self.app_context_shortcuts

    def _get_app(self, wm_class):
        for app in self.apps_index:
            self.logger.debug(
                "Applying regex '%s' for '%s'...", app["wm_class"], app["name"]
            )
            if re.search(app["wm_class"], wm_class):
                self.logger.debug("'%s' is open!", app["name"])
                return app
            else:
                self.logger.debug("This application is not open!")
        return None

    def _get_app_shortcuts(self):
        with open(self.data_path / self.app["json"]) as f:
            return json.load(f)

    def _get_context_shortcuts(self, wm_name):
        for context in self.app_shortcuts:
            self.logger.debug(
                "Applying regex '%s' for '%s'...",
                context["wm_name"],
                context["context"],
            )
            if re.search(context["wm_name"], wm_name):
                self.logger.debug("'%s' is active!", context["context"])
                return context
            else:
                self.logger.debug("This context is not active!")
        return None
