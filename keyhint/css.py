from pathlib import Path

from gi.repository import Gdk, Gtk


def create_provider(display: Gdk.Display, css: str | None = None) -> Gtk.CssProvider:
    """Load custom global CSS."""
    provider = Gtk.CssProvider()
    Gtk.StyleContext().add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
    )
    if css and Path(css).exists():
        provider.load_from_path(css)
    return provider
