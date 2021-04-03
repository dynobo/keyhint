"""Logic handler used by the application window.

Does the rendering of the hints as well interface actions.
"""

import importlib.resources
import logging
import re
from typing import List, Optional, Tuple

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

import keyhint.utils

logger = logging.getLogger(__name__)


class WindowHandler:  # pylint: disable=too-many-instance-attributes
    """Handler for main ApplicationWindow."""

    _section_title_height: Optional[int] = None
    _row_height: Optional[int] = None
    _hints: List[dict] = keyhint.utils.load_hints()
    _dialog_is_open: bool = False
    _wm_class: str = ""
    _window_title: str = ""
    _hint_id: str = ""

    def __init__(self, builder, options):
        """Initialize during window creation."""
        self._options = options

        self._builder = builder
        self._about_dialog = builder.get_object("about_dialog")
        self._debug_info_dialog = builder.get_object("debug_info_dialog")
        self._window = builder.get_object("keyhint_app_window")
        self._header_bar = builder.get_object("header_bar")
        self._select_hints_combo = builder.get_object("select_hints_combo")
        self._hints_box = builder.get_object("hints_container_box")

        logger.debug(f"Loaded {len(self._hints)} hints.")

    def _get_screen_dims(self) -> Tuple[int, int]:
        screen = self._window.get_screen()
        display = screen.get_display()
        monitor = display.get_monitor_at_window(screen.get_root_window())
        workarea = monitor.get_workarea()
        return workarea.width, workarea.height

    def _get_hints_box_dims(self) -> Tuple[int, int]:
        size = self._hints_box.size_request()
        return size.width, size.height

    def _get_hint_ids_titles(self) -> List[Tuple[str, str]]:
        return [(k["id"], k["title"]) for k in self._hints]

    def _get_hints_by_id(self, hint_id: str) -> Optional[dict]:
        for hint in self._hints:
            if hint["id"] == hint_id:
                return hint
        return None

    def _get_hint_id_by_active_window(self) -> Optional[str]:
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

    def _get_appropriate_hint_id(self) -> Optional[str]:
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

    def _get_row_heights(self) -> Tuple[int, int]:
        if self._section_title_height and self._row_height:
            return self._section_title_height, self._row_height

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

    def _distribute_hints_in_columns(self, keyhints: dict) -> List[dict]:
        _, screen_height = self._get_screen_dims()
        max_column_height = screen_height // 1.3

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

    def _set_icons(self):
        with importlib.resources.path("keyhint.resources", "keyhint.svg") as ui_path:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(ui_path.absolute()))

        self._window.set_icon(pixbuf)
        self._about_dialog.set_logo(pixbuf)
        self._about_dialog.set_icon(pixbuf)

    @staticmethod
    def _create_column_grid() -> Gtk.Grid:
        column_grid = Gtk.Grid()
        column_grid.set_column_spacing(20)
        column_grid.set_row_spacing(10)
        return column_grid

    @staticmethod
    def _create_label(text) -> Gtk.Label:
        label = Gtk.Label()
        label.set_text(text)
        label.set_xalign(0.0)
        return label

    @staticmethod
    def _create_bindings(text) -> Gtk.Box:
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

    @staticmethod
    def _create_section_title(text) -> Gtk.Label:
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

        self._window.show_all()

    def _adjust_window_dimensions(self):

        screen_width, screen_height = self._get_screen_dims()
        hints_box_width, hints_box_height = self._get_hints_box_dims()
        header_height = self._header_bar.size_request().height
        target_height = min(hints_box_height + header_height, screen_height // 1.1)
        target_width = min(hints_box_width + 80, screen_width // 1.1)

        position_x = (screen_width - target_width) // 2
        position_y = (screen_height - target_height) // 2

        self._window.resize(target_width, target_height)
        self._window.move(position_x, position_y)

    # EVENT HANDLERS
    def on_quit(self):
        """Shutdown the application."""
        self._window.get_application().quit()

    def on_menu_quit(self, _):
        """Execute on click 'quit' in application menu."""
        self.on_quit()

    def on_key_release(
        self, widget, event, data=None  # pylint: disable=unused-argument
    ):
        """Execute on key release."""
        if event.keyval == Gdk.KEY_Escape:
            if self._dialog_is_open:
                self._dialog_is_open = False
            else:
                self.on_quit()

    def on_select_hints_combo_changed(self, _):
        """Execute on change of the hints selection dropdown."""
        self._clear_hints_container()
        self._populate_hints_container()
        self._adjust_window_dimensions()

    def on_window_destroy(self, _):  # pylint: disable=unused-argument,no-self-use
        """Execute on window close."""
        logger.debug("Closing application window.")

    def on_window_realize(self, _):
        """Execute on window realization on startup."""
        self._set_icons()
        self._populate_select_hints_combo()
        self._hint_id = self._get_appropriate_hint_id()
        self._select_hints_combo.set_active_id(self._hint_id)

    def on_menu_about(self, _):
        """Execute on click "about" in application menu."""
        self._dialog_is_open = True
        self._about_dialog.run()
        self._about_dialog.hide()

    def on_menu_debug_info(self, _):
        """Execute on click "debug info" in application menu."""
        hints = self._get_hints_by_id(self._hint_id)

        self._builder.get_object("debug_wm_class").set_text(self._wm_class)
        self._builder.get_object("debug_title").set_text(self._window_title)
        self._builder.get_object("debug_hint_id").set_text(hints["id"])
        self._builder.get_object("debug_hint_wmclass").set_text(
            hints["match"]["regex_process"]
        )
        self._builder.get_object("debug_hint_title").set_text(
            hints["match"]["regex_title"]
        )
        self._builder.get_object("debug_hint_source").set_label(
            "website with shortcuts"
        )
        logger.info(hints["source"])
        self._builder.get_object("debug_hint_source").set_uri(hints["source"])
        self._builder.get_object("debug_hint_yaml").set_text("not implemented")

        self._dialog_is_open = True
        self._debug_info_dialog.run()
        self._debug_info_dialog.hide()
