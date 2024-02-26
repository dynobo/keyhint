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
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from gi.repository import Adw, Gdk, Gio, GObject, Gtk

from keyhint import __version__, config, context, sheets, utils

logger = logging.getLogger("keyhint")

RESOURCE_PATH = Path(__file__).parent / "resources"


class BindingsRow(GObject.Object):
    shortcut: str
    label: str
    filter_text: str

    def __init__(self, shortcut: str, label: str, section: str) -> None:
        super().__init__()
        self.shortcut = shortcut
        self.label = label
        self.filter_text = f"{shortcut} {label} {section}"


@Gtk.Template(filename=f"{RESOURCE_PATH}/header_bar.ui")
class HeaderBar(Gtk.Box):
    __gtype_name__ = "header_bar"

    sheet_drop_down: Gtk.DropDown = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    fullscreen_button = Gtk.Template.Child()
    adwheaderbar: Adw.HeaderBar = Gtk.Template.Child()
    sort_by_size_button = Gtk.Template.Child()
    sort_by_title_button = Gtk.Template.Child()
    sort_by_native_button = Gtk.Template.Child()
    scroll_vertical_button = Gtk.Template.Child()
    scroll_horizontal_button = Gtk.Template.Child()
    zoom_spin_button = Gtk.Template.Child()
    fallback_sheet_entry: Gtk.Entry = Gtk.Template.Child()

    def __init__(
        self, for_fullscreen: bool = False, decoration: str | None = None
    ) -> None:
        super().__init__()
        if for_fullscreen:
            self.adwheaderbar.set_decoration_layout(":minimize,close")
            self.fullscreen_button.set_icon_name("view-restore-symbolic")
            self.set_visible(False)
        else:
            self.set_visible(True)


