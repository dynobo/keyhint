from collections.abc import Iterator
from pathlib import Path
from typing import cast

from gi.repository import Gtk

RESOURCE_PATH = Path(__file__).parent / "resources"


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


class HeaderBars:
    """Utility class for easier accessing the two header bars.

    The 'normal' header bar is used as application title bar. It is shown in the normal
    window mode, and automatically hidden in fullscreen mode (by design of GTK).

    The 'fullscreen' header bar is added as a widget to the window content. Its
    visibility needs to be toggled depending on window state.
    """

    normal = HeaderBarBox()
    fullscreen = HeaderBarBox(for_fullscreen=True)

    def __iter__(self) -> Iterator[HeaderBarBox]:
        yield from (self.normal, self.fullscreen)
