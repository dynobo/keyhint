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

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from keyhint import __version__, config, context, sheets, utils

logger = logging.getLogger("keyhint")

RESOURCE_PATH = Path(__file__).parent / "resources"

ActionCallbackType = Callable[
    [Gtk.ApplicationWindow, Gio.SimpleAction, GLib.Variant], None
]

# TODO: Flatpak


def check_state(func: ActionCallbackType) -> ActionCallbackType:
    """Decorator to only execute the function if the action state changed."""

    def wrapper(
        cls: Gtk.ApplicationWindow, action: Gio.SimpleAction, state: GLib.Variant
    ) -> None:
        if action.get_state() == state:
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
class HeaderBarBox(Gtk.Box):
    __gtype_name__ = "headerbar_box"

    sheet_dropdown: Gtk.DropDown = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    fullscreen_button = Gtk.Template.Child()
    headerbar: Adw.HeaderBar = Gtk.Template.Child()
    zoom_spin_button = Gtk.Template.Child()
    fallback_sheet_entry: Gtk.Entry = Gtk.Template.Child()

    def __init__(
        self, for_fullscreen: bool = False, decoration: str | None = None
    ) -> None:
        super().__init__()
        if for_fullscreen:
            self.headerbar.set_decoration_layout(":minimize,close")
            self.fullscreen_button.set_icon_name("view-restore-symbolic")
            self.set_visible(False)
        else:
            self.set_visible(True)


