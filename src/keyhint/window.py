import logging
import re

from gi.repository import Gdk, GLib, Gtk

import keyhint.utils

logger = logging.getLogger(__name__)


class WindowHandler:
    _section_title_height = None
    _row_height = None
    _hints = keyhint.utils.load_hints()
    _about_dialog_open = False

    def __init__(self, builder, options):
        self._options = options

        self._about_dialog = builder.get_object("about_dialog")
        self._window = builder.get_object("keyhint_app_window")
        self._header_bar = builder.get_object("header_bar")
        self._select_hints_combo = builder.get_object("select_hints_combo")
        self._hints_box = builder.get_object("hints_container_box")
        self._about_dialog = builder.get_object("about_dialog")

        logger.debug(f"Loaded {len(self._hints)} hints.")

    def _get_screen_dims(self):
        screen = self._window.get_screen()
        display = screen.get_display()
        monitor = display.get_monitor_at_window(screen.get_root_window())
        workarea = monitor.get_workarea()
        return workarea.width, workarea.height

    def _get_hints_box_dims(self):
        size = self._hints_box.size_request()
        return size.width, size.height

    def _get_hint_ids_titles(self):
        return [(k["id"], k["title"]) for k in self._hints]

    def _get_hints_by_id(self, hint_id):
        for h in self._hints:
            if h["id"] == hint_id:
                return h
        return None

    def _get_hint_id_by_active_window(self):
        self._wm_class, self._window_title = keyhint.utils.detect_active_window()

        matching_hints = [
            h
            for h in self._hints
            if re.search(h["match"]["regex_process"], self._wm_class, re.IGNORECASE)
            and re.search(h["match"]["regex_title"], self._window_title, re.IGNORECASE)
        ]

        if matching_hints:
            hint_id = matching_hints[0]["id"]
        else:
            hint_id = None

        return hint_id

    def _get_appropriate_hint_id(self):
        hint_id = None

        # If hint-id was provided by option, use that one:
        if "hint" in self._options:
            hint_id = self._options["hint"]
            logger.debug(f"Using provided hint-id: {hint_id}")

        # Else try to find hints for active window
        if not hint_id:
            hint_id = self._get_hint_id_by_active_window()
            logger.debug(f"Found matching hints '{hint_id}'.")

        # First fallback to cli provided default
        if (not hint_id) and ("default-hint" in self._options):
            hint_id = self._options["default-hint"]
            logger.debug(f"Using provided default hint-id: {hint_id}")

        # Last fallback to first entry in list
        if not hint_id:
            model = self._select_hints_combo.get_model()
            hint_id = model.get_value(model.get_iter_first(), 1)
            logger.debug("No matching hints found. Using first hint in list.")

        return hint_id

    def _get_row_heights(self):
        grid = self._create_column_grid()
        spacing = grid.get_row_spacing()

        section_title = self._create_section_title("dummy")
        grid.attach(section_title, left=1, top=0, width=1, height=1)

        bindings_box = self._create_bindings("Ctrl + A")
        label = self._create_label("testlabel")
        grid.attach(bindings_box, left=0, top=1, width=1, height=1)
        grid.attach(label, left=1, top=1, width=1, height=1)

        grid.show_all()

        title_height = section_title.size_request().height + spacing
        row_height = bindings_box.size_request().height + spacing

        logger.debug(f"Title height: {title_height}, Row height: {row_height}")
        return title_height, row_height

    def _distribute_hints_in_columns(self, keyhints):
        _, screen_height = self._get_screen_dims()
        max_column_height = screen_height // 1.3

        if (not self._section_title_height) or (not self._row_height):
            self._section_title_height, self._row_height = self._get_row_heights()

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

    # GENERATE/MODIFY WIDGETS

    def _create_column_grid(self):
        column_grid = Gtk.Grid()
        column_grid.set_column_spacing(20)
        column_grid.set_row_spacing(10)
        return column_grid

    def _create_label(self, text):
        label = Gtk.Label()
        label.set_text(text)
        label.set_xalign(0.0)
        return label

    def _create_bindings(self, text):
        box = Gtk.Box()
        box.set_halign(Gtk.Align.END)
        box.set_spacing(6)
        if text.startswith("`"):
            keys = [text.replace("`", "")]
        else:
            keys = text.split()

        for key in keys:
            label = Gtk.Label()
            key = keyhint.utils.replace_keys(key.strip())
            label_context = label.get_style_context()
            if key in ["+", "/"]:
                label_context.add_class("dim-label")
            else:
                key = key.replace("\\/", "/")
                key = key.replace("\\+", "+")
                label_context.add_class("keycap")
            label.set_markup(f"{GLib.markup_escape_text(key)}")
            box.add(label)
        return box

    def _create_section_title(self, text):
        label = Gtk.Label()
        label.set_markup(f"<b>{text}</b>")
        label.set_xalign(0.0)
        label.set_margin_top(24)
        return label

    def _clear_hints_container(self):
        for child in self._hints_box.get_children():
            self._hints_box.remove(child)

    def _populate_select_hints_combo(self):
        for hint_id, title in self._get_hint_ids_titles():
            self._select_hints_combo.append(id=hint_id, text=title)

    def _populate_hints_container(self):
        hint_id = self._select_hints_combo.get_active_id()
        keyhints = self._get_hints_by_id(hint_id)
        hint_columns = self._distribute_hints_in_columns(keyhints)

        for column in hint_columns:
            grid = self._create_column_grid()
            idx = 0
            for section, shortcuts in column.items():
                section_title = self._create_section_title(section)
                grid.attach(section_title, left=1, top=idx, width=1, height=1)
                idx += 1
                for bindings in shortcuts:
                    bindings_box = self._create_bindings(bindings)
                    label = self._create_label(shortcuts[bindings])
                    grid.attach(bindings_box, left=0, top=idx, width=1, height=1)
                    grid.attach(label, left=1, top=idx, width=1, height=1)
                    idx += 1

            self._hints_box.pack_start(grid, False, False, 0)

        self._hints_box.show_all()

    def _adjust_window_dimensions(self):
        screen_width, screen_height = self._get_screen_dims()
        hints_box_width, hints_box_height = self._get_hints_box_dims()
        header_height = self._header_bar.size_request().height

        target_height = min(hints_box_height + header_height, screen_height // 1.1)
        target_width = min(hints_box_width + 80, screen_width // 1.1)

        self._window.resize(target_width, target_height)
        self._window.move(0, 0)

    # EVENT HANDLERS
    def on_quit(self):
        self._window.get_application().quit()

    def on_menu_quit(self, target):
        self.on_quit()

    def on_key_release(self, widget, event, data=None):
        if event.keyval == Gdk.KEY_Escape:
            if self._about_dialog_open:
                self._about_dialog_open = False
            else:
                self.on_quit()

    def on_select_hints_combo_changed(self, combo):
        self._clear_hints_container()
        self._populate_hints_container()
        self._adjust_window_dimensions()

    def on_window_destroy(self, *args):
        pass

    def on_window_realize(self, *args):
        self._populate_select_hints_combo()
        hint_id = self._get_appropriate_hint_id()
        self._select_hints_combo.set_active_id(hint_id)
        self._header_bar.set_subtitle(
            f"(wm_class: {self._wm_class}, title: {self._window_title})"
        )

    def on_menu_about(self, target):
        self._about_dialog_open = True
        self._about_dialog.run()
        self._about_dialog.hide()
