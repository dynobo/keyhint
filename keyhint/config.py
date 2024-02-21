from configparser import ConfigParser

from keyhint.utils import get_users_config_path

CONFIG_FILE = get_users_config_path() / "keyhint.ini"


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
