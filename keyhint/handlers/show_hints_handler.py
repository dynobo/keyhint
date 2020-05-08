"""Handler responsible for attaching screenshot(s) to session data."""

# default
from tkinter import Frame, Label, Tk  # noqa

# Own
from ..data_model import HintsData
from .abstract_handler import AbstractHandler


class HintsWindow(Frame):
    """Show window with hints."""

    current_row: int
    current_col: int
    style: dict = {}

    def __init__(self, master: Tk, data: HintsData):
        """Receive tk and data to show.

        Arguments:
            master {Tk} -- Tk root window
            data {Hintsdata} -- central data object

        """
        Frame.__init__(self, master)
        self.data = data

        self.pack(side="top", fill="both", expand="yes")
        # get screen width and height
        # ws = master.winfo_screenwidth()
        # hs = master.winfo_screenheight()

        # self.master.geometry("%dx%d+%d+%d" % (w, h, x, y))
        self.lift()

        self._set_style()
        self._create_layout()

    def _set_style(self):
        """Configure style for window."""
        font_family = self.data.style_font_family
        font_size = self.data.style_font_base_size

        if self.data.style_theme.lower() == "dark":
            self.style["bg_color"] = "black"
            self.style["text_color"] = "white"
        else:
            self.style["bg_color"] = "white"
            self.style["text_color"] = "black"

        self.config(bg=self.style["bg_color"])

        self.style["title_format"] = {
            "font": (font_family, int(font_size * 1.4),),
            "fg": self.style["text_color"],
            "bg": self.style["bg_color"],
            "justify": "center",
        }
        self.style["group_title_format"] = {
            "font": (font_family, int(font_size * 1.125),),
            "bg": self.style["bg_color"],
            "fg": self.style["text_color"],
            "justify": "left",
        }
        self.style["text_format"] = {
            "font": (font_family, int(font_size * 0.85),),
            "bg": self.style["bg_color"],
            "fg": self.style["text_color"],
            "justify": "left",
        }
        self.style["bold_text_format"] = {
            "font": (font_family, int(font_size * 0.85), "bold",),
            "bg": self.style["bg_color"],
            "fg": self.style["text_color"],
            "justify": "left",
        }

    def _create_title_row(self, text, max_cols):
        title = Label(self, text=text)
        title.config(**self.style["title_format"])
        title.grid(column=0, columnspan=max_cols, row=0)
        print(max_cols)

    def _create_group_title_row(self, column, group):
        group_title = Label(column, text=group)
        group_title.grid(column=0, columnspan=2, pady=(15, 5), padx=0, sticky="W")
        group_title.config(**self.style["group_title_format"])

    def _create_key_desc_row(self, col, key, desc):
        key = Label(col, text=key)
        key.grid(column=0, row=self.current_row, sticky="W", padx=15, pady=2)
        key.config(**self.style["bold_text_format"])

        desc = Label(col, text=desc)
        desc.grid(column=1, row=self.current_row, sticky="W", padx=15, pady=2)
        desc.config(**self.style["text_format"])

    def _create_new_column(self):
        column = Frame(self, bg=self.style["bg_color"])
        column.grid(row=1, column=self.current_col, sticky="nsew", padx=15, pady=15)
        self.current_col += 1
        self.current_row = 1
        return column

    def _create_layout(self):
        self.current_row = 1  # Row 0 is reserved for Title
        self.current_col = 0

        column = self._create_new_column()

        for group, hints in self.data.hints.items():

            # Start next column, if less than 4 rows left
            if self.current_row > self.data.style_max_rows - 4:
                column = self._create_new_column()
            # Append group title
            self._create_group_title_row(column, group)
            self.current_row += 1

            # Append keys
            for key, desc in hints.items():
                # If column is full switch to next column
                if self.current_row >= self.data.style_max_rows:
                    column = self._create_new_column()
                self._create_key_desc_row(column, key, desc)
                self.current_row += 1

        self._create_title_row(
            f"{self.data.app_name} ({self.data.context_name})", self.current_col
        )


class ShowHintsHandler(AbstractHandler):
    """Display hints in own window."""

    # Container for data object
    data: HintsData

    def handle(self, data: HintsData) -> HintsData:
        """Take multimon screenshots and add those images to session data.

        Arguments
            AbstractHandler {class} -- self
            data {NormcapData} -- NormCap's

        Returns
            NormcapData -- Enriched NormCap's session data

        """
        self._logger.info("Displaying hints...")

        self.data = data

        root = Tk(className="keyhint")
        root.title("keyhint")

        _ = HintsWindow(root, data)

        def on_event(_):
            root.destroy()

        root.bind("<FocusOut>", on_event)
        root.bind_all("<Key>", on_event)

        root.wait_visibility(root)
        root.attributes("-alpha", 0.6)

        root.mainloop()

        if self._next_handler:
            return super().handle(data)
        return data
