import importlib.resources
import logging
import re

from gi.repository import Gdk, GLib, Gtk

import keyhint.utils

logger = logging.getLogger(__name__)


class WindowHandler:
    _section_title_height = None
    _row_height = None

    def __init__(self, builder, options):
        self._options = options

        self._hints = keyhint.utils.load_hints()

        self._window = builder.get_object("keyhint_app_window")
        self._header_bar = builder.get_object("header_bar")
        self._select_hints_combo = builder.get_object("select_hints_combo")
        self._hints_box = builder.get_object("hints_container_box")

        logger.debug(f"Loaded {len(self._hints)} hints.")

    def get_screen_dims(self):
        screen = self._window.get_screen()
        display = screen.get_display()
        monitor = display.get_monitor_at_window(screen.get_root_window())
        workarea = monitor.get_workarea()
        logger.debug(f"Width: {workarea.width}, Height: {workarea.height}")
        return workarea.width, workarea.height

    def get_hints_box_dims(self):
        size = self._hints_box.size_request()
        return size.width, size.height

    def get_hint_ids_titles(self):
        return [(k["id"], k["title"]) for k in self._hints]

    def get_hints_by_id(self, hint_id):
        for h in self._hints:
            if h["id"] == hint_id:
                return h
        return None

    def get_appropriate_hint_id(self):
        # If hint-id was provided by option, use that one:
        if "hint" in self._options:
            hint_id = self._options["hint"]
            logger.debug(f"Using provided hint-id: {hint_id}")
            return hint_id

        # Otherwise select hints by active window
        (
            self.active_wm_class,
            self.active_window_title,
        ) = keyhint.utils.detect_active_window()

        matching_hints = [
            h
            for h in self._hints
            if re.search(
                h["match"]["regex_process"], self.active_wm_class, re.IGNORECASE
            )
            and re.search(
                h["match"]["regex_title"], self.active_window_title, re.IGNORECASE
            )
        ]

        hint_id = None
        if matching_hints:
            hint_id = matching_hints[0]["id"]
            logger.debug(f"Found matching hints '{hint_id}'.")
        else:
            logger.debug("No matching hints found.")
            if "default-hint" in self._options:
                hint_id = self._options["default-hint"]
                logger.debug(f"Using provided default hint-id: {hint_id}")
                return hint_id

        return hint_id

    def get_row_heights(self):
        grid = self.create_column_grid()
        section_title = self.create_section_title("dummy")
        grid.attach(section_title, left=1, top=0, width=1, height=1)

        bindings_box = self.create_bindings("Ctrl + A")
        label = self.create_label("testlabel")
        grid.attach(bindings_box, left=0, top=1, width=1, height=1)
        grid.attach(label, left=1, top=1, width=1, height=1)
        # self._hints_box.pack_start(grid, False, False, 0)
        # self._window.show_all()
        grid.show_all()

        spacing = grid.get_row_spacing()

        title_height = section_title.size_request().height + spacing
        row_height = bindings_box.size_request().height + spacing

        logger.debug(f"Title height: {title_height}, Row height: {row_height}")
        return title_height, row_height

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

    def clear_hints_container(self):
        for child in self._hints_box.get_children():
            self._hints_box.remove(child)

    def populate_select_hints_combo(self):
        for hint_id, title in self.get_hint_ids_titles():
            self._select_hints_combo.append(id=hint_id, text=title)

    def create_column_grid(self):
        column_grid = Gtk.Grid()
        column_grid.set_column_spacing(20)
        column_grid.set_row_spacing(10)
        column_grid.set_column_homogeneous(False),
        column_grid.set_vexpand(False)
        column_grid.set_valign(Gtk.Align.START)
        return column_grid

    def distribute_hints_in_columns(self, keyhints):
        _, screen_height = self.get_screen_dims()
        max_column_height = screen_height // 1.3

        if (not self._section_title_height) or (not self._row_height):
            self._section_title_height, self._row_height = self.get_row_heights()

        hint_columns = []
        current_column = {}
        column_height = 0

        for section, hints in keyhints["hints"].items():
            section_height = self._section_title_height + self._row_height * len(hints)
            if column_height + section_height < max_column_height:
                current_column[section] = hints
                column_height += section_height
            else:
                hint_columns.append(current_column)
                current_column = {}
                current_column[section] = hints
                column_height = section_height

        if len(current_column) > 0:
            hint_columns.append(current_column)

        return hint_columns

    def populate_hints_container(self):
        hint_id = self._select_hints_combo.get_active_id()
        keyhints = self.get_hints_by_id(hint_id)
        hint_columns = self.distribute_hints_in_columns(keyhints)

        for column in hint_columns:
            grid = self.create_column_grid()
            idx = 0
            for section, shortcuts in column.items():
                section_title = self.create_section_title(section)
                grid.attach(section_title, left=1, top=idx, width=1, height=1)
                idx += 1
                for bindings in shortcuts:
                    bindings_box = self.create_bindings(bindings)
                    label = self.create_label(shortcuts[bindings])
                    grid.attach(bindings_box, left=0, top=idx, width=1, height=1)
                    grid.attach(label, left=1, top=idx, width=1, height=1)
                    idx += 1

            self._hints_box.pack_start(grid, False, False, 0)

        self._hints_box.show_all()

    def adjust_window_dimensions(self):
        screen_width, screen_height = self.get_screen_dims()
        hints_box_width, hints_box_height = self.get_hints_box_dims()
        header_height = self._header_bar.size_request().height

        target_height = min(hints_box_height + header_height, screen_height // 1.1)
        target_width = min(hints_box_width + 80, screen_width // 1.1)

        self._window.resize(target_width, target_height)
        self._window.move(0, 0)

    def on_select_hints_combo_changed(self, combo):
        self.clear_hints_container()
        self.populate_hints_container()
        self.adjust_window_dimensions()

    def on_window_destroy(self, *args):
        print("destroy")
        Gtk.main_quit()

    def on_window_realize(self, *args):
        self.create_css()
        self.populate_select_hints_combo()
        hint_id = self.get_appropriate_hint_id()
        if hint_id is not None:
            self._select_hints_combo.set_active_id(hint_id)
        else:
            self._select_hints_combo.set_active(0)
        self._header_bar.set_subtitle(
            f"(wm_class: {self.active_wm_class}, title: {self.active_window_title})"
        )

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
