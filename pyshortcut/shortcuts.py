## Standard
import logging
import re
import json
from pathlib import Path

# Extra


class Shortcuts:
    data_path = Path(__file__).parent.parent / "data"
    index = {}
    app = {}
    shortcuts = []

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        with open(self.data_path / "index.json") as f:
            self.index = json.load(f)

    def set_application(self, window_title):
        for app in self.index:
            self.logger.debug(
                "Applying regex '%s' for '%s'...", app["regex"], app["name"]
            )
            if re.search(app["regex"], window_title):
                self.logger.debug("'%s' is open!", app["name"])
                self.app = app
                self.load_app_shortcuts()
            else:
                self.logger.debug("This application is not open!")

    def load_app_shortcuts(self):
        with open(self.data_path / self.app["json"]) as f:
            self.shortcuts = json.load(f)
            print(self.shortcuts)