@Gtk.Template(filename=f"{RESOURCE_PATH}/window.ui")
class KeyhintWindow(Gtk.ApplicationWindow):
    """Handler for main ApplicationWindow."""

    __gtype_name__ = "main_window"

    dialog_is_open: bool = False
    wm_class: str = ""
    window_title: str = ""
    sheet_id: str = ""
    ignore_search_changed: bool = False
    search_text: str = ""

    scrolled_window: Gtk.ScrolledWindow = Gtk.Template.Child()
    container: Gtk.Box = Gtk.Template.Child()
    sheet_container_box: Gtk.FlowBox = Gtk.Template.Child()

    max_shortcut_width = 0

    def __init__(self, cli_args: dict) -> None:
        """Initialize during window creation."""
        super().__init__()

        self.cli_args = cli_args
        self.config = config.load()
        self.sheets = sheets.load_sheets()

        self.load_css()
        self.zoom_css_provider = self.init_zoom_css_provider()
        self.set_icon_name("keyhint")

        # Add normal header bar
        self.headerbar = HeaderBar()
        self.set_titlebar(self.headerbar)

        # Add second header bar which is only visible in fullscreen mode
        self.headerbar_fs = HeaderBar(for_fullscreen=True)
        self.container.prepend(self.headerbar_fs)

        self.shortcut_column_factory = self.create_list_item_factory(
            self.bind_shortcuts_callback
        )
        self.label_column_factory = self.create_list_item_factory(
            self.bind_labels_callback
        )
        self.list_view_filter = Gtk.CustomFilter.new(
            match_func=self.list_view_match_func
        )

        # Set up the controls
        self.init_signals()
        self.init_actions()
        self.init_binds()
        self.init_sheet_drop_down()
        self.init_search_entry()
        self.init_event_controller_key()

        # Apply loaded configuration
        self.toggle_orientation(
            None, self.config["main"].get("orientation", "horizontal")
        )
        self.toggle_sort(None, self.config["main"].get("sort_by", "size"))
        self.toggle_fullscreen(self.config["main"].getboolean("fullscreen", False))
        self.zoom(self.config["main"].getint("zoom", 100))
        self.headerbar.fallback_sheet_entry.set_text(
            self.config["main"].get("default_cheatsheet", "keyhint")
        )

        # Make sure the window is focused
        self.present()
        self.focus_search_entry()

    def init_signals(self) -> None:
        """Connect signals to methods."""
        # Fullscreen button
        self.headerbar.fullscreen_button.connect(
            "clicked", lambda _: self.toggle_fullscreen()
        )
        self.headerbar_fs.fullscreen_button.connect(
            "clicked", lambda _: self.toggle_fullscreen()
        )

        # Search entry
        self.search_changed_handler = self.headerbar.search_entry.connect(
            "search-changed", self.on_search_entry_changed
        )
        self.search_fs_changed_handler = self.headerbar_fs.search_entry.connect(
            "search-changed", self.on_search_entry_changed
        )

        # Sheet drop down
        self.headerbar.sheet_drop_down.connect(
            "notify::selected-item", self.on_sheet_drop_down_changed
        )

        # Scroll orientation
        scroll_buttons = (
            (self.headerbar.scroll_vertical_button, "vertical"),
            (self.headerbar_fs.scroll_vertical_button, "vertical"),
            (self.headerbar.scroll_horizontal_button, "horizontal"),
            (self.headerbar_fs.scroll_horizontal_button, "horizontal"),
        )
        for button, orientation in scroll_buttons:
            button.connect(
                "notify::active",
                self.toggle_orientation_func(value=orientation),
            )

        # Sort
        sort_buttons = (
            (self.headerbar.sort_by_size_button, "size"),
            (self.headerbar_fs.sort_by_size_button, "size"),
            (self.headerbar.sort_by_title_button, "title"),
            (self.headerbar_fs.sort_by_title_button, "title"),
            (self.headerbar.sort_by_native_button, "native"),
            (self.headerbar_fs.sort_by_native_button, "native"),
        )
        for button, direction in sort_buttons:
            button.connect(
                "notify::active",
                self.toggle_sort_func(value=direction),
            )

        # Zoom
        self.headerbar.zoom_spin_button.connect(
            "value-changed", lambda btn: self.zoom(btn.get_value())
        )
        self.headerbar_fs.zoom_spin_button.connect(
            "value-changed", lambda btn: self.zoom(btn.get_value())
        )

        # Default sheet
        self.headerbar.fallback_sheet_entry.connect(
            "changed",
            lambda entry: self.set_default_sheet(entry.get_text()),
        )

        # Sheets filter
        self.sheet_container_box.set_filter_func(self.filter_sections_func)
        self.sheet_container_box.set_sort_func(self.sort_sections_func)

        # Window state
        self.connect("notify::fullscreened", self.on_fullscreen_state_changed)

    def init_actions(self) -> None:
        """Add actions used by main menu."""
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about_action)
        self.add_action(action)

    def init_event_controller_key(self) -> None:
        """Register key press handler."""
        evk = Gtk.EventControllerKey()
        evk.connect("key-pressed", self.on_key_pressed)
        self.add_controller(evk)

    def init_sheet_drop_down(self) -> None:
        """Populate dropdown and select appropriate sheet."""
        # Populate the model with sheet ids
        model = self.headerbar.sheet_drop_down.get_model()
        for sheet_id in sorted([s["id"] for s in self.sheets]):
            model.append(sheet_id)

        # Use the same model for the fullscreen dropdown and bind changes
        self.headerbar_fs.sheet_drop_down.set_model(model)

        # Select entry with appropriate sheet id
        drop_down_strings = [
            s.get_string() for s in self.headerbar.sheet_drop_down.get_model()
        ]
        select_idx = drop_down_strings.index(self.get_appropriate_sheet_id())
        self.headerbar.sheet_drop_down.set_selected(select_idx)

    def init_search_entry(self) -> None:
        """Let search entry capture key events."""
        # Bind changes between search entries in header bar and for fullscreen
        evk = Gtk.EventControllerKey()
        evk.connect("key-pressed", self.on_search_entry_key_pressed)
        self.headerbar.search_entry.add_controller(evk)

        # Reusing the same evk leads to critical assertion error
        evk = Gtk.EventControllerKey()
        evk.connect("key-pressed", self.on_search_entry_key_pressed)
        self.headerbar_fs.search_entry.add_controller(evk)

    def init_binds(self) -> None:
        """Bind properties of controls between both header bars."""
        widgets = [
            ("sort_by_size_button", "active"),
            ("sort_by_title_button", "active"),
            ("sort_by_native_button", "active"),
            ("scroll_vertical_button", "active"),
            ("scroll_horizontal_button", "active"),
            ("zoom_spin_button", "value"),
            ("fallback_sheet_entry", "text"),
            ("sheet_drop_down", "selected"),
        ]
        for widget, prop in widgets:
            getattr(self.headerbar, widget).bind_property(
                prop,
                getattr(self.headerbar_fs, widget),
                prop,
                GObject.BindingFlags.BIDIRECTIONAL,
            )

    def init_zoom_css_provider(self) -> Gtk.CssProvider:
        provider = Gtk.CssProvider()
        Gtk.StyleContext().add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        return provider

    def set_default_sheet(self, sheet_id: str) -> None:
        """Set the default sheet to use."""
        if sheet_id not in [s["id"] for s in self.sheets]:
            sheet_id = "keyhint"
            css_class = "error"
        else:
            css_class = "success"
        self.headerbar.fallback_sheet_entry.set_css_classes([css_class])
        self.headerbar_fs.fallback_sheet_entry.set_css_classes([css_class])
        self.config.set_persistent("main", "default_cheatsheet", sheet_id)

    def zoom(self, value: float) -> None:
        """Set the zoom level of the sheet container."""
        self.headerbar.zoom_spin_button.set_value(value)
        self.zoom_css_provider.load_from_string(
            f"""
            .sheet_container_box,
            .sheet_container_box .bindings-section header label {{
                font-size: {value}%;
            }}
            """
        )
        self.config.set_persistent("main", "zoom", str(int(value)))

    def toggle_orientation_func(self, value: str) -> Callable:
        """Set the orientation of the sheet container."""
        return lambda btn, _: self.toggle_orientation(btn, value)

    def toggle_orientation(self, btn: Gtk.ToggleButton | None, value: str) -> None:
        """Set the orientation of the sheet container."""
        # The used GTK orientation is the opposite of the config value, which follows
        # the naming from user perspective!
        if btn and not btn.get_active():
            return

        if not btn:
            match value:
                case "horizontal":
                    self.headerbar.scroll_horizontal_button.set_active(True)
                case "vertical":
                    self.headerbar.scroll_vertical_button.set_active(True)

        gtk_orientation = (
            Gtk.Orientation.VERTICAL
            if value == "horizontal"
            else Gtk.Orientation.HORIZONTAL
        )
        self.sheet_container_box.set_orientation(gtk_orientation)
        self.config.set_persistent("main", "orientation", value)

    def toggle_sort_func(self, value: str) -> Callable:
        """Create function to toggle the order of the sections."""
        return lambda btn, _: self.toggle_sort(btn, value)

    def toggle_sort(self, btn: Gtk.ToggleButton | None, value: str) -> None:
        """Set the order of the sections."""
        if btn and not btn.get_active():
            return

        if not btn:
            match value:
                case "size":
                    self.headerbar.sort_by_size_button.set_active(True)
                case "title":
                    self.headerbar.sort_by_title_button.set_active(True)
                case "native":
                    self.headerbar.sort_by_native_button.set_active(True)

        self.config.set_persistent("main", "sort_by", value)
        self.sheet_container_box.invalidate_sort()

    def toggle_fullscreen(self, to_fullscreen: bool | None = None) -> None:
        """Set the fullscreen state."""
        if to_fullscreen is self.is_fullscreen():
            return

        if to_fullscreen is None:
            to_fullscreen = not self.is_fullscreen()

        self.headerbar.fullscreen_button.set_active(to_fullscreen)
        self.headerbar_fs.fullscreen_button.set_active(to_fullscreen)

        self.ignore_search_changed = True
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

    def on_fullscreen_state_changed(self, _: Gtk.Widget, __: GObject.Parameter) -> None:
        """Hide header bar in title and show it in window instead, and vice versa."""
        if self.is_fullscreen():
            self.headerbar_fs.set_visible(True)
        else:
            self.headerbar_fs.set_visible(False)
        self.focus_search_entry()

    def on_search_entry_changed(self, search_entry: Gtk.SearchEntry) -> None:
        """Execute on change of the sheet selection dropdown."""
        if self.ignore_search_changed:
            self.ignore_search_changed = False
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

    def on_sheet_drop_down_changed(
        self, drop_down: Gtk.DropDown, _: GObject.Parameter
    ) -> None:
        """Execute on change of the sheet selection dropdown."""
        if not (selected_item := drop_down.get_selected_item()):
            return

        self.sheet_id = selected_item.get_string()
        self.populate_sheet_container()

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
                if self.dialog_is_open:
                    self.dialog_is_open = False
                else:
                    self.close()
            case Gdk.KEY_F11, _:
                self.toggle_fullscreen()
            case Gdk.KEY_f, True:
                # Focus search entry
                if self.is_fullscreen():
                    self.headerbar_fs.search_entry.grab_focus()
                else:
                    self.headerbar.search_entry.grab_focus()
            case Gdk.KEY_s, True:
                # Open sheet dropdown
                if self.is_fullscreen():
                    self.headerbar_fs.sheet_drop_down.grab_focus()
                else:
                    self.headerbar.sheet_drop_down.grab_focus()
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
        self.dialog_is_open = True
        logo = Gtk.Image.new_from_file(f"{RESOURCE_PATH}/keyhint_icon.svg")
        Gtk.AboutDialog(
            program_name="KeyHint",
            comments="Cheatsheet for keyboard shortcuts &amp; commands",
            version=__version__,
            website_label="Website",
            website="https://github.com/dynobo/keyhint",
            logo=logo.get_paintable(),
            system_information=self.get_debug_info(),
            modal=True,
            resizable=True,
            transient_for=self,
        ).show()

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

    def get_sheet_by_id(self, sheet_id: str) -> dict[str, Any]:
        return next(sheet for sheet in self.sheets if sheet["id"] == sheet_id)

    def get_sheet_id_by_active_window(self) -> str | None:
        self.wm_class, self.window_title = context.detect_active_window()

        matching_sheets = [
            h
            for h in self.sheets
            if re.search(h["match"]["regex_process"], self.wm_class, re.IGNORECASE)
            and re.search(h["match"]["regex_title"], self.window_title, re.IGNORECASE)
        ]

        if not matching_sheets:
            return None

        # First sort by secondary criterion
        matching_sheets.sort(key=lambda h: len(h["match"]["regex_title"]), reverse=True)

        # Then sort by primary criterion
        matching_sheets.sort(
            key=lambda h: len(h["match"]["regex_process"]), reverse=True
        )

        # First element is (hopefully) the best fitting sheet id
        return matching_sheets[0]["id"]

    def get_appropriate_sheet_id(self) -> str | None:
        sheet_id = None

        # If sheet-id was provided by option, use that one:
        if "cheatsheet" in self.cli_args:
            sheet_id = self.cli_args["cheatsheet"]
            logger.debug("Using provided sheet-id: %s.", sheet_id)

        # Else try to find cheatsheet for active window
        if not sheet_id:
            sheet_id = self.get_sheet_id_by_active_window()
            logger.debug("Found matching sheet: %s.", sheet_id)

        # First fallback to cli provided default
        if (not sheet_id) and ("default-cheatsheet" in self.cli_args):
            sheet_id = self.cli_args["default-cheatsheet"]
            logger.debug("Using provided fallback sheet-id: %s.", sheet_id)

        # Last fallback to first entry in list
        if not sheet_id:
            model = self.sheet_drop_down.get_model()
            sheet_id = model.get_item(0).get_string()
            logger.debug("No matching or fallback sheet found. Using first sheet.")

        return sheet_id

    def load_css(self) -> None:
        """Load custom global CSS."""
        css_path = f"{RESOURCE_PATH}/style.css"
        provider = Gtk.CssProvider()
        provider.load_from_path(css_path)
        Gtk.StyleContext().add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

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

    def create_list_item_factory(self, callback: Callable) -> Gtk.SignalListItemFactory:
        factory = Gtk.SignalListItemFactory()
        factory.connect("bind", callback)
        return factory

    def create_column_view_column(
        self,
        title: str,
        factory: Gtk.SignalListItemFactory,
        fixed_width: float | None = None,
    ) -> Gtk.ColumnViewColumn:
        column = Gtk.ColumnViewColumn(title=title, factory=factory)
        if fixed_width:
            column.set_fixed_width(int(fixed_width))
        return column

    def create_column_view(
        self,
        selection: Gtk.SelectionModel,
        shortcut_column: Gtk.ColumnViewColumn,
        label_column: Gtk.ColumnViewColumn,
    ) -> Gtk.ColumnView:
        column_view = Gtk.ColumnView()
        column_view.get_style_context().add_class("bindings-section")
        column_view.set_hexpand(True)
        column_view.set_model(selection)
        column_view.append_column(shortcut_column)
        column_view.append_column(label_column)
        return column_view

    def populate_sheet_container(self) -> None:
        if hasattr(self.sheet_container_box, "remove_all") and False:
            # Only available in GTK 4.12+
            self.sheet_container_box.remove_all()
        else:
            while child := self.sheet_container_box.get_first_child():
                self.sheet_container_box.remove(child)

        sheet_id = self.headerbar.sheet_drop_down.get_selected_item().get_string()
        sheet = self.get_sheet_by_id(sheet_id)

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
        shortcut_column = self.create_column_view_column(
            "", self.shortcut_column_factory, shortcut_column_width
        )
        label_column = self.create_column_view_column(
            section, self.label_column_factory
        )
        column_view = self.create_column_view(selection, shortcut_column, label_column)

        section_child = Gtk.FlowBoxChild()
        section_child.set_vexpand(False)
        section_child.set_child(column_view)
        return section_child

    def get_debug_info(self) -> str:
        text = "Active Window:\n"
        text += f"\ttitle: {self.window_title}\n"
        text += f"\twmclass: {self.wm_class}\n"
        text += "\nSelected Cheatsheet:\n"
        text += f"\tID: {self.sheet_id}\n"
        if sheet := self.get_sheet_by_id(self.sheet_id):
            text += f"\tregex_process: {sheet['match']['regex_process']}\n"
            text += f"\tregex_title: {sheet['match']['regex_title']}\n"
            text += f"\tsource: {sheet['source']}\n"
        else:
            text += "No cheatsheet for this ID found!"
        return text
