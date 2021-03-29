import importlib.resources
import logging
import sys

import gi

from keyhint.handler import WindowHandler

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gio, GLib, Gtk  # noqa

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%H:%M:%S",
    level="WARNING",
)
logger = logging.getLogger(__name__)
# TODO: Store settings:
# https://docs.python.org/3/library/configparser.html
# https://marianochavero.wordpress.com/2012/04/03/short-example-of-gsettings-bindings-in-python/
# https://www.micahcarrick.com/gsettings-python-gnome-3.htm


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="org.example.myapp",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs,
        )
        self.window = None

        self.add_main_option(
            "verbose",
            ord("v"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Verbose log output for debugging",
            None,
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

    def do_startup(self):
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

    def do_activate(self):
        if not self.window:
            builder = Gtk.Builder()
            builder.add_from_file("keyhint/resources/ApplicationWindow.glade")
            builder.connect_signals(WindowHandler(builder, self.options))

            self.window = builder.get_object("application_window")
            self.window.set_application(self)
            self.window.show_all()

        self.window.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        self.options = options.end().unpack()

        if "verbose" in self.options:
            logging.getLogger().setLevel("DEBUG")
            logger.info("Log level is set to 'DEBUG'")

        logger.debug("CLI Options: " + str(self.options))
        self.activate()
        return 0

    def on_quit(self, action, param):
        self.quit()


def main():
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
