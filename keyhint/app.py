"""
Cheatsheat for keyboard shortcuts & commands.

Main entry point that get's executed on start.
"""

import logging
import sys

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, GLib, Gtk  # noqa: E402

from keyhint.window import KeyhintWindow  # noqa: E402

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%H:%M:%S",
    level="WARNING",
)
logger = logging.getLogger(__name__)


class Application(Gtk.Application):
    """Main application class.

    Handle command line options and display the window.

    Args:
        Gtk (Gtk.Application): Application Class
    """

    options: dict = {}

    def __init__(self, *args, **kwargs):
        """Initialize application with command line options."""
        super().__init__(
            *args,
            application_id="eu.dynobo.keyhint",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs,
        )
        self.add_main_option(
            "hint",
            ord("h"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Show hints by specified ID",
            "HINT-ID",
        )
        self.add_main_option(
            "default-hint",
            ord("d"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Hint to show in case no hints for active application were found",
            "HINT-ID",
        )
        self.add_main_option(
            "verbose",
            ord("v"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Verbose log output for debugging",
            None,
        )

    def do_activate(self, *args, **kwargs):
        """Create and activate a window."""
        window = KeyhintWindow(self.options)
        window.set_application(self)
        window.present()

    def do_command_line(self, *args, **kwargs):
        """Store command line options in class attribute for later usage."""
        self.options = args[0].get_options_dict().end().unpack()

        if "verbose" in self.options:
            logging.getLogger().setLevel("DEBUG")
            logger.debug(f"CLI Options: {self.options}")

        self.activate()
        return 0


def main():
    """Start application on script call."""
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
