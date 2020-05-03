"""Handler responsible for attaching screenshot(s) to session data."""
# Standard
import os
import subprocess
import re

# extra
import PySimpleGUI as sg

# Own
from ..data_model import HintsData
from .abstract_handler import AbstractHandler


class ShowHintsHandler(AbstractHandler):
    def handle(self, data: HintsData) -> HintsData:
        """Take multimon screenshots and add those images to session data.

        Arguments:
            AbstractHandler {class} -- self
            data {NormcapData} -- NormCap's session data

        Returns:
            NormcapData -- Enriched NormCap's session data
        """
        self._logger.info("Displaying hints...")

        self.data = data
        self._set_style()
        self.show()

        if self._next_handler:
            return super().handle(data)
        else:
            return data

    def _set_style(self):
        # Add dunmy data in case app or context not found
        if not self.data.app_name:
            self.data.app_name = {
                "name": "Application unknown!",
            }

        if not self.data.shortcuts:
            self.data.context_name = "No shortcuts found"
            self.data.shortcuts = {
                "Properties of active Window": {
                    "wm_class": self.wm_class,
                    "wm_name": self.wm_name,
                },
            }

        # Theme & Styling
        # ==============================================
        if self.data.style_theme.lower() == "dark":
            sg.theme("Black")
            self.bg_color = "black"
            self.text_color = "white"
        else:
            sg.theme("Default")
            self.bg_color = "white"
            self.text_color = "black"

        sg.theme_background_color(self.bg_color)
        sg.theme_element_background_color(self.bg_color)
        sg.theme_text_color(self.text_color)

        self.titel_format = {
            "font": (
                self.data.style_font_family,
                int(self.data.style_font_base_size * 1.4),
            ),
            "background_color": self.bg_color,
        }
        self.group_title_format = {
            "font": (
                self.data.style_font_family,
                int(self.data.style_font_base_size * 1.125),
            ),
            "background_color": self.bg_color,
            "pad": ((0, 0), (int(self.data.style_font_base_size * 0.75), 0)),
        }
        self.text_format = {
            "font": (
                self.data.style_font_family,
                int(self.data.style_font_base_size * 0.85),
            ),
            "background_color": self.bg_color,
        }
        self.bold_text_format = {
            "font": (
                self.data.style_font_family,
                int(self.data.style_font_base_size * 0.85),
                "bold",
            ),
            "background_color": self.bg_color,
        }

    def show(self):
        self._create_layout()
        self._show_window()

    def _show_window(self):
        self.window = sg.Window(
            "keyhint",
            self.layout,
            return_keyboard_events=True,
            keep_on_top=True,
            no_titlebar=True,
            alpha_channel=self.data.style_alpha,
            grab_anywhere=True,
            finalize=True,
        )
        while True:
            event, values = self.window.read()
            if event in ["Escape:9"]:
                break
        self.window.close()

    def _create_keys_layout(self):
        layout = []

        temp_column = []
        column_counter = 0

        # Loop over shortcut groups
        for group, shortcuts in self.data.shortcuts.items():

            # Start fresh column, if less than 4 rows left
            if column_counter > self.data.style_max_rows - 4:
                layout.append(sg.Column(temp_column))
                temp_column = []
                column_counter = 0

            # Append group title
            temp_column.append([sg.Text(group, **self.group_title_format)])
            column_counter += 1

            # Append keys
            left, right = [], []
            for key, desc in shortcuts.items():

                # If row is full, append what's in column and switch to next column
                if column_counter >= self.data.style_max_rows:
                    temp_column.append([sg.Column(left), sg.Column(right)])
                    layout.append(sg.Column(temp_column))
                    temp_column, left, right = [], [], []
                    column_counter = 0

                left.append([sg.Text(key, **self.bold_text_format)])
                right.append([sg.Text(desc, **self.text_format)])
                column_counter += 1

            temp_column.append([sg.Column(left), sg.Column(right)])

        layout.append(sg.Column(temp_column))

        return layout

    def _create_layout(self):
        self.layout = []

        layout_title = self._create_layout_title()
        self.layout.append(layout_title)

        layout_keys = self._create_keys_layout()
        self.layout.append(layout_keys)

    def _create_layout_title(self):
        title = self.data.app_name + " (" + self.data.context_name + ")"
        layout = [
            sg.Text(title, pad=(0, 0), justification="right", **self.titel_format),
        ]
        return layout
