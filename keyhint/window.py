"""Logic handler used by the application window.

Does the rendering of the hints as well interface actions.
"""

import logging
import re
from typing import List, Optional, Tuple

from gi.repository import Gdk, GLib, Gtk

import keyhint

logger = logging.getLogger(__name__)

RESOURCE_PATH = __file__.rstrip("window.py") + "resources"


@Gtk.Template(filename=f"{RESOURCE_PATH}/window.ui")
class KeyhintWindow(Gtk.ApplicationWindow):
    """Handler for main ApplicationWindow."""

    __gtype_name__ = "main_window"
    _section_title_height: Optional[int] = None
    _row_height: Optional[int] = None
    _hints: List[dict] = keyhint.utils.load_hints()
    _dialog_is_open: bool = False
    _wm_class: str = ""
    _window_title: str = ""
    _hint_id: str = ""
    hints_combo_box: Gtk.ComboBox = Gtk.Template.Child()  # type: ignore
    hints_container_box: Gtk.Box = Gtk.Template.Child()  # type: ignore
    about_button: Gtk.Button = Gtk.Template.Child()  # type: ignore
    header_bar_title: Gtk.Label = Gtk.Template.Child()  # type: ignore
    scrolled_window: Gtk.ScrolledWindow = Gtk.Template.Child()  # type: ignore

    def __init__(self, options):
        """Initialize during window creation."""
        super().__init__()
        self._options = options

        self._load_css()
        self.set_icon_name("keyhint")
        logger.debug(f"Loaded {len(self._hints)} hints.")
        self.connect("realize", self.on_realize)

        evk = Gtk.EventControllerKey()
        evk.connect("key-released", self.on_key_release)
        self.add_controller(evk)  # add to window
        self.screen_width, self.screen_height = self._get_screen_dims()

    def _get_screen_dims(self) -> Tuple[int, int]:
        display = self.get_display()
        monitors = display.get_monitors()
        geometry = monitors.get_item(0).get_geometry()  # TODO: Find correct monitor
        return geometry.width, geometry.height

    def _get_hints_box_dims(self) -> Tuple[int, int]:
        size = self.hints_container_box.get_preferred_size().natural_size
        return size.width, size.height

    def _get_hint_ids_titles(self) -> List[Tuple[str, str]]:
        return [(k["id"], k["title"]) for k in self._hints]

    def _get_hints_by_id(self, hint_id: str) -> Optional[dict]:
        return next((hint for hint in self._hints if hint["id"] == hint_id), None)

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
            model = self.hints_combo_box.get_model()
            hint_id = model.get_value(model.get_iter_first(), 1)
            logger.debug("No matching hints found. Using first hint in list.")

        return hint_id

    def _get_row_heights(self) -> Tuple[int, int]:
        if self._section_title_height and self._row_height:
            return self._section_title_height, self._row_height

        grid = Gtk.Grid(column_spacing=20, row_spacing=10)
        spacing = grid.get_row_spacing()

        section_title = self._create_section_title("placeholder")
        grid.attach(section_title, column=1, row=0, width=1, height=1)
        bindings_box = self._create_bindings("Ctrl + A")
        label = Gtk.Label(label="TestingLabel", xalign=0.0)
        grid.attach(bindings_box, column=0, row=1, width=1, height=1)
        grid.attach(label, column=1, row=1, width=1, height=1)

        grid.show()

        title_height = section_title.get_preferred_size().natural_size.height + spacing
        row_height = section_title.get_preferred_size().natural_size.height + spacing

        logger.debug(f"Title height: {title_height}, Row height: {row_height}")
        return title_height, row_height

    def _distribute_hints_in_columns(self, keyhints: dict) -> List[dict]:
        max_column_height = self.screen_height // 1.2

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
                current_column = {section: hints}
                column_height = section_height

        if current_column:
            hint_columns.append(current_column)

        return hint_columns

    # GENERATE/MODIFY WIDGETS
    def _load_css(self):
        css_path = f"{RESOURCE_PATH}/style.css"
        provider = Gtk.CssProvider()
        provider.load_from_path(css_path)
        Gtk.StyleContext().add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    @staticmethod
    def _create_bindings(text) -> Gtk.Box:
        box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END
        )
        keys = [text.replace("`", "")] if text.startswith("`") else text.split()
        for key in keys:
            key = keyhint.utils.replace_keys(key.strip())
            label = Gtk.Label()
            if key in ["+", "/"]:
                label.set_css_classes(["dim-label"])
            else:
                key = key.replace("\\/", "/")
                key = key.replace("\\+", "+")
                label.set_css_classes(["keycap"])
            label.set_markup(f"{GLib.markup_escape_text(key)}")
            box.append(label)
        return box

    def _create_section_title(self, text) -> Gtk.Label:
        label = Gtk.Label(xalign=0.0, css_classes=["section-title"])
        label.set_markup(f"<b>{text}</b>")
        return label

    def _populate_hints_combo_box(self):
        for hint_id, title in self._get_hint_ids_titles():
            self.hints_combo_box.append(id=hint_id, text=title)

    def _clear_hints_container(self):
        while child := self.hints_container_box.get_first_child():
            child.get_parent().remove(child)

    def _populate_hints_container(self):
        hint_id = self.hints_combo_box.get_active_id()
        keyhints = self._get_hints_by_id(hint_id)
        hint_columns = self._distribute_hints_in_columns(keyhints)

        for column in hint_columns:
            grid = Gtk.Grid(column_spacing=20, row_spacing=8)
            grid.set_halign(Gtk.Align.START)
            grid.set_hexpand(False)
            idx = 0
            for section, shortcuts in column.items():
                section_title = self._create_section_title(section)
                grid.attach(section_title, column=1, row=idx, width=1, height=1)
                idx += 1
                for bindings in shortcuts:
                    bindings_box = self._create_bindings(bindings)
                    label = Gtk.Label(label=shortcuts[bindings], xalign=0.0)
                    grid.attach(bindings_box, column=0, row=idx, width=1, height=1)
                    grid.attach(label, column=1, row=idx, width=1, height=1)
                    idx += 1
            self.hints_container_box.append(grid)

    def _adjust_window_dimensions(self):
        hints_box_width, hints_box_height = self._get_hints_box_dims()
        header_height = 80  #  self._header_bar.get_preferred_size().natural_size.height
        target_height = min(hints_box_height + header_height, self.screen_height // 1.1)
        target_width = min(hints_box_width + 80, self.screen_width // 1.1)
        self.set_default_size(target_width, target_height)

        # TODO: self.move(position_x, position_y)

    def on_key_release(self, evk: Gtk.EventControllerKey, keycode, keyval, modifier):
        """Execute on key release."""
        if keycode == Gdk.KEY_Escape:
            if self._dialog_is_open:
                self._dialog_is_open = False
            else:
                self.close()
        elif keycode == Gdk.KEY_Down:
            idx = self.hints_combo_box.get_active()
            if idx + 1 < self.hints_combo_box.get_model().iter_n_children():
                self.hints_combo_box.set_active(idx + 1)
        elif keycode == Gdk.KEY_Up:
            idx = self.hints_combo_box.get_active()
            if idx > 0:
                self.hints_combo_box.set_active(idx - 1)
        elif keycode == Gdk.KEY_Right:
            hadj = self.scrolled_window.get_hadjustment()
            hadj.set_value(hadj.get_value() + self.screen_width // 3)
        elif keycode == Gdk.KEY_Left:
            hadj = self.scrolled_window.get_hadjustment()
            hadj.set_value(hadj.get_value() - self.screen_width // 3)

    def set_active_keyhint(self, hint_id):
        if hint_id == self._hint_id:
            return
        self._hint_id = hint_id
        self._active_keyhint = self._get_hints_by_id(self._hint_id)

    @Gtk.Template.Callback("on_hints_combo_box_changed")
    def on_select_hints_combo_changed(self, _):
        """Execute on change of the hints selection dropdown."""
        self.set_active_keyhint(self.hints_combo_box.get_active_id())
        self.header_bar_title.set_text(self._active_keyhint["title"] + " - Shortcuts")
        self._clear_hints_container()
        self._populate_hints_container()
        self._adjust_window_dimensions()

    def on_window_destroy(self, _):
        """Execute on window close."""
        logger.debug("Closing application window.")

    def on_realize(self, *_):
        """Execute on window realization on startup."""
        self._populate_hints_combo_box()
        self.hints_combo_box.set_active_id(self._get_appropriate_hint_id())
        self.hints_combo_box.grab_focus()

    @Gtk.Template.Callback("on_about_button_clicked")
    def open_about_dialog(self, _):
        """Execute on click "about" in application menu."""
        self._dialog_is_open = True
        logo = Gtk.Image.new_from_file(f"{RESOURCE_PATH}/keyhint.svg")
        Gtk.AboutDialog(
            program_name="KeyHint",
            comments="Cheatsheat for keyboard shortcuts &amp; commands",
            version=keyhint.__version__,
            website_label="Website",
            website="https://github.com/dynobo/keyhint",
            logo=logo.get_paintable(),
            system_information=self._get_debug_info(),
            modal=True,
            resizable=True,
            transient_for=self,
        ).show()

    def _get_debug_info(self) -> str:
        text = "Active Window:\n"
        text += f"\ttitle: {self._window_title}\n"
        text += f"\twmclass: {self._wm_class}\n"
        text += "\nSelected Hints:\n"
        text += f"\tID: {self._hint_id}\n"
        hints = self._get_hints_by_id(self._hint_id)
        if hints:
            text += f"\tregex_process: {hints['match']['regex_process']}\n"
            text += f"\tregex_title: {hints['match']['regex_title']}\n"
            text += f"\tsource: {hints['source']}\n"
        else:
            text += "No hints for this ID found!"
        return text
