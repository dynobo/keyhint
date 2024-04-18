"""Logic handler used by the application window.

Does the rendering of the cheatsheets as well interface actions.

Naming Hierarchy:
1. Keyhint works with multiple cheatsheets, in short "Sheets".
2. A single "Sheet" corresponds to one application and is rendered as one page in UI.
   The sheet to render can be selected in the dropdown field. Each sheet has a
   "Sheet ID" which must be unique.
3. A "Sheet" consists of multiple "Sections", which group together shortcuts or commands
   into a blocks. Each section has a section title.
4. A "Section" consists of multiple "Bindings"
5. A "Binding" consists of a "Shortcut", which contains the key combination or command,
   and a "Label" which describes the combination/command.
"""

import logging
import subprocess
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar, cast

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from keyhint import __version__, binding, config, context, css, sheets

logger = logging.getLogger("keyhint")

RESOURCE_PATH = Path(__file__).parent / "resources"

TKeyhintWindow = TypeVar("TKeyhintWindow", bound="KeyhintWindow")
TActionCallback = Callable[[TKeyhintWindow, Gio.SimpleAction, GLib.Variant], None]

# TODO: Flatpak


def check_state(func: TActionCallback) -> TActionCallback:
    """Decorator to only execute the function if the action state changed."""

    def wrapper(cls: Gtk.Widget, action: Gio.SimpleAction, state: GLib.Variant) -> None:
        if action.get_state_type() and action.get_state() == state:
            return None

        if state:
            action.set_state(state)

        return func(cls, action, state)

    return wrapper


class BindingsRow(GObject.Object):
    shortcut: str
    label: str
    filter_text: str

    def __init__(self, shortcut: str, label: str, section: str) -> None:
        super().__init__()
        self.shortcut = shortcut
        self.label = label
        self.filter_text = f"{shortcut} {label} {section}"


@Gtk.Template(filename=f"{RESOURCE_PATH}/headerbar.ui")
class HeaderBarBox(Gtk.HeaderBar):
    __gtype_name__ = "headerbar"

    sheet_dropdown = cast(Gtk.DropDown, Gtk.Template.Child())
    search_entry = cast(Gtk.SearchEntry, Gtk.Template.Child())
    fullscreen_button = cast(Gtk.ToggleButton, Gtk.Template.Child())
    zoom_scale = cast(Gtk.Scale, Gtk.Template.Child())
    fallback_sheet_entry = cast(Gtk.Entry, Gtk.Template.Child())
    fallback_sheet_button = cast(Gtk.Button, Gtk.Template.Child())

    def __init__(self, for_fullscreen: bool = False) -> None:
        super().__init__()
        if for_fullscreen:
            self.set_decoration_layout(":minimize,close")
            self.fullscreen_button.set_icon_name("view-restore-symbolic")
            self.set_visible(False)
        else:
            self.set_visible(True)


