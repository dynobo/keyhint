import importlib.resources
import logging
import re
import sys
import traceback

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gdk, Gio, GLib, Gtk

from keyhint.utils import (
    get_active_window_info_wayland,
    get_active_window_info_x,
    is_using_wayland,
    load_hints,
    replace_keys,
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%H:%M:%S",
    level="WARNING",
)
logger = logging.getLogger(__name__)


class AppWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set window properties
        self.set_default_size(int(1280), int(720))
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_modal(True)
        self.add_css()
        self.padding = 20
        self.spacing = 30

        # Attach key listener (for ESC)
        self.connect("key-release-event", self.on_key_release)

        # Create control elements
        self.select_hints_combo = self.create_select_hints_combo()
        self.header_bar = self.create_headerbar()
        self.set_titlebar(self.header_bar)

        # Render headerbar to determine size
        self.header_bar.show()

        hint_id = self.get_application().get_appropriate_hint_id()
        if hint_id is not None:
            self.select_hints_combo.set_active_id(hint_id)
        else:
            self.select_hints_combo.set_active(0)

        self.show_all()

    def on_key_release(self, widget, event, data=None):
        if event.keyval == Gdk.KEY_Escape:
            self.get_application().quit()

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
            label.set_markup(f"{GLib.markup_escape_text(key)}")
            label_context = label.get_style_context()
            label_context.add_class("key")
            if "🠇" in key:
                label_context.add_class("symbol")
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
        label_context = label.get_style_context()
        label_context.add_class("section-title")
        return label

    def get_section(self, section: str, shortcuts: dict):
        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True),
        grid.set_vexpand(False)
        grid.set_valign(Gtk.Align.START)

        section_title = self.get_section_title(section)
        grid.attach(section_title, left=1, top=0, width=1, height=1)

        for idx, bindings in enumerate(shortcuts):
            bindings_box = self.get_bindings(bindings)
            label = self.get_label(shortcuts[bindings])
            grid.attach(bindings_box, left=0, top=idx + 1, width=1, height=1)
            grid.attach(label, left=1, top=idx + 1, width=1, height=1)
        return grid

    def create_select_hints_combo(self):
        hints_store = Gtk.ListStore(str, str)
        for hint_id, title in self.get_application().get_hint_ids_titles():
            hints_store.append([hint_id, title])

        combo = Gtk.ComboBox.new_with_model_and_entry(hints_store)
        combo.connect("changed", self.on_title_combo_changed)
        combo.set_id_column(0)
        combo.set_entry_text_column(1)
        return combo

    def create_hints_box(self, hint_id):
        # Retrieve keyhints for currently selected sapplication
        keyhints = self.get_application().get_hints_by_id(hint_id)

        # Parent container box to be filled with columns
        hints_box = Gtk.Box()
        hints_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        hints_box.set_margin_top(self.padding)
        hints_box.set_margin_left(self.padding)
        hints_box.set_margin_right(self.padding)

        max_column_height = (
            self.get_default_size().height - self.header_bar.size_request().height
        )

        column_box = Gtk.Box()
        column_box.set_orientation(Gtk.Orientation.VERTICAL)
        column_height = 0
        for section, hints in keyhints["hints"].items():
            section_box = self.get_section(section, hints)
            section_box.show_all()
            section_height = section_box.size_request().height

            # Start new column, too high
            if column_height + section_height > max_column_height:
                hints_box.pack_start(column_box, False, False, 0)
                column_box = Gtk.Box()
                column_box.set_orientation(Gtk.Orientation.VERTICAL)
                section_box.set_margin_bottom(self.spacing)

            # Don't draw margin bottom, if it would exceed column height
            if column_height + section_height + self.spacing < max_column_height:
                section_box.set_margin_bottom(self.spacing)

            column_box.pack_start(section_box, False, False, 0)
            column_box.show_all()
            column_height = column_box.size_request().height

        hints_box.pack_start(column_box, False, False, 0)

        return hints_box

    def create_headerbar(self):
        header_bar = Gtk.HeaderBar(title="Keyhint")
        header_bar.props.show_close_button = True

        header_bar.pack_start(self.select_hints_combo)

        MENU_XML = importlib.resources.read_text("keyhint.resources", "menu.xml")
        builder = Gtk.Builder.new_from_string(MENU_XML, -1)
        menu = builder.get_object("app-menu")
        button = Gtk.MenuButton(menu_model=menu)
        header_bar.pack_end(button)

        return header_bar

    def get_selected_hint_id(self):
        hint_id = None
        selected_hints = self.select_hints_combo.get_active_iter()
        if selected_hints is not None:
            model = self.select_hints_combo.get_model()
            hint_id = model[selected_hints][0]
            logger.debug(f"Hint selected in dropdown: '{hint_id}'")
        return hint_id

    def update_hints_scrolled(self):
        hint_id = self.get_selected_hint_id()

        if hasattr(self, "hints_scrolled"):
            self.remove(self.hints_scrolled)

        self.hints_scrolled = Gtk.ScrolledWindow()
        self.hints_scrolled.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )

        hints_box = self.create_hints_box(hint_id)
        self.hints_scrolled.add(hints_box)

        self.add(self.hints_scrolled)
        self.show_all()

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

    def detect_active_window(self):
        self.wm_class = self.window_title = None

        try:
            if is_using_wayland():
                self.wm_class, self.window_title = get_active_window_info_wayland()
            else:
                self.wm_class, self.window_title = get_active_window_info_x()
        except Exception:
            logger.error("Traceback:\n" + traceback.format_tb())
            logger.error(
                "Couldn't detect active application window."
                "KeyHint currently should support Wayland and X. If you are using one "
                "of those and see this error, please create and issue incl. the tracebackk "
                "above on https://github.com/dynobo/keyhint/issues."
            )

        logger.debug(
            f"Detected wm_class: '{self.wm_class}'. Detected window_title: '{self.window_title}'."
        )
        return self.wm_class, self.window_title

    def get_appropriate_hint_id(self):
        wm_class, window_title = self.detect_active_window()
        matching_hints = [
            h
            for h in self.hints
            if re.search(h["match"]["regex_process"], wm_class, re.IGNORECASE)
            and re.search(h["match"]["regex_title"], window_title, re.IGNORECASE)
        ]

        hint_id = None
        if matching_hints:
            hint_id = matching_hints[0]["id"]
            logger.debug(f"Found matching hints '{hint_id}'.")
        else:
            logger.debug("No matching hints found.")

        return hint_id

    def do_activate(self):
        # We only allow a single window and raise any existing ones
        logger.debug(f"Loaded {len(self.hints)} hints.")
        if not self.window:
            # Windows are associated with the application
            # when the last one is closed the application shuts down
            self.window = AppWindow(application=self, title="Main Window")

        self.window.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()

        logger.debug("CLI Options: " + str(options))
        if "verbose" in options:
            logger.setLevel("DEBUG")
            logger.info("Log level is set to 'DEBUG'")

        self.activate()
        return 0

    def get_hint_ids_titles(self):
        hints = self.hints
        return [(k["id"], k["title"]) for k in hints]

    def get_hints_by_id(self, hint_id):
        hints = self.hints
        for keyhint in hints:
            if keyhint["id"] == hint_id:
                return keyhint
        return None

    def on_about(self, action, param):
        about = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about.set_program_name("KeyHint")
        about.set_version("0.1")
        about.set_authors(["dynobo"])
        about.set_copyright(
            "\nDETECTED WINDOW:\n"
            f"wm class: '{self.wm_class}'\n"
            f"window title: '{self.window_title}'"
        )
        about.set_comments(
            "Display context-sensitive keyboard shortcuts\nor other hints on Linux"
        )
        about.set_website("https://github.com/dynobo/keyhint")
        about.present()

    def on_quit(self, action, param):
        self.quit()


def main():
    # app_process, app_title = get_active_window_info_x()
    # logger.info(app_process, app_title)
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
