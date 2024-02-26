"""Various utility functions."""

import logging
from pathlib import Path

from gi.repository import Gdk, GLib, Gtk

logger = logging.getLogger("keyhint")


def replace_keys(text: str) -> str:
    """Replace key names by corresponding unicode symbol.

    Args:
        text (str): Text with key names.

    Returns:
        str: Text where some key names have been replaced by unicode symbol.
    """
    if text in {"PageUp", "PageDown"}:
        text = text.replace("Page", "Page ")

    text = text.replace("Down", "↓")
    text = text.replace("Up", "↑")
    text = text.replace("Left", "←")
    text = text.replace("Right", "→")
    text = text.replace("Direction", "←↓↑→")
    text = text.replace("PlusMinus", "±")
    text = text.replace("Plus", "＋")  # noqa: RUF001
    text = text.replace("Minus", "−")  # noqa: RUF001
    text = text.replace("Slash", "/")

    return text  # noqa: RET504


def style_key(text: str) -> tuple[str, list[str]]:
    if text in ["+", "/", "&", "or"]:
        css_classes = ["dim-label"]
    else:
        text = text.replace("\\/", "/")
        text = text.replace("\\+", "+")
        text = text.replace("\\&", "&")
        css_classes = ["keycap"]
    return text, css_classes


def create_shortcut(text: str) -> Gtk.Box:
    box = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END
    )
    keys = [text.replace("`", "")] if text.startswith("`") else text.split()
    for k in keys:
        key = replace_keys(text=k.strip())
        key, css_classes = style_key(text=key)
        label = Gtk.Label()
        label.set_css_classes(css_classes)
        label.set_markup(f"{GLib.markup_escape_text(key)}")
        box.append(label)
    return box


def create_column_view_column(
    title: str,
    factory: Gtk.SignalListItemFactory,
    fixed_width: float | None = None,
) -> Gtk.ColumnViewColumn:
    column = Gtk.ColumnViewColumn(title=title, factory=factory)
    if fixed_width:
        column.set_fixed_width(int(fixed_width))
    return column


def create_column_view(
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


def create_css_provider(
    display: Gdk.Display, css: str | None = None
) -> Gtk.CssProvider:
    """Load custom global CSS."""
    provider = Gtk.CssProvider()
    Gtk.StyleContext().add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
    )
    if css and Path(css).exists():
        provider.load_from_path(css)
    return provider