@Gtk.Template(filename=f"{RESOURCE_PATH}/window.ui")
class KeyhintWindow(Gtk.ApplicationWindow):
    """Handler for main ApplicationWindow."""

    __gtype_name__ = "main_window"

    overlay: Adw.ToastOverlay = Gtk.Template.Child()
    scrolled_window: Gtk.ScrolledWindow = Gtk.Template.Child()
    container: Gtk.Box = Gtk.Template.Child()
    sheet_container_box: Gtk.FlowBox = Gtk.Template.Child()

    shortcut_column_factory = Gtk.SignalListItemFactory()
    label_column_factory = Gtk.SignalListItemFactory()

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

        self.css_provider = utils.create_css_provider(
            display=self.get_display(), css=f"{RESOURCE_PATH}/style.css"
        )
        self.zoom_css_provider = utils.create_css_provider(display=self.get_display())
        self.set_icon_name("keyhint")

        # Add normal header bar
        self.headerbar = HeaderBarBox()
        self.set_titlebar(self.headerbar)

        # Add second header bar which is only visible in fullscreen mode
        self.headerbar_fs = HeaderBarBox(for_fullscreen=True)
        self.container.prepend(self.headerbar_fs)

        self.list_view_filter = Gtk.CustomFilter.new(
            match_func=self.list_view_match_func
        )

        # Set up the controls
        self.init_create_actions()
        self.init_connect_signals()
        self.init_add_key_event_controllers()
        self.init_populate_sheet_dropdown()
        self.init_apply_state()

        # Make sure the window is focused
        self.present()
        self.focus_search_entry()

    def init_apply_state(self) -> None:
        """Apply initial state of the stateful actions."""
        if self.config["main"].getboolean("fullscreen", False):
            self.activate_action("fullscreen")

        self.change_action_state(
            "fallback_sheet",
            GLib.Variant(
                "s", self.config["main"].get("fallback_cheatsheet", "keyhint")
            ),
        )
        self.change_action_state(
            "zoom", GLib.Variant("i", self.config["main"].getint("zoom", 100))
        )
        self.change_action_state(
            "sheet", GLib.Variant("s", self.get_appropriate_sheet_id())
        )

    def init_connect_signals(self) -> None:
        """Connect signals to methods."""
        for headerbar in [self.headerbar, self.headerbar_fs]:
            # Search entry
            self.search_changed_handler = headerbar.search_entry.connect(
                "search-changed", self.on_search_entry_changed
            )
            # Sheet drop down
            headerbar.sheet_dropdown.connect(
                "notify::selected-item",
                lambda btn, param: self.change_action_state(
                    "sheet", GLib.Variant("s", btn.get_selected_item().get_string())
                ),
            )
            # Zoom
            headerbar.zoom_spin_button.connect(
                "value-changed",
                lambda btn: self.change_action_state(
                    "zoom", GLib.Variant("i", btn.get_value_as_int())
                ),
            )

            # Default sheet
            headerbar.fallback_sheet_entry.connect(
                "changed",
                lambda entry: self.change_action_state(
                    "fallback_sheet", GLib.Variant("s", entry.get_text())
                ),
            )

        # Sheets filter
        self.sheet_container_box.set_filter_func(self.filter_sections_func)
        self.sheet_container_box.set_sort_func(self.sort_sections_func)

        # Column factories
        self.shortcut_column_factory.connect("bind", self.bind_shortcuts_callback)
        self.label_column_factory.connect("bind", self.bind_labels_callback)

        # Window state
        self.connect("notify::fullscreened", self.on_fullscreen_state_changed)

    def init_create_actions(self) -> None:
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

        action = Gio.SimpleAction.new("create_new_sheet", None)
        action.connect("activate", self.on_create_new_sheet)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful(
            name="fullscreen",
            state=GLib.Variant("b", False),
            parameter_type=None,
        )
        action.connect("activate", self.on_change_fullscreen)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful(
            name="sheet",
            state=GLib.Variant("s", "keyhint"),
            parameter_type=GLib.VariantType.new("s"),
        )
        action.connect("change-state", self.on_change_sheet)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful(
            name="sort_by",
            state=GLib.Variant("s", self.config["main"].get("sort_by", "size")),
            parameter_type=GLib.VariantType.new("s"),
        )
        action.connect("activate", self.on_change_sort)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful(
            name="orientation",
            state=GLib.Variant("s", self.config["main"].get("orientation", "vertical")),
            parameter_type=GLib.VariantType.new("s"),
        )
        action.connect("activate", self.on_change_orientation)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful(
            name="zoom",
            state=GLib.Variant("i", self.config["main"].getint("zoom", 100)),
            parameter_type=GLib.VariantType.new("i"),
        )
        action.connect("change-state", self.on_change_zoom)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful(
            name="fallback_sheet",
            state=GLib.Variant(
                "s", self.config["main"].get("fallback_cheatsheet", "keyhint")
            ),
            parameter_type=GLib.VariantType.new("s"),
        )
        action.connect("change-state", self.on_change_fallback_sheet)
        self.add_action(action)

    def init_add_key_event_controllers(self) -> None:
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

    def init_populate_sheet_dropdown(self) -> None:
        """Populate dropdown and select appropriate sheet."""
        # Populate the model with sheet ids
        model = self.headerbar.sheet_dropdown.get_model()
        for sheet_id in sorted([s["id"] for s in self.sheets]):
            model.append(sheet_id)

        # Use the same model for the fullscreen dropdown
        self.headerbar_fs.sheet_dropdown.set_model(model)

    @check_state
    def on_change_fallback_sheet(
        self, action: Gio.SimpleAction, state: GLib.Variant
    ) -> None:
        """Set the default sheet to use."""
        sheet_id = state.get_string()
        if sheet_id not in [s["id"] for s in self.sheets]:
            sheet_id = "keyhint"
            css_class = "error"
        else:
            css_class = ""
            self.config.set_persistent("main", "fallback_cheatsheet", sheet_id)
        self.headerbar.fallback_sheet_entry.set_text(sheet_id)
        self.headerbar_fs.fallback_sheet_entry.set_text(sheet_id)
        self.headerbar.fallback_sheet_entry.set_css_classes([css_class])
        self.headerbar_fs.fallback_sheet_entry.set_css_classes([css_class])

    @check_state
    def on_change_sheet(self, action: Gio.SimpleAction, state: GLib.Variant) -> None:
        sheet_id = state.get_string()

        # Update dropdown states
        dropdown_strings = [
            s.get_string() for s in self.headerbar.sheet_dropdown.get_model()
        ]
        select_idx = dropdown_strings.index(sheet_id)
        self.headerbar.sheet_dropdown.set_selected(select_idx)
        self.headerbar_fs.sheet_dropdown.set_selected(select_idx)

        # Render sheet
        self.show_sheet(sheet_id=sheet_id)

    @check_state
    def on_change_zoom(self, action: Gio.SimpleAction, state: GLib.Variant) -> None:
        """Set the zoom level of the sheet container."""
        value = state.get_int32()
        self.headerbar.zoom_spin_button.set_value(value)
        self.headerbar_fs.zoom_spin_button.set_value(value)
        self.zoom_css_provider.load_from_string(
            f"""
            .sheet_container_box,
            .sheet_container_box .bindings-section header label {{
                font-size: {value}%;
            }}
            """
        )
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
        self.list_view_filter.changed(Gtk.FilterChange.DIFFERENT)
        self.sheet_container_box.invalidate_filter()

    def on_search_entry_key_pressed(
        self,
        evk: Gtk.EventControllerKey,
        keycode,  # noqa: ANN001
        keyval,  # noqa: ANN001
        modifier,  # noqa: ANN001
    ) -> None:
        if keycode == Gdk.KEY_Escape:
            self.close()

    def on_key_pressed(
        self,
        evk: Gtk.EventControllerKey,
        keycode,  # noqa: ANN001
        keyval,  # noqa: ANN001
        modifier,  # noqa: ANN001
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

    def filter_sections_func(self, child: Gtk.Widget) -> bool:
        """Filter binding sections based on the search entry text."""
        # If no text, show all sections
        if not self.search_text:
            return True

        # If text, show only sections with 1 or more visible bindings
        column_view = child.get_child()
        selection = column_view.get_model()
        filter_model = selection.get_model()
        return filter_model.get_n_items() > 0

    def sort_sections_func(self, child_a: Gtk.Widget, child_b: Gtk.Widget) -> bool:
        sort_by = self.config["main"].get("sort_by", "size")
        if sort_by == "size":
            return (
                child_a.get_child().get_model().get_n_items()
                < child_b.get_child().get_model().get_n_items()
            )
        if sort_by == "title":
            return (
                child_a.get_child().get_columns().get_item(1).get_title()
                > child_b.get_child().get_columns().get_item(1).get_title()
            )
        return child_a.get_name() > child_b.get_name()

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
        model = self.sheet_drop_down.get_model()
        sheet_id = model.get_item(0).get_string()
        logger.debug("No matching or fallback sheet found. Using first sheet.")
        return sheet_id

    def bind_shortcuts_callback(
        self, _: Gtk.SignalListItemFactory, item: Gtk.Widget
    ) -> None:
        shortcut = utils.create_shortcut(item.get_item().shortcut)
        self.max_shortcut_width = max(
            self.max_shortcut_width, shortcut.get_preferred_size().natural_size.width
        )
        item.set_child(shortcut)

    def bind_labels_callback(
        self, _: Gtk.SignalListItemFactory, item: Gtk.Widget
    ) -> None:
        label = item.get_item().label
        if item.get_item().shortcut:
            child = Gtk.Label(label=label, xalign=0.0)
        else:
            # section title
            child = Gtk.Label(xalign=0.0)
            child.set_markup(f"<b>{label}</b>")
        item.set_child(child)

    def list_view_match_func(self, bindings_row: BindingsRow) -> bool:
        if self.search_text:
            return self.search_text.lower() in bindings_row.filter_text.lower()
        return True

    def show_sheet(self, sheet_id: str) -> None:
        if hasattr(self.sheet_container_box, "remove_all") and False:
            # Only available in GTK 4.12+
            self.sheet_container_box.remove_all()
        else:
            while child := self.sheet_container_box.get_first_child():
                self.sheet_container_box.remove(child)

        sheet = sheets.get_sheet_by_id(sheets=self.sheets, sheet_id=sheet_id)

        self.max_shortcut_width = 0

        sections = sheet["section"]

        for index, (section, bindings) in enumerate(sections.items()):
            section_child = self.create_section(section, bindings)
            section_child.set_name(f"section-{index:03}")
            self.sheet_container_box.append(section_child)

    def create_section(self, section: str, bindings: dict[str, str]) -> Gtk.Box:
        ls = Gio.ListStore()
        for shortcut, label in bindings.items():
            ls.append(BindingsRow(shortcut=shortcut, label=label, section=section))

        filter_list = Gtk.FilterListModel(model=ls)
        filter_list.set_filter(self.list_view_filter)

        selection = Gtk.NoSelection.new(filter_list)

        # TODO: Dynamic width based on content
        shortcut_column_width = self.config["main"].getint("zoom", 100) * 1.1 + 135
        shortcut_column = utils.create_column_view_column(
            "", self.shortcut_column_factory, shortcut_column_width
        )
        label_column = utils.create_column_view_column(
            section, self.label_column_factory
        )
        column_view = utils.create_column_view(selection, shortcut_column, label_column)

        section_child = Gtk.FlowBoxChild()
        section_child.set_vexpand(False)
        section_child.set_child(column_view)
        return section_child

    def get_debug_info_text(self) -> str:
        sheet_id = self.lookup_action("sheet").get_state().get_string()
        sheet = sheets.get_sheet_by_id(sheets=self.sheets, sheet_id=sheet_id)
        return (
            "\n"
            "<big>Last Active Application</big>\n\n"
            f"<span foreground='#FF2E88'>title:</span> {self.window_title}\n"
            f"<span foreground='#FF2E88'>wmclass:</span> {self.wm_class}\n"
            "\n\n"
            "<big>Selected Cheatsheet</big>\n\n"
            f"<span foreground='#FF2E88'>ID:</span> {sheet_id}\n"
            "<span foreground='#FF2E88'>regex_wmclass:</span> "
            f"{sheet.get('match',{}).get('regex_wmclass', 'n/a')}\n"
            "<span foreground='#FF2E88'>regex_title:</span> "
            f"{sheet.get('match', {}).get('regex_title', 'n/a')}\n"
            "<span foreground='#FF2E88'>source:</span> "
            f"<a href='{sheet.get('url', '')}'>"
            f"<span foreground='#00A6FF'>{sheet.get('url', 'n/a')}</span>"
            "</a>\n"
        )
