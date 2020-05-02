# standard
import logging
from typing import List

# extra
import PySimpleGUI as sg


class Display:
    def __init__(
        self,
        title: str = "Unknown",
        keys: dict = None,
        theme: str = "Black",
        font_family: str = None,
        font_size: int = 14,
        beautify: bool = False,
        bg_color: str = None,
        text_color: str = None,
    ):
        self.logger = logging.getLogger(__name__)

        self.title = title
        self.keys = keys
        sg.theme(theme)
        sg.theme_background_color(bg_color)
        sg.theme_text_color(text_color)

        self.beautify = beautify
        self.title_font = (font_family, int(font_size * 1.25))
        self.heading_font = (font_family, int(font_size * 1.125))
        self.heading_pad = ((0, 0), (int(font_size * 0.75), 0))
        self.keys_font = (font_family, int(font_size * 0.85), "bold")
        self.keys_desc_font = (font_family, int(font_size * 0.85))

    def show(self):
        self._create_layout(self.keys)
        self._show_window(self.keys["context"])

    def _show_window(self, title: str):
        self.window = sg.Window(
            title,
            self.layout,
            return_keyboard_events=True,
            keep_on_top=True,
            no_titlebar=True,
            alpha_channel=0.8,
            grab_anywhere=True,
            finalize=True,
        )
        while True:
            event, values = self.window.read()
            if event in ["Escape:9"]:
                break
            else:
                self.logger.debug("Event detected: '%s'", event)
        self.window.close()

    def _create_layout(self, keys: dict):
        self.layout = []

        # self.layout.append(
        #     [
        #         sg.Text(self.title, font=self.title_font, pad=(0, 0)),
        #         sg.Text(keys["context"], font=self.title_font),
        #     ]
        # )

        self.group_counter = -1
        for group, shortcuts in keys["shortcuts"].items():
            self.group_counter += 1
            layout_heading = self._create_layout_heading(group)
            layout_keys = self._create_layout_keys(shortcuts)

            self.layout.append(layout_heading)
            self.layout.append(layout_keys)

    def _create_layout_heading(self, text: str) -> List[sg.Text]:
        if self.group_counter == 0:
            pad = (0, 0)
        else:
            pad = self.heading_pad
        return [sg.Text(text, font=self.heading_font, pad=pad)]

    def _create_layout_keys(self, shortcuts: dict) -> List[sg.Column]:
        left = []
        right = []

        for key, desc in shortcuts.items():
            if self.beautify:
                key = self._beautify_keys(key)
            left.append([sg.Text(key, font=self.keys_font)])
            right.append([sg.Text(desc, font=self.keys_desc_font)])

        col_left = sg.Column(left, justification="left")
        col_right = sg.Column(right, justification="left")

        return [col_left, col_right]

    def _beautify_keys(self, text: str) -> str:
        text = text.replace("up", "↑")
        text = text.replace("down", "↓")
        text = text.replace("left", "←")
        text = text.replace("right", "→")
        text = text.replace("enter", "↵")
        text = text.replace("shift", "⇧")
        text = text.replace("super", "🐧")
        return text


# Text(text="",
#     size=(None, None),
#     auto_size_text=None,
#     click_sgubmits=False,
#     enable_events=False,
#     relief=None,
#     font=None,
#     text_color=None,
#     background_color=None,
#     border_width=None,
#     justification=None,
#     pad=None,
#     key=None,
#     right_click_menu=None,
#     tooltip=None,
#     visible=True,
#     metadata=None)


# Column(layout,
#     background_color=None,
#     size=(None, None),
#     pad=None,
#     scrollable=False,
#     vertical_scroll_only=False,
#     right_click_menu=None,
#     key=None,
#     visible=True,
#     justification="left",
#     element_justification="left",
#     metadata=None)
