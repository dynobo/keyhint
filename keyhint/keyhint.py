import sys
import logging
import importlib.resources

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gio, Gtk, Gdk

from keyhint.utils import load_hints, replace_keys

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%H:%M:%S",
    level="WARNING",
)
logger = logging.getLogger(__name__)


class AppWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.get_application()
        self.select_hints_combo = self.create_select_hints_combo()
        self.select_hints_combo.set_active(0)
        self.header_bar = self.create_headerbar()

        self.set_titlebar(self.header_bar)
        self.set_default_size(int(1280), int(720))
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_modal(True)

        self.add_css()
        self.update_hints_scrolled()
        self.show_all()

    def add_css(self):
        css = importlib.resources.read_binary("keyhint.resources", "style.css")
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def get_label(self, text):
        label = Gtk.Label()
        label.set_text(text)
        label.set_xalign(0.0)
        return label

    def get_plus(self):
        label = Gtk.Label()
        label.set_markup(" + ")
        label_context = label.get_style_context()
        label_context.add_class("plus")
        return label

    def get_bindings(self, text):
        box = Gtk.Box()
        box.set_halign(Gtk.Align.END)
        for key in text.split("+"):
            label = Gtk.Label()
            key = replace_keys(key.strip())
            label.set_markup(f"{key}")
            label_context = label.get_style_context()
            label_context.add_class("key")
            box.add(label)
            plus = self.get_plus()
            box.add(plus)
        last = box.get_children()[-1]
        last.destroy()
        return box

    def get_section_title(self, text):
        label = Gtk.Label()
        label.set_markup(f"<b>{text}</b>")
        label.set_xalign(0.0)
        return label

    def get_section(self, section: str, shortcuts: dict):
        grid = Gtk.Grid()
        grid.set_column_spacing(30)
        grid.set_row_spacing(10)
        grid.set_margin_bottom(30)
        grid.set_column_homogeneous(True),

        section_title = self.get_section_title(section)
        grid.attach(section_title, left=1, top=0, width=1, height=1)

        for idx, bindings in enumerate(shortcuts):
            bindings_box = self.get_bindings(bindings)
            label = self.get_label(shortcuts[bindings])
            grid.attach(bindings_box, left=0, top=idx + 1, width=1, height=1)
            grid.attach(label, left=1, top=idx + 1, width=1, height=1)
        return grid

    def create_select_hints_combo(self):
        combo = Gtk.ComboBoxText()
        combo.set_entry_text_column(0)
        for title in self.get_application().get_hints_titles():
            combo.append_text(title)
        combo.connect("changed", self.on_title_combo_changed)
        return combo

    def create_flowbox(self, keyhints):
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(30)
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        for section, hints in keyhints["hints"].items():
            sectionGrid = self.get_section(section, hints)
            flowbox.add(sectionGrid)
        return flowbox

    def create_headerbar(self):
        header_bar = Gtk.HeaderBar(title="Keyhint")
        header_bar.props.show_close_button = True
        header_bar.pack_end(self.select_hints_combo)
        return header_bar

    def update_hints_scrolled(self):
        selected_hints = self.select_hints_combo.get_active_text()
        if hasattr(self, "hints_scrolled"):
            self.remove(self.hints_scrolled)

        self.hints_scrolled = Gtk.ScrolledWindow()
        self.hints_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        flowbox = self.create_flowbox(
            self.get_application().get_hints_by_title(selected_hints)
        )
        self.hints_scrolled.add(flowbox)

        self.add(self.hints_scrolled)
        self.hints_scrolled.show_all()

    def on_title_combo_changed(self, combo):
        self.update_hints_scrolled()


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
        # TODO
        self.add_main_option(
            "hints",
            ord("h"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Command line test",
            None,
        )

        self.hints = load_hints()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

        MENU_XML = importlib.resources.read_text("keyhint.resources", "menu.xml")
        builder = Gtk.Builder.new_from_string(MENU_XML, -1)

        self.set_app_menu(builder.get_object("app-menu"))

    def do_activate(self):
        # We only allow a single window and raise any existing ones
        if not self.window:
            # Windows are associated with the application
            # when the last one is closed the application shuts down
            self.window = AppWindow(application=self, title="Main Window")

        self.window.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()

        logger.warning(options)
        if "verbose" in options:
            logger.setLevel("DEBUG")
            logger.info("Log level is set to 'DEBUG'")

        self.activate()
        return 0

    def get_hints_titles(self):
        hints = self.hints
        return [k["title"] for k in hints]

    def get_hints_by_title(self, title):
        hints = self.hints
        for keyhint in hints:
            if keyhint["title"] == title:
                return keyhint
        return None

    def on_about(self, action, param):
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.present()

    def on_quit(self, action, param):
        self.quit()


def main():
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    main()