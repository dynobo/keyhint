"""Various utility functions."""

import logging

from gi.repository import GLib, Gtk

logger = logging.getLogger(__name__)


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
    if text in ["+", "/", "&"]:
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


def create_section_title(text: str) -> Gtk.Label:
    label = Gtk.Label(xalign=0.0)
    label.set_markup(f"<b>{text}</b>")
    return label
