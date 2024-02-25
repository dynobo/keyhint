import os
from configparser import ConfigParser
from pathlib import Path

if xdg_conf := os.getenv("XDG_CONFIG_HOME", None):
    CONFIG_PATH = Path(xdg_conf) / "keyhint"
else:
    CONFIG_PATH = Path.home() / ".config" / "keyhint"
CONFIG_FILE = CONFIG_PATH / "keyhint.ini"


class WritingConfigParser(ConfigParser):
    def set_persistent(
        self, section: str, option: str, value: str | bool | int
    ) -> None:
        self.set(section, option, str(value))
        self.write(CONFIG_FILE.open("w"))


def load() -> WritingConfigParser:
    """Create the default settings file if it doesn't exist."""
    config = WritingConfigParser(
        defaults={
            "fullscreen": "True",
            "sort_by": "size",
            "orientation": "vertical",
            "default_cheatsheet": "keyhint",
        },
    )
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
    if not config.has_section("main"):
        config.add_section("main")
    return config
