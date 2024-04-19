from pathlib import Path

from gi.repository import Gdk, Gtk


def new_provider(display: Gdk.Display, css_file: Path | None = None) -> Gtk.CssProvider:
    """Create a new css provider which applies globally.

    Args:
        display: Target Gtk.Display.
        css_file: Path to file with css rules to be loaded. If None, an empty css
            provider is created.

    Returns:
        css provider which rules apply to the whole application.
    """
    provider = Gtk.CssProvider()
    Gtk.StyleContext().add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
    )
    if css_file and css_file.exists():
        provider.load_from_path(str(css_file.resolve()))
    return provider
