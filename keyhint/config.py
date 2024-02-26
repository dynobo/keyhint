import logging
import os
from configparser import ConfigParser
from pathlib import Path

if xdg_conf := os.getenv("XDG_CONFIG_HOME", None):
    CONFIG_PATH = Path(xdg_conf) / "keyhint"
else:
    CONFIG_PATH = Path.home() / ".config" / "keyhint"
CONFIG_FILE = CONFIG_PATH / "keyhint.ini"

logger = logging.getLogger("keyhint")


class WritingConfigParser(ConfigParser):
    def set_persistent(
        self, section: str, option: str, value: str | bool | int
    ) -> None:
        if self.get(section, option) == str(value):
            return
        self.set(section, option, str(value))
        self.write(CONFIG_FILE.open("w"))


def load() -> WritingConfigParser:
    """Create the default settings file if it doesn't exist."""
    config = WritingConfigParser(
        defaults={
            "fullscreen": "True",
            "sort_by": "size",
            "orientation": "vertical",
            "fallback_cheatsheet": "keyhint",
            "zoom": "100",
        },
    )
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
        logger.debug("Loaded config from %s.", CONFIG_FILE)
    if not config.has_section("main"):
        config.add_section("main")
        logger.debug("Created missing 'main' section.")
    return config


if __name__ == "__main__":
    load()