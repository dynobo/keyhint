"""
Cheatsheat for keyboard shortcuts & commands.

Main entry point that get's executed on start.
"""

import importlib.resources
import logging
import sys
from typing import Optional

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gio, GLib, Gtk  # pylint: disable=wrong-import-position

from keyhint.window import WindowHandler  # pylint: disable=wrong-import-position

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

    window: Optional[Gtk.ApplicationWindow] = None
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
        """Create and activate a window with self as application the window belongs to."""
        Gtk.Application.do_activate(self, *args, **kwargs)

        if not self.window:
            builder = Gtk.Builder()
            builder.set_application(self)
            with importlib.resources.path(
                "keyhint.resources", "ApplicationWindow.glade"
            ) as ui_path:
                ui_file = str(ui_path.absolute())
            builder.add_from_file(ui_file)
            builder.connect_signals(WindowHandler(builder, self.options))

            self.window = builder.get_object("keyhint_app_window")
            self.window.set_application(self)
            self.window.show_all()

        self.window.present()

    def do_command_line(self, *args, **kwargs):
        """Store command line options in class attribute for later usage."""
        Gtk.Application.do_command_line(self, *args, **kwargs)

        self.options = args[0].get_options_dict().end().unpack()

        if "verbose" in self.options:
            logging.getLogger().setLevel("DEBUG")
            logger.info("Log level is set to 'DEBUG'")

        logger.debug(f"CLI Options: {self.options}")
        self.activate()
        return 0


def main():
    """Start application on script call."""
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