@Gtk.Template(filename=f"{RESOURCE_PATH}/window.ui")
class KeyhintWindow(Gtk.ApplicationWindow):
    """Handler for main ApplicationWindow."""

    __gtype_name__ = "main_window"

    overlay = cast(Adw.ToastOverlay, Gtk.Template.Child())
    scrolled_window = cast(Gtk.ScrolledWindow, Gtk.Template.Child())
    container = cast(Gtk.Box, Gtk.Template.Child())
    sheet_container_box = cast(Gtk.FlowBox, Gtk.Template.Child())

    shortcut_column_factory = Gtk.SignalListItemFactory()
    label_column_factory = Gtk.SignalListItemFactory()

    headerbar = HeaderBarBox()
    headerbar_fs = HeaderBarBox(for_fullscreen=True)

    max_shortcut_width = 0

    def __init__(self, cli_args: dict) -> None:
        """Initialize during window creation."""
        super().__init__()

        self.cli_args = cli_args
        self.config = config.load()
        self.sheets = sheets.load_sheets()
        self.wm_class, self.window_title = context.detect_active_window()

        self.skip_search_changed: bool = False
        self.search_text: str = ""

        self.css_provider = css.create_provider(
            display=self.get_display(), css=f"{RESOURCE_PATH}/style.css"
        )
        self.zoom_css_provider = css.create_provider(display=self.get_display())
        self.set_icon_name("keyhint")

        self.headerbars = [self.headerbar, self.headerbar_fs]
        self.set_titlebar(self.headerbar)
        self.container.prepend(self.headerbar_fs)

        self.bindings_filter = Gtk.CustomFilter.new(match_func=self.bindings_match_func)
        self.sheet_container_box.set_filter_func(filter_func=self.sections_filter_func)
        self.sheet_container_box.set_sort_func(sort_func=self.sections_sort_func)

        self.shortcut_column_factory.connect("bind", self.bind_shortcuts_callback)
        self.label_column_factory.connect("bind", self.bind_labels_callback)

        self.init_sheet_dropdown()
        self.init_action_sheet()
        self.init_action_fullscreen()
        self.init_action_sort_by()
        self.init_action_zoom()
        self.init_action_orientation()
        self.init_action_fallback_sheet()
        self.init_actions_for_menu_entries()
        self.init_actions_for_toasts()
        self.init_search_entry()
        self.init_key_event_controllers()

        self.focus_search_entry()

    def init_search_entry(self) -> None:
        """Connect signals to methods."""
        for headerbar in self.headerbars:
            # Search entry
            self.search_changed_handler = headerbar.search_entry.connect(
                "search-changed", self.on_search_entry_changed
            )

    def init_action_sort_by(self) -> None:
        # Create
        action = Gio.SimpleAction.new_stateful(
            name="sort_by",
            state=GLib.Variant("s", ""),
            parameter_type=GLib.VariantType.new("s"),
        )
        action.connect("activate", self.on_change_sort)
        action.connect("change-state", self.on_change_sort)
        self.add_action(action)

        # Connect
        # ... via headerbar.ui

        # Init state
        self.change_action_state(
            "sort_by", GLib.Variant("s", self.config["main"].get("sort_by", "size"))
        )

    def init_action_zoom(self) -> None:
        # Create
        action = Gio.SimpleAction.new_stateful(
            name="zoom",
            state=GLib.Variant("i", 0),
            parameter_type=GLib.VariantType.new("i"),
        )
        action.connect("change-state", self.on_change_zoom)
        self.add_action(action)

        # Connect & add marks
        for headerbar in self.headerbars:
            headerbar.zoom_scale.connect(
                "value-changed",
                lambda btn: self.change_action_state(
                    "zoom", GLib.Variant("i", btn.get_value())
                ),
            )
            slider_range = headerbar.zoom_scale.get_adjustment()
            for i in range(
                int(slider_range.get_lower()), int(slider_range.get_upper()) + 1, 25
            ):
                headerbar.zoom_scale.add_mark(
                    i, Gtk.PositionType.BOTTOM, f"<small>{i}</small>"
                )

        # Init state
        self.change_action_state(
            "zoom", GLib.Variant("i", self.config["main"].getint("zoom", 100))
        )

    def init_action_fullscreen(self) -> None:
        # Create
        action = Gio.SimpleAction.new_stateful(
            name="fullscreen",
            state=GLib.Variant("b", False),
            parameter_type=None,
        )
        action.connect("activate", self.on_change_fullscreen)
        action.connect("change-state", self.on_change_fullscreen)
        self.add_action(action)

        #  Connect
        # ... via headerbar.ui

        # Register Callback
        self.connect("notify::fullscreened", self.on_fullscreen_state_changed)

        # Init state
        self.change_action_state(
            "fullscreen",
            GLib.Variant("b", self.config["main"].getboolean("fullscreen", False)),
        )

    def init_action_orientation(self) -> None:
        # Create
        action = Gio.SimpleAction.new_stateful(
            name="orientation",
            state=GLib.Variant("s", ""),
            parameter_type=GLib.VariantType.new("s"),
        )
        action.connect("activate", self.on_change_orientation)
        action.connect("change-state", self.on_change_orientation)
        self.add_action(action)

        # Connect
        # ... via headerbar.ui

        # Init state
        self.change_action_state(
            "orientation",
            GLib.Variant("s", self.config["main"].get("orientation", "vertical")),
        )

    def init_action_fallback_sheet(self) -> None:
        # Create
        action = Gio.SimpleAction.new_stateful(
            name="fallback_sheet",
            state=GLib.Variant("s", ""),
            parameter_type=GLib.VariantType.new("s"),
        )
        action.connect("change-state", self.on_set_fallback_sheet)
        self.add_action(action)

        # Connect
        for headerbar in self.headerbars:
            headerbar.fallback_sheet_button.connect(
                "clicked",
                lambda *args: self.change_action_state(
                    "fallback_sheet",
                    GLib.Variant("s", self.get_current_sheet_id() or "keyhint"),
                ),
            )

        # Init state
        self.change_action_state(
            "fallback_sheet",
            GLib.Variant(
                "s", self.config["main"].get("fallback_cheatsheet", "keyhint")
            ),
        )

    def init_action_sheet(self) -> None:
        # Create
        action = Gio.SimpleAction.new_stateful(
            name="sheet",
            state=GLib.Variant("s", ""),
            parameter_type=GLib.VariantType.new("s"),
        )
        action.connect("change-state", self.on_change_sheet)
        self.add_action(action)

        # Connect
        for headerbar in self.headerbars:
            headerbar.sheet_dropdown.connect(
                "notify::selected-item",
                lambda btn, param: self.change_action_state(
                    "sheet", GLib.Variant("s", btn.get_selected_item().get_string())
                ),
            )

        # Init state
        self.change_action_state(
            "sheet", GLib.Variant("s", self.get_appropriate_sheet_id())
        )

    def init_actions_for_menu_entries(self) -> None:
        """Add actions accessible in the UI."""
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about_action)
        self.add_action(action)

        action = Gio.SimpleAction.new("debug_info", None)
        action.connect("activate", self.on_debug_action)
        self.add_action(action)

        action = Gio.SimpleAction.new("open_folder", None)
        action.connect("activate", self.on_open_folder_action)
        self.add_action(action)

    def init_actions_for_toasts(self) -> None:
        action = Gio.SimpleAction.new("create_new_sheet", None)
        action.connect("activate", self.on_create_new_sheet)
        self.add_action(action)

    def init_key_event_controllers(self) -> None:
        """Register key press handler."""
        evk = Gtk.EventControllerKey()
        evk.connect("key-pressed", self.on_key_pressed)
        self.add_controller(evk)

        evk = Gtk.EventControllerKey()
        evk.connect("key-pressed", self.on_search_entry_key_pressed)
        self.headerbar.search_entry.add_controller(evk)

        # NOTE: Reusing the same evk would lead to critical assertion error!
        evk = Gtk.EventControllerKey()
        evk.connect("key-pressed", self.on_search_entry_key_pressed)
        self.headerbar_fs.search_entry.add_controller(evk)

    def init_sheet_dropdown(self) -> None:
        """Populate dropdown and select appropriate sheet."""
        # Populate the model with sheet ids
        model = self.headerbar.sheet_dropdown.get_model()

        if not isinstance(model, Gtk.StringList):
            raise TypeError("Sheet dropdown model is not a Gtk.StringList.")

        for sheet_id in sorted([s["id"] for s in self.sheets]):
            model.append(sheet_id)

        # Use the same model for the fullscreen dropdown
        self.headerbar_fs.sheet_dropdown.set_model(model)

    @check_state
    def on_set_fallback_sheet(
        self, action: Gio.SimpleAction, state: GLib.Variant
    ) -> None:
        """Set the default sheet to use."""
        sheet_id = state.get_string()
        self.config.set_persistent("main", "fallback_cheatsheet", sheet_id)
        for headerbar in self.headerbars:
            headerbar.fallback_sheet_entry.set_text(sheet_id)

    @check_state
    def on_change_sheet(self, action: Gio.SimpleAction, state: GLib.Variant) -> None:
        sheet_id = state.get_string()

        # Update dropdown states
        if dropdown_model := self.headerbar.sheet_dropdown.get_model():
            dropdown_strings = [
                s.get_string()
                for s in dropdown_model
                if isinstance(s, Gtk.StringObject)
            ]
        else:
            dropdown_strings = []

        select_idx = dropdown_strings.index(sheet_id)
        self.headerbar.sheet_dropdown.set_selected(select_idx)
        self.headerbar_fs.sheet_dropdown.set_selected(select_idx)

        # Render sheet
        self.show_sheet(sheet_id=sheet_id)

    @check_state
    def on_change_zoom(self, action: Gio.SimpleAction, state: GLib.Variant) -> None:
        """Set the zoom level of the sheet container."""
        value = state.get_int32()
        css_style = f"""
                .sheet_container_box,
                .sheet_container_box .bindings-section header label {{
                    font-size: {value}%;
                }}
                """
        self.headerbar.zoom_scale.set_value(value)
        self.headerbar_fs.zoom_scale.set_value(value)
        if hasattr(self.zoom_css_provider, "load_from_string"):
            # GTK 4.12+
            self.zoom_css_provider.load_from_string(css_style)
        else:
            # ONHOLD: Remove once GTK 4.12+ is required
            self.zoom_css_provider.load_from_data(css_style, len(css_style))

        self.config.set_persistent("main", "zoom", str(int(value)))

    @check_state
    def on_change_orientation(
        self, action: Gio.SimpleAction, state: GLib.Variant
    ) -> None:
        """Set the orientation of the sheet container."""
        # The used GTK orientation is the opposite of the config value, which follows
        # the naming from user perspective!
        value = state.get_string()
        gtk_orientation = (
            Gtk.Orientation.VERTICAL
            if value == "horizontal"
            else Gtk.Orientation.HORIZONTAL
        )

        self.sheet_container_box.set_orientation(gtk_orientation)
        self.config.set_persistent("main", "orientation", value)

    @check_state
    def on_change_sort(self, action: Gio.SimpleAction, state: GLib.Variant) -> None:
        """Set the order of the sections."""
        self.config.set_persistent("main", "sort_by", state.get_string())
        self.sheet_container_box.invalidate_sort()

    @check_state
    def on_change_fullscreen(
        self, action: Gio.SimpleAction, state: GLib.Variant
    ) -> None:
        """Set the fullscreen state."""
        if state is not None:
            to_fullscreen = bool(state)
        else:
            # toggle
            to_fullscreen = not bool(action.get_state())
        action.set_state(GLib.Variant("b", to_fullscreen))

        self.skip_search_changed = True
        if to_fullscreen:
            self.headerbar_fs.search_entry.set_text(self.search_text)
            self.fullscreen()
        else:
            self.headerbar.search_entry.set_text(self.search_text)
            self.unfullscreen()

        self.config.set_persistent("main", "fullscreen", to_fullscreen)

    def scroll(self, to_start: bool, by_page: bool) -> None:
        if self.sheet_container_box.get_orientation() == 1:
            adj = self.scrolled_window.get_hadjustment()
        else:
            adj = self.scrolled_window.get_vadjustment()

        default_distance = 25
        distance = adj.get_page_size() if by_page else default_distance
        if to_start:
            distance *= -1

        adj.set_value(adj.get_value() + distance)

    def focus_search_entry(self) -> None:
        """Focus search entry depending on state."""
        if self.is_fullscreen():
            self.headerbar_fs.search_entry.grab_focus()
            self.headerbar_fs.search_entry.set_position(-1)
        else:
            self.headerbar.search_entry.grab_focus()
            self.headerbar.search_entry.set_position(-1)

    def show_create_new_sheet_toast(self) -> None:
        toast = Adw.Toast.new(f"No cheatsheet found for '{self.wm_class}'.")
        toast.set_button_label("Create new")
        toast.set_action_name("win.create_new_sheet")
        toast.set_timeout(5)
        self.overlay.add_toast(toast)

    def on_fullscreen_state_changed(self, _: Gtk.Widget, __: GObject.Parameter) -> None:
        """Hide header bar in title and show it in window instead, and vice versa."""
        if self.is_fullscreen():
            self.headerbar_fs.set_visible(True)
        else:
            self.headerbar_fs.set_visible(False)
        self.focus_search_entry()

    def on_search_entry_changed(self, search_entry: Gtk.SearchEntry) -> None:
        """Execute on change of the sheet selection dropdown."""
        if self.skip_search_changed:
            self.skip_search_changed = False
            return

        if search_entry.get_text() == self.search_text:
            return

        self.search_text = search_entry.get_text()
        self.bindings_filter.changed(Gtk.FilterChange.DIFFERENT)
        self.sheet_container_box.invalidate_filter()

    def on_search_entry_key_pressed(
        self,
        evk: Gtk.EventControllerKey,
        keycode: int,
        keyval: int,
        modifier: Gdk.ModifierType,
    ) -> None:
        if keycode == Gdk.KEY_Escape:
            self.close()

    def on_key_pressed(
        self,
        evk: Gtk.EventControllerKey,
        keycode: int,
        keyval: int,
        modifier: Gdk.ModifierType,
    ) -> None:
        ctrl_pressed = modifier == Gdk.ModifierType.CONTROL_MASK
        match keycode, ctrl_pressed:
            case Gdk.KEY_Escape, _:
                # If the dialog is open, that one is closed. Otherwise close the window
                self.close()
            case Gdk.KEY_F11, _:
                self.activate_action("win.fullscreen")
            case Gdk.KEY_f, True:
                # Focus search entry
                if self.is_fullscreen():
                    self.headerbar_fs.search_entry.grab_focus()
                else:
                    self.headerbar.search_entry.grab_focus()
            case Gdk.KEY_s, True:
                # Open sheet dropdown
                if self.is_fullscreen():
                    self.headerbar_fs.sheet_dropdown.grab_focus()
                else:
                    self.headerbar.sheet_dropdown.grab_focus()
            case (Gdk.KEY_Up, _) | (Gdk.KEY_k, True):
                self.scroll(to_start=True, by_page=False)
            case (Gdk.KEY_Down, _) | (Gdk.KEY_j, True):
                self.scroll(to_start=False, by_page=False)
            case Gdk.KEY_Page_Up, _:
                self.scroll(to_start=True, by_page=True)
            case Gdk.KEY_Page_Down, _:
                self.scroll(to_start=False, by_page=True)

    def on_about_action(self, _: Gio.SimpleAction, __: None) -> None:
        """Execute on click "about" in application menu."""
        logo = Gtk.Image.new_from_file(f"{RESOURCE_PATH}/keyhint_icon.svg")
        Gtk.AboutDialog(
            program_name="KeyHint",
            comments="Cheatsheet for keyboard shortcuts & commands",
            version=__version__,
            website_label="Github",
            website="https://github.com/dynobo/keyhint",
            logo=logo.get_paintable(),
            license_type=Gtk.License.MIT_X11,
            modal=True,
            resizable=True,
            transient_for=self,
        ).show()

    def on_debug_action(self, _: Gio.SimpleAction, __: None) -> None:
        dialog = Gtk.Dialog(title="Debug Info", transient_for=self, modal=True)
        label = Gtk.Label()
        label.set_use_markup(True)
        label.set_wrap(True)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_markup(self.get_debug_info_text())
        label.set_margin_start(24)
        label.set_margin_end(24)

        dialog.set_child(label)
        dialog.show()

    def on_create_new_sheet(self, _: Gio.SimpleAction, __: None) -> None:
        title = self.wm_class.lower().replace(" ", "")
        pad = 26 - len(title)
        template = f"""\
            id = "{title}"{" " * pad } # Unique ID, used e.g. in cheatsheet dropdown
            url = ""                       # (Optional) URL to keybinding docs

            [match]
            regex_wmclass = "{self.wm_class}"
            regex_title = ".*"                # Narrow down by window title if needed

            [section]

            [section."My Section Title"]      # Add as many sections you like ...
            "Ctrl + c" = "Copy to clipboard"  # ... with keybinding + description
            "Ctrl + v" = "Paste from clipboard"
        """
        template = textwrap.dedent(template)
        new_file = config.CONFIG_PATH / f"{title}.toml"
        for idx in range(1, 100):
            if new_file.exists():
                new_file = new_file.with_name(f"{title}_{idx}.toml")
            else:
                break
        new_file.write_text(template)
        subprocess.Popen(["xdg-open", str(new_file.resolve())])  # noqa: S603, S607

    def on_open_folder_action(self, _: Gio.SimpleAction, __: None) -> None:
        subprocess.Popen(["xdg-open", str(config.CONFIG_PATH.resolve())])  # noqa: S603, S607

    def sections_filter_func(self, child: Gtk.FlowBoxChild) -> bool:
        """Filter binding sections based on the search entry text."""
        # If no text, show all sections
        if not self.search_text:
            return True

        # If text, show only sections with 1 or more visible bindings
        column_view = child.get_child()
        if not isinstance(column_view, Gtk.ColumnView):
            raise TypeError("Child is not a ColumnView.")

        selection = column_view.get_model()
        if not isinstance(selection, Gtk.NoSelection):
            raise TypeError("ColumnView model is not a NoSelection.")

        filter_model = selection.get_model()
        if not isinstance(filter_model, Gtk.FilterListModel):
            raise TypeError("ColumnView model is not a FilterListModel.")

        return filter_model.get_n_items() > 0

    def sections_sort_func(
        self, child_a: Gtk.FlowBoxChild, child_b: Gtk.FlowBoxChild
    ) -> bool:
        sort_by = self.config["main"].get("sort_by", "size")

        if sort_by == "native":
            return child_a.get_name() > child_b.get_name()

        sub_child_a = child_a.get_child()
        sub_child_b = child_b.get_child()
        if not isinstance(sub_child_a, Gtk.ColumnView) or not isinstance(
            sub_child_b, Gtk.ColumnView
        ):
            raise TypeError("Child is not a ColumnView.")

        if sort_by == "size":
            model_a = sub_child_a.get_model()
            model_b = sub_child_b.get_model()
            if not isinstance(model_a, Gtk.NoSelection) or not isinstance(
                model_b, Gtk.NoSelection
            ):
                raise TypeError("ColumnView model is not a NoSelection.")
            return model_a.get_n_items() < model_b.get_n_items()

        if sort_by == "title":
            column_a = sub_child_a.get_columns().get_item(1)
            column_b = sub_child_b.get_columns().get_item(1)
            if not isinstance(column_a, Gtk.ColumnViewColumn) or not isinstance(
                column_b, Gtk.ColumnViewColumn
            ):
                raise TypeError("Column is not a ColumnViewColumn.")
            return (column_a.get_title() or "") > (column_b.get_title() or "")

        raise ValueError(f"Invalid sort_by value: {sort_by}")

    def get_appropriate_sheet_id(self) -> str:
        sheet_id = None

        # If sheet-id was provided via cli option, use that one
        if sheet_id := self.cli_args.get("cheatsheet", None):
            logger.debug("Using provided sheet-id: %s.", sheet_id)
            return sheet_id

        # Else try to find cheatsheet for active window
        if sheet_id := sheets.get_sheet_id_by_active_window(
            sheets=self.sheets, wm_class=self.wm_class, window_title=self.window_title
        ):
            logger.debug("Found matching sheet: %s.", sheet_id)
            return sheet_id

        self.show_create_new_sheet_toast()

        # Use configured fallback
        if sheet_id := self.config["main"].get("fallback_cheatsheet", ""):
            logger.debug("Using provided fallback sheet-id: %s.", sheet_id)
            return sheet_id

        # Fallback to first entry in list
        model = self.headerbar.sheet_dropdown.get_model()
        item = model.get_item(0) if model else None
        sheet_id = (
            item.get_string() if isinstance(item, Gtk.StringObject) else "keyhint"
        )
        logger.debug("No matching or fallback sheet found. Using first sheet.")
        return sheet_id

    def bind_shortcuts_callback(
        self,
        _: Gtk.SignalListItemFactory,
        item: Gtk.ColumnViewCell,  # type: ignore  # Available since GTK 4.12
    ) -> None:
        row = cast(BindingsRow, item.get_item())
        shortcut = binding.create_shortcut(row.shortcut)
        self.max_shortcut_width = max(
            self.max_shortcut_width,
            shortcut.get_preferred_size().natural_size.width,  # type: ignore # False Positive
        )
        item.set_child(shortcut)

    def bind_labels_callback(
        self,
        _: Gtk.SignalListItemFactory,
        item: Gtk.ColumnViewCell,  # type: ignore  # Available since GTK 4.12
    ) -> None:
        row = cast(BindingsRow, item.get_item())
        if row.shortcut:
            child = Gtk.Label(label=row.label, xalign=0.0)
        else:
            # section title
            child = Gtk.Label(xalign=0.0)
            child.set_markup(f"<b>{row.label}</b>")
        item.set_child(child)

    def bindings_match_func(self, bindings_row: BindingsRow) -> bool:
        if self.search_text:
            return self.search_text.lower() in bindings_row.filter_text.lower()
        return True

    def show_sheet(self, sheet_id: str) -> None:
        if hasattr(self.sheet_container_box, "remove_all"):
            # Only available in GTK 4.12+
            self.sheet_container_box.remove_all()
        else:
            # ONHOLD: Remove once GTK 4.12+ is required
            while child := self.sheet_container_box.get_first_child():
                self.sheet_container_box.remove(child)

        sheet = sheets.get_sheet_by_id(sheets=self.sheets, sheet_id=sheet_id)

        self.max_shortcut_width = 0

        sections = sheet["section"]

        for index, (section, bindings) in enumerate(sections.items()):
            section_child = self.create_section(section, bindings)
            section_child.set_name(f"section-{index:03}")
            self.sheet_container_box.append(section_child)

    def create_section(
        self, section: str, bindings: dict[str, str]
    ) -> Gtk.FlowBoxChild:
        ls = Gio.ListStore()
        for shortcut, label in bindings.items():
            ls.append(BindingsRow(shortcut=shortcut, label=label, section=section))

        filter_list = Gtk.FilterListModel(model=ls)
        filter_list.set_filter(self.bindings_filter)

        selection = Gtk.NoSelection.new(filter_list)

        # TODO: Dynamic width based on content
        shortcut_column_width = self.config["main"].getint("zoom", 100) * 1.1 + 135
        shortcut_column = binding.create_column_view_column(
            "", self.shortcut_column_factory, shortcut_column_width
        )
        label_column = binding.create_column_view_column(
            section, self.label_column_factory
        )
        column_view = binding.create_column_view(
            selection, shortcut_column, label_column
        )

        section_child = Gtk.FlowBoxChild()
        section_child.set_vexpand(False)
        section_child.set_child(column_view)
        return section_child

    def get_current_sheet_id(self) -> str:
        action = self.lookup_action("sheet")
        state = action.get_state() if action else None
        return state.get_string() if state else ""

    def get_debug_info_text(self) -> str:
        sheet_id = self.get_current_sheet_id()
        sheet = (
            sheets.get_sheet_by_id(sheets=self.sheets, sheet_id=sheet_id)
            if sheet_id
            else {}
        )
        regex_wm_class = sheet.get("match", {}).get("regex_wmclass", "n/a")
        regex_title = sheet.get("match", {}).get("regex_title", "n/a")
        link = sheet.get("url", "")
        link_text = f"<span foreground='#00A6FF'>{link or 'n/a'}</span>"

        return textwrap.dedent(
            f"""
            <big>Last Active Application</big>

            <span foreground='#FF2E88'>title:</span> {self.window_title}
            <span foreground='#FF2E88'>wmclass:</span> {self.wm_class}

            <big>Selected Cheatsheet</big>

            <span foreground='#FF2E88'>ID:</span> {sheet_id}
            <span foreground='#FF2E88'>regex_wmclass:</span> {regex_wm_class}
            <span foreground='#FF2E88'>regex_title:</span> {regex_title}
            <span foreground='#FF2E88'>source:</span> <a href='{link}'>{link_text}</a>
            """
        )
