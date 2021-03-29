import importlib
import logging
import re

from gi.repository import Gdk, GLib, Gtk

import keyhint.utils

logger = logging.getLogger(__name__)


class WindowHandler:
    def __init__(self, builder, options):
        self.builder = builder
        self.options = options
        self.hints = keyhint.utils.load_hints()
        logger.debug(f"Loaded {len(self.hints)} hints.")

    def get_hint_ids_titles(self):
        return [(k["id"], k["title"]) for k in self.hints]

    def get_hints_by_id(self, hint_id):
        for h in self.hints:
            if h["id"] == hint_id:
                return h
        return None

    def get_selected_hint_id(self):
        hint_id = None
        select_hints_combo = self.builder.get_object("select_hints_combo")
        selected_hints = select_hints_combo.get_active_iter()
        if selected_hints is not None:
            model = select_hints_combo.get_model()
            hint_id = model[selected_hints][0]
            logger.debug(f"Hint selected in dropdown: '{hint_id}'")
        return hint_id

    def get_appropriate_hint_id(self):
        # If hint-id was provided by option, use that one:
        if "hint" in self.options:
            hint_id = self.options["hint"]
            logger.debug(f"Using provided hint-id: {hint_id}")
            return hint_id

        # Otherwise select hints by active window
        wm_class, window_title = keyhint.utils.detect_active_window()
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
            if "default-hint" in self.options:
                hint_id = self.options["default-hint"]
                logger.debug(f"Using provided default hint-id: {hint_id}")
                return hint_id

        return hint_id

    # GENERATE/MODIFY WIDGETS

    def create_css(self):
        css = importlib.resources.read_binary("keyhint.resources", "style.css")
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def create_label(self, text):
        label = Gtk.Label()
        label.set_text(text)
        label.set_xalign(0.0)
        return label

    def create_bindings(self, text):
        box = Gtk.Box()
        box.set_halign(Gtk.Align.END)
        if text.startswith("`"):
            keys = [text.replace("`", "")]
        else:
            keys = text.split()

        for key in keys:
            label = Gtk.Label()
            key = keyhint.utils.replace_keys(key.strip())
            label_context = label.get_style_context()
            if key in ["+", "/"]:
                label_context.add_class("separator")
            else:
                key = key.replace("\\/", "/")
                key = key.replace("\\+", "+")
                label_context.add_class("key")
            label.set_markup(f"{GLib.markup_escape_text(key)}")
            box.add(label)
        return box

    def create_section_title(self, text):
        label = Gtk.Label()
        label.set_markup(f"<b>{text}</b>")
        label.set_xalign(0.0)
        label_context = label.get_style_context()
        label_context.add_class("section-title")
        return label

    def create_section(self, section: str, shortcuts: dict):
        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True),
        grid.set_vexpand(False)
        grid.set_valign(Gtk.Align.START)

        section_title = self.create_section_title(section)
        grid.attach(section_title, left=1, top=0, width=1, height=1)

        for idx, bindings in enumerate(shortcuts):
            bindings_box = self.create_bindings(bindings)
            label = self.create_label(shortcuts[bindings])
            grid.attach(bindings_box, left=0, top=idx + 1, width=1, height=1)
            grid.attach(label, left=1, top=idx + 1, width=1, height=1)
        return grid

    def clear_hints_container(self):
        hints_box = self.builder.get_object("hints_container_box")
        for child in hints_box.get_children():
            hints_box.remove(child)

    def populate_select_hints_combo(self):
        hints_liststore = self.builder.get_object("hints_liststore")
        for hint_id, title in self.get_hint_ids_titles():
            hints_liststore.append([hint_id, title])

    def populate_hints_container(self):
        hint_id = self.get_selected_hint_id()
        keyhints = self.get_hints_by_id(hint_id)
        max_column_height = 700  # self.window.get_default_size().height

        hints_box = self.builder.get_object("hints_container_box")
        column_box = Gtk.Box()
        column_box.set_orientation(Gtk.Orientation.VERTICAL)
        column_height = 0
        for section, hints in keyhints["hints"].items():
            section_box = self.create_section(section, hints)
            section_box.show_all()
            section_height = section_box.size_request().height

            # Start new column, too high
            if column_height + section_height > max_column_height:
                hints_box.pack_start(column_box, False, False, 0)
                column_box = Gtk.Box()
                column_box.set_orientation(Gtk.Orientation.VERTICAL)
                section_box.set_margin_bottom(10)

            # Don't draw margin bottom, if it would exceed column height
            if column_height + section_height + 10 < max_column_height:
                section_box.set_margin_bottom(10)

            column_box.pack_start(section_box, False, False, 0)
            column_box.show_all()
            column_height = column_box.size_request().height

        hints_box.pack_start(column_box, False, False, 0)

    # EVENT HANDLERS

    def on_select_hints_combo_changed(self, combo):
        self.clear_hints_container()
        self.populate_hints_container()

    def on_window_destroy(self, *args):
        print("destroy")
        Gtk.main_quit()

    def on_window_realize(self, *args):
        self.create_css()
        self.populate_select_hints_combo()
        hint_id = self.get_appropriate_hint_id()
        if hint_id is not None:
            self.builder.get_object("select_hints_combo").set_active_id(hint_id)
        else:
            self.builder.get_object("select_hints_combo").set_active(1)

    def onButtonPressed(self, button):
        print("button")
        print("Hello World!")

    def on_about(self, action, param):
        about = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about.set_program_name("KeyHint")
        about.set_version("0.1")
        about.set_authors(["dynobo"])
        about.set_copyright("MIT Licenced")
        about.set_comments(
            "Display context-sensitive keyboard shortcuts\nor other hints on Linux"
        )
        about.set_website("https://github.com/dynobo/keyhint")
        about.present()
