"""Utility functions to format and view bindings (shortcut + label)."""

import logging

from gi.repository import GLib, GObject, Gtk

logger = logging.getLogger("keyhint")


def replace_keys(text: str) -> str:
    """Replace certain key names by corresponding unicode symbol.

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
    """Style the key as keycap or as divider (between two keycaps).

    Args:
        text: A single partition of a shortcut.

    Returns:
        (Unescaped) key of the shortcut, css classes to use.
    """
    key_dividers = ["+", "/", "&", "or"]
    if text in key_dividers:
        css_classes = ["dim-label"]
    else:
        text = text.replace("\\/", "/")
        text = text.replace("\\+", "+")
        text = text.replace("\\&", "&")
        css_classes = ["keycap"]
    return text, css_classes


class Row(GObject.Object):
    shortcut: str
    label: str
    filter_text: str

    def __init__(self, shortcut: str, label: str, section: str) -> None:
        super().__init__()
        self.shortcut = shortcut
        self.label = label
        self.filter_text = f"{shortcut} {label} {section}"


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
