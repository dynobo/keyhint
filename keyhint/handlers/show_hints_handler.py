"""Handler responsible for attaching screenshot(s) to session data."""

# extra
import PySimpleGUI as sg  # type: ignore

# Own
from ..data_model import HintsData
from .abstract_handler import AbstractHandler


class ShowHintsHandler(AbstractHandler):
    """Display hints in own window."""

    # Container for data object
    data: HintsData

    # Container for style info
    style: dict = {}

    # pySimplyGUI Window object
    window: sg.Window

    # Will contain the elements to be layed ou in window
    layout: list = []

    def handle(self, data: HintsData) -> HintsData:
        """Take multimon screenshots and add those images to session data.

        Arguments
            AbstractHandler {class} -- self
            data {NormcapData} -- NormCap's session data

        Returns
            NormcapData -- Enriched NormCap's session data

        """
        self._logger.info("Displaying hints...")

        self.data = data

        self._set_style()
        self.show()

        if self._next_handler:
            return super().handle(data)
        return data

    def _set_style(self):
        """Configure style for window."""
        if self.data.style_theme.lower() == "dark":
            sg.theme("Black")
            self.style["bg_color"] = "black"
            self.style["text_color"] = "white"
        else:
            sg.theme("Default")
            self.style["bg_color"] = "white"
            self.style["text_color"] = "black"

        sg.theme_background_color(self.style["bg_color"])
        sg.theme_element_background_color(self.style["bg_color"])
        sg.theme_text_color(self.style["text_color"])

        self.style["title_format"] = {
            "font": (
                self.data.style_font_family,
                int(self.data.style_font_base_size * 1.4),
            ),
            "background_color": self.style["bg_color"],
        }
        self.style["group_title_format"] = {
            "font": (
                self.data.style_font_family,
                int(self.data.style_font_base_size * 1.125),
            ),
            "background_color": self.style["bg_color"],
            "pad": ((0, 0), (int(self.data.style_font_base_size * 0.75), 0)),
        }
        self.style["text_format"] = {
            "font": (
                self.data.style_font_family,
                int(self.data.style_font_base_size * 0.85),
            ),
            "background_color": self.style["bg_color"],
        }
        self.style["bold_text_format"] = {
            "font": (
                self.data.style_font_family,
                int(self.data.style_font_base_size * 0.85),
                "bold",
            ),
            "background_color": self.style["bg_color"],
        }

    def show(self):
        """Create layout of elements and display them in window."""
        self._create_layout()
        self._show_window()

    def _show_window(self):
        """Display the window, close on Esc or any other key."""
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
            event, _ = self.window.read()
            if event in ["Escape:9"]:
                break
        self.window.close()

    def _create_keys_layout(self):
        layout = []

        temp_column = []
        column_counter = 0

        # Loop over hint groups
        for group, hints in self.data.hints.items():

            # Start fresh column, if less than 4 rows left
            if column_counter > self.data.style_max_rows - 4:
                layout.append(sg.Column(temp_column))
                temp_column = []
                column_counter = 0

            # Append group title
            temp_column.append([sg.Text(group, **self.style["group_title_format"])])
            column_counter += 1

            # Append keys
            left, right = [], []
            for key, desc in hints.items():

                # If row is full, append what's in column and switch to next column
                if column_counter >= self.data.style_max_rows:
                    temp_column.append([sg.Column(left), sg.Column(right)])
                    layout.append(sg.Column(temp_column))
                    temp_column, left, right = [], [], []
                    column_counter = 0

                left.append([sg.Text(key, **self.style["bold_text_format"])])
                right.append([sg.Text(desc, **self.style["text_format"])])
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
            sg.Text(
                title, pad=(0, 0), justification="right", **self.style["title_format"]
            ),
        ]
        return layout
