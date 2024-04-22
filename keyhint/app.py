"""Cheatsheet for keyboard shortcuts & commands.

Main entry point that get's executed on start.
"""

import logging
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib  # noqa: E402

from keyhint.window import KeyhintWindow  # noqa: E402

logging.basicConfig(
    format="%(asctime)s - %(levelname)-7s - %(module)s.py:%(lineno)d - %(message)s",
    datefmt="%H:%M:%S",
    level="WARNING",
)
logger = logging.getLogger("keyhint")


class Application(Adw.Application):
    """Main application class.

    Handle command line options and display the window.

    Args:
        Gtk (Gtk.Application): Application Class
    """

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Initialize application with command line options."""
        kwargs.update(
            application_id="com.github.dynobo.keyhint",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        super().__init__(
            *args,
            **kwargs,
        )
        self.options: dict = {}

        self.add_main_option(
            "cheatsheet",
            ord("c"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Show cheatsheet with this ID on startup",
            "SHEET-ID",
        )
        self.add_main_option(
            "verbose",
            ord("v"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Verbose log output for debugging",
            None,
        )

    def do_activate(self, *_, **__) -> None:  # noqa: ANN002, ANN003
        """Create and activate a window."""
        window = KeyhintWindow(self.options)
        window.set_application(self)
        window.present()

    def do_command_line(self, cli: Gio.ApplicationCommandLine) -> int:
        """Store command line options in class attribute for later usage."""
        self.options = cli.get_options_dict().end().unpack()

        if "verbose" in self.options:
            logger.setLevel("DEBUG")
            logger.debug("CLI Options: %s", self.options)

        self.activate()
        return 0


def main() -> None:
    """Start application on script call."""
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
