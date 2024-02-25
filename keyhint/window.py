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

import keyhint

logger = logging.getLogger(__name__)

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
    scroll_vertical_button = Gtk.Template.Child()
    scroll_horizontal_button = Gtk.Template.Child()
    zoom_spin_button = Gtk.Template.Child()
    fallback_sheet_entry: Gtk.Entry = Gtk.Template.Child()

    def __init__(self, visible: bool = True, decoration: str | None = None) -> None:
        super().__init__()
        self.set_visible(visible)
        if decoration:
            self.adwheaderbar.set_decoration_layout(decoration)


@Gtk.Template(filename=f"{RESOURCE_PATH}/window.ui")
class KeyhintWindow(Gtk.ApplicationWindow):
    """Handler for main ApplicationWindow."""

    __gtype_name__ = "main_window"

    sheets: list[dict] = keyhint.sheets.load_sheets()
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
        logger.debug("Loaded %s cheatsheets.", len(self.sheets))

        self.cli_args = cli_args
        self.config = keyhint.config.load()

        self.load_css()
        self.set_icon_name("keyhint")

        # Add normal header bar
        self.headerbar = HeaderBar()
        self.set_titlebar(self.headerbar)

        # Add second header bar which is only visible in fullscreen mode
        self.headerbar_fs = HeaderBar(decoration=":minimize,close", visible=False)
        self.container.prepend(self.headerbar_fs)

        # Set up the controls
        self.init_signals()
        self.init_actions()
        self.init_binds()
        self.init_sheet_drop_down()
        self.init_search_entry()
        self.init_event_controller_key()

        # Apply loaded configuration
        self.toggle_orientation(self.config["main"].get("orientation", "horizontal"))
        self.toggle_fullscreen(self.config["main"].getboolean("fullscreen", False))

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

        # Sheets filter
        self.sheet_container_box.set_filter_func(self.filter_sections)

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

    def on_sheet_drop_down_changed(
        self, drop_down: Gtk.DropDown, _: GObject.Parameter
    ) -> None:
        """Execute on change of the sheet selection dropdown."""
        if not (selected_item := drop_down.get_selected_item()):
            return

        self.sheet_id = selected_item.get_string()
        self.populate_sheet_container()

    def toggle_orientation(self, orientation: str | None = None) -> None:
        """Set the orientation of the sheet container."""
        if not orientation:
            orientation = str(self.sheet_container_box.get_orientation().value_nick)

        # The used GTK orientation is the opposite of the config value, which follows
        # the naming from user perspective!
        gtk_orientation = (
            Gtk.Orientation.VERTICAL
            if orientation == "horizontal"
            else Gtk.Orientation.HORIZONTAL
        )
        self.sheet_container_box.set_orientation(gtk_orientation)
        self.config.set_persistent("main", "orientation", orientation)

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

    def on_fullscreen_state_changed(self, _: Gtk.Widget, __: GObject.Parameter) -> None:
        """Hide header bar in title and show it in window instead, and vice versa."""
        if self.is_fullscreen():
            self.headerbar_fs.set_visible(True)
        else:
            self.headerbar_fs.set_visible(False)
        self.focus_search_entry()

    def focus_search_entry(self) -> None:
        """Focus search entry depending on state."""
        if self.is_fullscreen():
            self.headerbar_fs.search_entry.grab_focus()
            self.headerbar_fs.search_entry.set_position(-1)
        else:
            self.headerbar.search_entry.grab_focus()
            self.headerbar.search_entry.set_position(-1)

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

    def on_key_pressed(
        self,
        evk: Gtk.EventControllerKey,
        keycode,  # noqa: ANN001
        keyval,  # noqa: ANN001
        modifier,  # noqa: ANN001
    ) -> None:
        match keycode:
            case Gdk.KEY_Escape:
                # If the dialog is open, that one is closed. Otherwise close the window
                if self.dialog_is_open:
                    self.dialog_is_open = False
                else:
                    self.close()
            case Gdk.KEY_F11:
                self.toggle_fullscreen()
            case Gdk.KEY_f:
                if modifier == Gdk.ModifierType.CONTROL_MASK:
                    # Focus search entry
                    if self.is_fullscreen():
                        self.search_entry_fs.grab_focus()
                    else:
                        self.search_entry.grab_focus()
            case Gdk.KEY_s:
                if modifier == Gdk.ModifierType.CONTROL_MASK:
                    # Open sheet dropdown
                    self.sheet_drop_down.grab_focus()
            case Gdk.KEY_Up | Gdk.KEY_k:
                self.scroll(to_start=True, by_page=False)
            case Gdk.KEY_Down | Gdk.KEY_j:
                self.scroll(to_start=False, by_page=False)
            case Gdk.KEY_Left | Gdk.KEY_h:
                self.scroll(to_start=True, by_page=False)
            case Gdk.KEY_Right | Gdk.KEY_l:
                self.scroll(to_start=False, by_page=False)
            case Gdk.KEY_Page_Up:
                self.scroll(to_start=True, by_page=True)
            case Gdk.KEY_Page_Down:
                self.scroll(to_start=False, by_page=True)

    def on_about_action(self, _: Gio.SimpleAction, __: None) -> None:
        """Execute on click "about" in application menu."""
        self.dialog_is_open = True
        logo = Gtk.Image.new_from_file(f"{RESOURCE_PATH}/keyhint_icon.svg")
        Gtk.AboutDialog(
            program_name="KeyHint",
            comments="Cheatsheet for keyboard shortcuts &amp; commands",
            version=keyhint.__version__,
            website_label="Website",
            website="https://github.com/dynobo/keyhint",
            logo=logo.get_paintable(),
            system_information=self.get_debug_info(),
            modal=True,
            resizable=True,
            transient_for=self,
        ).show()

    def filter_sections(self, child: Gtk.Widget) -> bool:
        """Filter binding sections based on the search entry text."""
        # If no text, show all sections
        if not self.search_text:
            return True

        # If text, show only sections with 1 or more visible bindings
        column_view = child.get_child()
        selection = column_view.get_model()
        filter_model = selection.get_model()
        return filter_model.get_n_items() > 0

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

    def get_sheet_by_id(self, sheet_id: str) -> dict[str, Any]:
        return next(sheet for sheet in self.sheets if sheet["id"] == sheet_id)

    def get_sheet_id_by_active_window(self) -> str | None:
        self.wm_class, self.window_title = keyhint.context.detect_active_window()

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
            logger.debug("Using provided sheet-id: %s", sheet_id)

        # Else try to find cheatsheet for active window
        if not sheet_id:
            sheet_id = self.get_sheet_id_by_active_window()
            logger.debug("Found matching sheets %s", sheet_id)

        # First fallback to cli provided default
        if (not sheet_id) and ("default-cheatsheet" in self.cli_args):
            sheet_id = self.cli_args["default-cheatsheet"]
            logger.debug("Using provided default sheet-id: %s", sheet_id)

        # Last fallback to first entry in list
        if not sheet_id:
            model = self.sheet_drop_down.get_model()
            sheet_id = model.get_item(0).get_string()
            logger.debug("No matching sheet found. Using first sheet in list.")

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
        shortcut = keyhint.utils.create_shortcut(item.get_item().shortcut)
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
            child = keyhint.utils.create_section_title(label)
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
        fixed_width: int | None = None,
    ) -> Gtk.ColumnViewColumn:
        column = Gtk.ColumnViewColumn(title=title, factory=factory)
        if fixed_width:
            column.set_fixed_width(fixed_width)
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
        # TODO: Simplify method
        if hasattr(self.sheet_container_box, "remove_all") and False:
            # Only available in GTK 4.12+
            self.sheet_container_box.remove_all()
        else:
            while child := self.sheet_container_box.get_first_child():
                self.sheet_container_box.remove(child)

        sheet_id = self.headerbar.sheet_drop_down.get_selected_item().get_string()
        sheet = self.get_sheet_by_id(sheet_id)

        shortcut_column_factory = self.create_list_item_factory(
            self.bind_shortcuts_callback
        )
        label_column_factory = self.create_list_item_factory(self.bind_labels_callback)

        self.list_view_filter = Gtk.CustomFilter.new(
            match_func=self.list_view_match_func
        )

        self.max_shortcut_width = 0

        sections = sheet["section"]
        if not self.cli_args.get("no-section-sort", False):
            # Sort sections by number of bindings to make the layout more dense
            sections = dict(
                sorted(sections.items(), key=lambda x: len(x[1]), reverse=True)
            )

        for section, bindings in sections.items():
            ls = Gio.ListStore()
            for shortcut, label in bindings.items():
                ls.append(BindingsRow(shortcut=shortcut, label=label, section=section))

            filter_list = Gtk.FilterListModel(model=ls)
            filter_list.set_filter(self.list_view_filter)

            selection = Gtk.NoSelection.new(filter_list)

            # TODO: Dynamic width based on content
            shortcut_column = self.create_column_view_column(
                "", shortcut_column_factory, 220
            )
            label_column = self.create_column_view_column(section, label_column_factory)

            column_view = self.create_column_view(
                selection, shortcut_column, label_column
            )

            section_child = Gtk.FlowBoxChild()
            section_child.set_vexpand(False)
            section_child.set_child(column_view)

            self.sheet_container_box.append(section_child)

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
