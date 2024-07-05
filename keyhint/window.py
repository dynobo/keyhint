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

TODO: Create Flatpak
"""

import logging
import platform
import subprocess
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar, cast

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from keyhint import __version__, binding, config, context, css, headerbar, sheets

logger = logging.getLogger("keyhint")

RESOURCE_PATH = Path(__file__).parent / "resources"

TKeyhintWindow = TypeVar("TKeyhintWindow", bound="KeyhintWindow")
TActionCallback = Callable[[TKeyhintWindow, Gio.SimpleAction, GLib.Variant], None]


def check_state(func: TActionCallback) -> TActionCallback:
    """Decorator to only execute a function if the action state really changed."""

    def wrapper(cls: Gtk.Widget, action: Gio.SimpleAction, state: GLib.Variant) -> None:
        if action.get_state_type() and action.get_state() == state:
            return None

        if state:
            action.set_state(state)

        return func(cls, action, state)

    return wrapper


@Gtk.Template(filename=f"{RESOURCE_PATH}/window.ui")
class KeyhintWindow(Gtk.ApplicationWindow):
    """The main UI for Keyhint."""

    __gtype_name__ = "main_window"

    overlay = cast(Adw.ToastOverlay, Gtk.Template.Child())
    banner_window_calls = cast(Gtk.Revealer, Gtk.Template.Child())
    banner_xprop = cast(Gtk.Revealer, Gtk.Template.Child())
    scrolled_window = cast(Gtk.ScrolledWindow, Gtk.Template.Child())
    container = cast(Gtk.Box, Gtk.Template.Child())
    sheet_container_box = cast(Gtk.FlowBox, Gtk.Template.Child())

    shortcut_column_factory = Gtk.SignalListItemFactory()
    label_column_factory = Gtk.SignalListItemFactory()

    headerbars = headerbar.HeaderBars()

    max_shortcut_width = 0

    def __init__(self, cli_args: dict) -> None:
        super().__init__()

        self.cli_args = cli_args
        self.config = config.load()
        self.sheets = sheets.load_sheets()
        self.wm_class, self.window_title = self.init_last_active_window_info()

        self.skip_search_changed: bool = False
        self.search_text: str = ""

        self.css_provider = css.new_provider(
            display=self.get_display(), css_file=RESOURCE_PATH / "style.css"
        )
        self.zoom_css_provider = css.new_provider(display=self.get_display())

        self.set_titlebar(self.headerbars.normal)
        self.container.prepend(self.headerbars.fullscreen)

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
        self.init_actions_for_banners()
        self.init_search_entry()
        self.init_key_event_controllers()

        self.focus_search_entry()

    def init_last_active_window_info(self) -> tuple[str, str]:
        """Get class and title of active window.

        Identify the OS and display server and pick the method accordingly.

        Returns:
            Tuple[str, str]: wm_class, window title
        """
        wm_class = wm_title = ""

        on_wayland = context.is_using_wayland()
        desktop_environment = context.get_desktop_environment_and_version()[0].lower()

        match (on_wayland, desktop_environment):
            case True, "gnome":
                if context.has_window_calls_extension():
                    wm_class, wm_title = context.get_active_window_via_window_calls()
                else:
                    self.banner_window_calls.set_reveal_child(True)
                    logger.error("Window Calls extension not found!")
            case True, "kde":
                wm_class, wm_title = context.get_active_window_via_kwin()
            case False, _:
                if context.has_xprop():
                    wm_class, wm_title = context.get_active_window_via_xprop()
                else:
                    self.banner_xprop.set_reveal_child(True)
                    logger.error("xprop not found!")

        logger.debug("Detected wm_class: '%s'.", wm_class)
        logger.debug("Detected window_title: '%s'.", wm_title)

        if "" in [wm_class, wm_title]:
            logger.warning("Couldn't detect active window!")

        return wm_class, wm_title

    def init_action_sort_by(self) -> None:
        action = Gio.SimpleAction.new_stateful(
            name="sort_by",
            state=GLib.Variant("s", ""),
            parameter_type=GLib.VariantType.new("s"),
        )
        action.connect("activate", self.on_change_sort)
        action.connect("change-state", self.on_change_sort)
        self.add_action(action)

        # Connect to button happens via headerbar.ui

        self.change_action_state(
            "sort_by", GLib.Variant("s", self.config["main"].get("sort_by", "size"))
        )

    def init_action_zoom(self) -> None:
        action = Gio.SimpleAction.new_stateful(
            name="zoom",
            state=GLib.Variant("i", 0),
            parameter_type=GLib.VariantType.new("i"),
        )
        action.connect("change-state", self.on_change_zoom)
        self.add_action(action)

        for bar in self.headerbars:
            bar.zoom_scale.connect(
                "value-changed",
                lambda btn: self.change_action_state(
                    "zoom", GLib.Variant("i", btn.get_value())
                ),
            )
            slider_range = bar.zoom_scale.get_adjustment()
            lower_bound = int(slider_range.get_lower())
            upper_bound = int(slider_range.get_upper())
            for i in range(lower_bound, upper_bound + 1, 25):
                bar.zoom_scale.add_mark(
                    i, Gtk.PositionType.BOTTOM, f"<small>{i}</small>"
                )

        self.change_action_state(
            "zoom", GLib.Variant("i", self.config["main"].getint("zoom", 100))
        )

    def init_action_fullscreen(self) -> None:
        action = Gio.SimpleAction.new_stateful(
            name="fullscreen",
            state=GLib.Variant("b", False),
            parameter_type=None,
        )
        action.connect("activate", self.on_change_fullscreen)
        action.connect("change-state", self.on_change_fullscreen)
        self.add_action(action)

        # Connect to button happens via headerbar.ui

        self.connect("notify::fullscreened", self.on_fullscreen_state_changed)

        self.change_action_state(
            "fullscreen",
            GLib.Variant("b", self.config["main"].getboolean("fullscreen", False)),
        )

    def init_action_orientation(self) -> None:
        action = Gio.SimpleAction.new_stateful(
            name="orientation",
            state=GLib.Variant("s", ""),
            parameter_type=GLib.VariantType.new("s"),
        )
        action.connect("activate", self.on_change_orientation)
        action.connect("change-state", self.on_change_orientation)
        self.add_action(action)

        # Connect to button happens via headerbar.ui

        self.change_action_state(
            "orientation",
            GLib.Variant("s", self.config["main"].get("orientation", "vertical")),
        )

    def init_action_fallback_sheet(self) -> None:
        action = Gio.SimpleAction.new_stateful(
            name="fallback_sheet",
            state=GLib.Variant("s", ""),
            parameter_type=GLib.VariantType.new("s"),
        )
        action.connect("change-state", self.on_set_fallback_sheet)
        self.add_action(action)

        for bar in self.headerbars:
            bar.fallback_sheet_button.connect(
                "clicked",
                lambda *args: self.change_action_state(
                    "fallback_sheet",
                    GLib.Variant("s", self.get_current_sheet_id() or "keyhint"),
                ),
            )

        self.change_action_state(
            "fallback_sheet",
            GLib.Variant(
                "s", self.config["main"].get("fallback_cheatsheet", "keyhint")
            ),
        )

    def init_action_sheet(self) -> None:
        action = Gio.SimpleAction.new_stateful(
            name="sheet",
            state=GLib.Variant("s", ""),
            parameter_type=GLib.VariantType.new("s"),
        )
        action.connect("change-state", self.on_change_sheet)
        self.add_action(action)

        for bar in self.headerbars:
            bar.sheet_dropdown.connect(
                "notify::selected-item",
                lambda btn, param: self.change_action_state(
                    "sheet", GLib.Variant("s", btn.get_selected_item().get_string())
                ),
            )

        self.change_action_state(
            "sheet", GLib.Variant("s", self.get_appropriate_sheet_id())
        )

    def init_search_entry(self) -> None:
        for bar in self.headerbars:
            self.search_changed_handler = bar.search_entry.connect(
                "search-changed", self.on_search_entry_changed
            )

    def init_actions_for_menu_entries(self) -> None:
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
        """Register actions which are triggered from toast notifications."""
        action = Gio.SimpleAction.new("create_new_sheet", None)
        action.connect("activate", self.on_create_new_sheet)
        self.add_action(action)

    def init_actions_for_banners(self) -> None:
        """Register actions which are triggered from banners."""
        action = Gio.SimpleAction.new("visit_window_calls", None)
        action.connect(
            "activate",
            lambda *args: Gio.AppInfo.launch_default_for_uri(
                "https://extensions.gnome.org/extension/4724/window-calls/"
            ),
        )
        self.add_action(action)

    def init_key_event_controllers(self) -> None:
        """Register key press handlers."""
        evk = Gtk.EventControllerKey()
        evk.connect("key-pressed", self.on_key_pressed)
        self.add_controller(evk)

        evk = Gtk.EventControllerKey()
        evk.connect("key-pressed", self.on_search_entry_key_pressed)
        self.headerbars.normal.search_entry.add_controller(evk)

        # NOTE: Reusing the same evk would lead to critical assertion error!
        evk = Gtk.EventControllerKey()
        evk.connect("key-pressed", self.on_search_entry_key_pressed)
        self.headerbars.fullscreen.search_entry.add_controller(evk)

    def init_sheet_dropdown(self) -> None:
        """Populate sheet dropdown with available sheet IDs."""
        # Use the model from normal dropdown also for the fullscreen dropdown
        model = self.headerbars.normal.sheet_dropdown.get_model()
        self.headerbars.fullscreen.sheet_dropdown.set_model(model)

        # Satisfy type checker
        if not isinstance(model, Gtk.StringList):
            raise TypeError("Sheet dropdown model is not a Gtk.StringList.")

        for sheet_id in sorted([s["id"] for s in self.sheets]):
            model.append(sheet_id)

    @property
    def active_headerbar(self) -> headerbar.HeaderBarBox:
        """Return the currently active headerbar depending on window state."""
        return (
            self.headerbars.fullscreen
            if self.is_fullscreen()
            else self.headerbars.normal
        )

    @check_state
    def on_set_fallback_sheet(
        self, action: Gio.SimpleAction, state: GLib.Variant
    ) -> None:
        """Set the sheet to use in case no matching sheet is found."""
        sheet_id = state.get_string()
        self.config.set_persistent("main", "fallback_cheatsheet", sheet_id)
        for bar in self.headerbars:
            bar.fallback_sheet_entry.set_text(sheet_id)

    @check_state
    def on_change_sheet(self, action: Gio.SimpleAction, state: GLib.Variant) -> None:
        """Get selected sheet and render it in the UI."""
        dropdown_model = self.headerbars.normal.sheet_dropdown.get_model()

        # Satisfy type checker
        if not dropdown_model:
            raise TypeError("Sheet dropdown model is not a Gtk.StringList.")

        dropdown_strings = [
            s.get_string() for s in dropdown_model if isinstance(s, Gtk.StringObject)
        ]

        sheet_id = state.get_string()
        select_idx = dropdown_strings.index(sheet_id)

        for bar in self.headerbars:
            bar.sheet_dropdown.set_selected(select_idx)

        self.show_sheet(sheet_id=sheet_id)

    @check_state
    def on_change_zoom(self, action: Gio.SimpleAction, state: GLib.Variant) -> None:
        """Set the zoom level of the sheet container via css."""
        value = state.get_int32()

        for bar in self.headerbars:
            bar.zoom_scale.set_value(value)

        css_style = f"""
                .sheet_container_box,
                .sheet_container_box .bindings-section header label {{
                    font-size: {value}%;
                }}
                """

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
        """Set the orientation or scroll direction of the sheet container."""
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
            # If state is not provided, just toggle the action's state
            to_fullscreen = not bool(action.get_state())
        action.set_state(GLib.Variant("b", to_fullscreen))

        # Set flag to temporarily ignore search entry changes (to avoid recursion)
        self.skip_search_changed = True

        for bar in self.headerbars:
            bar.search_entry.set_text(self.search_text)

        if to_fullscreen:
            self.fullscreen()
        else:
            self.unfullscreen()

        self.config.set_persistent("main", "fullscreen", to_fullscreen)

    def scroll(self, to_start: bool, by_page: bool) -> None:
        """Scroll the sheet container by a certain distance."""
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
        """Focus search entry of the active headerbar."""
        self.active_headerbar.search_entry.grab_focus()
        self.active_headerbar.search_entry.set_position(-1)

    def show_create_new_sheet_toast(self) -> None:
        """Display a toast notification to offer the creation of a new cheatsheet."""
        toast = Adw.Toast.new(f"No cheatsheet found for '{self.wm_class}'.")
        toast.set_button_label("Create new")
        toast.set_action_name("win.create_new_sheet")
        toast.set_timeout(5)
        self.overlay.add_toast(toast)

    def on_fullscreen_state_changed(self, _: Gtk.Widget, __: GObject.Parameter) -> None:
        """Toggle fullscreen header bar according to current window state."""
        if self.is_fullscreen():
            self.headerbars.fullscreen.set_visible(True)
        else:
            self.headerbars.fullscreen.set_visible(False)
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
        """Handle key press events in the search entry field.

        Note: The search itself is triggered by the 'change' event, not by 'key-pressed'
        """
        if keycode == Gdk.KEY_Escape:
            self.close()

    def on_key_pressed(
        self,
        evk: Gtk.EventControllerKey,
        keycode: int,
        keyval: int,
        modifier: Gdk.ModifierType,
    ) -> None:
        """Handle key press events in the main window."""
        ctrl_pressed = modifier == Gdk.ModifierType.CONTROL_MASK
        match keycode, ctrl_pressed:
            case Gdk.KEY_Escape, _:
                self.close()
            case Gdk.KEY_F11, _:
                self.activate_action("win.fullscreen")
            case Gdk.KEY_f, True:
                self.active_headerbar.grab_focus()
            case Gdk.KEY_s, True:
                self.active_headerbar.sheet_dropdown.grab_focus()
            case (Gdk.KEY_Up, _) | (Gdk.KEY_k, True):
                self.scroll(to_start=True, by_page=False)
            case (Gdk.KEY_Down, _) | (Gdk.KEY_j, True):
                self.scroll(to_start=False, by_page=False)
            case Gdk.KEY_Page_Up, _:
                self.scroll(to_start=True, by_page=True)
            case Gdk.KEY_Page_Down, _:
                self.scroll(to_start=False, by_page=True)

    def on_about_action(self, _: Gio.SimpleAction, __: None) -> None:
        """Show modal 'About' dialog."""
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
        """Show modal dialog with information useful for error reporting."""
        label = Gtk.Label()
        label.set_use_markup(True)
        label.set_wrap(True)
        label.set_selectable(True)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_markup(self.get_debug_info_text())
        label.set_margin_start(24)
        label.set_margin_end(24)

        def _on_copy_clicked(button: Gtk.Button) -> None:
            if display := Gdk.Display.get_default():
                clipboard = display.get_clipboard()
                clipboard.set(f"### Debug Info\n\n```\n{label.get_text().strip()}\n```")
                button.set_icon_name("object-select-symbolic")
                button.set_tooltip_text("Copied!")

        copy_button = Gtk.Button()
        copy_button.set_icon_name("edit-copy")
        copy_button.set_tooltip_text("Copy to clipboard")
        copy_button.connect("clicked", _on_copy_clicked)

        dialog = Gtk.Dialog(title="Debug Info", transient_for=self, modal=True)
        dialog.get_content_area().append(label)
        dialog.add_action_widget(copy_button, Gtk.ResponseType.NONE)
        dialog.show()

    def on_create_new_sheet(self, _: Gio.SimpleAction, __: None) -> None:
        """Create a new text file with a template for a new cheatsheet."""
        title = self.wm_class.lower().replace(" ", "")
        pad = 26 - len(title)
        template = f"""\
            id = "{title}"{" " * pad } # Unique ID, used e.g. in cheatsheet dropdown
            url = ""                          # (Optional) URL to keybinding docs

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

        # Make sure the file name is unique
        idx = 1
        while new_file.exists():
            new_file = new_file.with_name(f"{title}_{idx}.toml")
            idx += 1

        new_file.write_text(template)
        subprocess.Popen(["xdg-open", str(new_file.resolve())])  # noqa: S603, S607

    def on_open_folder_action(self, _: Gio.SimpleAction, __: None) -> None:
        """Open config folder in default file manager."""
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
        """Sort function for the sections of the cheatsheet."""
        sort_by = self.config["main"].get("sort_by", "size")

        if sort_by == "native":
            # The names use the format 'section-{INDEX}', so just sort by that
            return child_a.get_name() > child_b.get_name()

        sub_child_a = child_a.get_child()
        sub_child_b = child_b.get_child()

        # Satisfy type checker
        if not isinstance(sub_child_a, Gtk.ColumnView) or not isinstance(
            sub_child_b, Gtk.ColumnView
        ):
            raise TypeError("Child is not a ColumnView.")

        if sort_by == "size":
            # Sorts by number of bindings in the section
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
        """Determine the sheet ID based on context or configuration."""
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

        # If no sheet found, show toast to create new one...
        self.show_create_new_sheet_toast()

        # ...and use the configured fallback sheet
        if sheet_id := self.config["main"].get("fallback_cheatsheet", ""):
            logger.debug("Using provided fallback sheet-id: %s.", sheet_id)
            return sheet_id

        # If that fallback sheet also does not exist, just use the first in dropdown
        model = self.headerbars.normal.sheet_dropdown.get_model()
        item = model.get_item(0) if model else None
        sheet_id = (
            item.get_string() if isinstance(item, Gtk.StringObject) else "keyhint"
        )
        logger.debug("No matching or fallback sheet found. Using first sheet.")
        return sheet_id

    def bind_shortcuts_callback(
        self,
        _: Gtk.SignalListItemFactory,
        item,  # noqa: ANN001 # ONHOLD: Gtk.ColumnViewCell for GTK 4.12+
    ) -> None:
        row = cast(binding.Row, item.get_item())
        shortcut = binding.create_shortcut(row.shortcut)
        self.max_shortcut_width = max(
            self.max_shortcut_width,
            shortcut.get_preferred_size().natural_size.width,  # type: ignore # False Positive
        )
        item.set_child(shortcut)

    def bind_labels_callback(
        self,
        _: Gtk.SignalListItemFactory,
        item,  # noqa: ANN001  # ONHOLD: Gtk.ColumnViewCell for GTK 4.12+
    ) -> None:
        row = cast(binding.Row, item.get_item())
        if row.shortcut:
            child = Gtk.Label(label=row.label, xalign=0.0)
        else:
            # Section title
            child = Gtk.Label(xalign=0.0)
            child.set_markup(f"<b>{row.label}</b>")
        item.set_child(child)

    def bindings_match_func(self, bindings_row: binding.Row) -> bool:
        if self.search_text:
            return self.search_text.lower() in bindings_row.filter_text.lower()
        return True

    def show_sheet(self, sheet_id: str) -> None:
        """Clear sheet container and populate it with the selected sheet."""
        if hasattr(self.sheet_container_box, "remove_all"):
            # Only available in GTK 4.12+
            self.sheet_container_box.remove_all()
        else:
            # ONHOLD: Remove once GTK 4.12+ is required
            while child := self.sheet_container_box.get_first_child():
                self.sheet_container_box.remove(child)

        self.max_shortcut_width = 0

        sheet = sheets.get_sheet_by_id(sheets=self.sheets, sheet_id=sheet_id)
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
            ls.append(binding.Row(shortcut=shortcut, label=label, section=section))

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
        """Compile information which is useful for error analysis."""
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
        desktop_environment = " ".join(context.get_desktop_environment_and_version())

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

            <big>System Information</big>

            <span foreground='#FF2E88'>Platform:</span> {platform.platform()}
            <span foreground='#FF2E88'>Desktop Environment:</span> {desktop_environment}
            <span foreground='#FF2E88'>Wayland:</span> {context.is_using_wayland()}
            <span foreground='#FF2E88'>Python:</span> {platform.python_version()}
            <span foreground='#FF2E88'>Keyhint:</span> v{__version__}
            <span foreground='#FF2E88'>Flatpak:</span> {context.is_flatpak_package()}"""
        )
