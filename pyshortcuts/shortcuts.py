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
    keys = {}

    def __init__(self, wm_name, wm_class):
        self.logger = logging.getLogger(__name__)

        with open(self.data_path / "index.json") as f:
            self.apps_index = json.load(f)

        self.app = self._get_app(wm_class)
        self.keys = self._get_shortcuts(wm_name)

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

    def _get_shortcuts(self, wm_name):
        with open(self.data_path / self.app["json"]) as f:
            self.app_shortcuts = json.load(f)

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
