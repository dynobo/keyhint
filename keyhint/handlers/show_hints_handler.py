"""Handler responsible for attaching screenshot(s) to session data."""

# default
from tkinter import Tk, font, Text  # noqa import Label, Tk, Text, font  # noqa
from tkinter.ttk import Frame, Label, Style
import time
import logging

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

        Args:
            master (Tk): Root window object
            data (HintsData): Central data object
        """
        self._logger = logging.getLogger(self.__class__.__name__)
        Frame.__init__(self, master)
        self.data = data

        self.pack(side="top", fill="both", expand="yes")
        self.lift()

        self._logger.info(f"{time.time()} - Style ")
        self._set_style()

        self._logger.info(f"{time.time()} - Layout")
        self._create_layout()

        self._logger.info(f"{time.time()} - Window")
        self._set_window_style()

        self._logger.info(f"{time.time()} - Done")

    def _set_style(self):
        """Configure style for window."""
        style: dict = self.data.config["style"]

        # Fallback to defaults, if missing
        font_family_name = style.get("font_family", "")
        font_base_size = style.get("font_base_size", 16)
        background_color = style.get("background_color", "black")
        title_color = style.get("title_color", "white")
        group_title_color = style.get("group_title_color", "white")
        description_color = style.get("description_color", "white")
        keys_color = style.get("keys_color", "white")
        statusbar_color = style.get("statusbar_color", "white")

        # Window Background
        self.style["background_color"] = background_color
        font_family = font.nametofont("TkDefaultFont").copy()

        style = Style()
        style.configure(
            "title.TLabel",
            foreground=title_color,
            font=(font_family, int(font_base_size * 1.5)),
        )
        style.configure(
            "groupTitle.TLabel",
            foreground=group_title_color,
            font=(font_family, int(font_base_size * 1.125)),
        )
        style.configure(
            "keys.TLabel",
            foreground=keys_color,
            font=(font_family, int(font_base_size)),
        )
        style.configure(
            "desc.TLabel",
            foreground=description_color,
            font=(font_family, int(font_base_size)),
        )
        style.configure(
            "statusbar.TLabel",
            foreground=statusbar_color,
            font=(font_family, int(font_base_size * 0.8)),
        )

    def _create_title_row(self, text, max_cols):
        title = Label(self, text=text, style="title.TLabel")
        title.grid(column=0, columnspan=max_cols, row=0)

    def _create_group_title_row(self, column, row, group):
        if row == 1:
            pady = (0, 5)
        else:
            pady = (15, 5)
        group_title = Label(column, text=group, style="groupTitle.TLabel")
        group_title.grid(column=0, columnspan=2, pady=pady, padx=0, sticky="W")

    def _create_key_desc_row(self, col, key, desc):
        desc = Label(col, text=desc, style="desc.TLabel")
        desc.grid(column=0, row=self.current_row, sticky="W", padx=15, pady=2)

        key = Label(col, text=key, style="keys.TLabel")
        key.grid(column=1, row=self.current_row, sticky="W", padx=15, pady=2)

    def _create_statusbar_row(self, text, max_cols, row):
        status = Label(
            self, text=text, wraplength=300 * max_cols, style="statusbar.TLabel"
        )
        # with: 0.048 / without: 0.026 - 0.030
        status.grid(column=0, columnspan=max_cols, row=row, pady=1)

    def _create_new_column(self):
        column = Frame(self)
        column.grid(row=1, column=self.current_col, sticky="nsew", padx=15, pady=15)
        self.current_col += 1
        self.current_row = 1
        return column

    def _create_layout(self):
        start_time = time.time()
        self._logger.info(f"{start_time} - Layout - Start")
        self.current_row = 1  # Row 0 is reserved for Title
        self.current_col = 0

        max_rows = self.data.config["style"].get("max_rows", 15)
        acutal_max_rows = 0  # actual might not reach max_rows
        column = self._create_new_column()
        self._logger.info(f"Layout - {time.time() - start_time:.4f} - Init")

        if len(self.data.hints) <= 0:
            acutal_max_rows = 1
            title_text = "No Hints found"
        else:
            first_hints = self.data.hints[0]
            title_text = first_hints["title"]

            for group, hints in first_hints["hints"].items():
                # Start next column, if less than 4 rows left
                if self.current_row > max_rows - 4:
                    column = self._create_new_column()

                # Append group title
                self._create_group_title_row(column, self.current_row, group)
                self.current_row += 1

                # Append keys
                for key, desc in hints.items():
                    # If column is full switch to next column
                    if self.current_row >= max_rows:
                        column = self._create_new_column()
                    self._create_key_desc_row(column, key, desc)
                    self.current_row += 1
                    acutal_max_rows = max(acutal_max_rows, self.current_row)
                self._logger.info(
                    f"Layout - {time.time() - start_time:.4f} - Group {group}"
                )

        self._create_title_row(title_text, self.current_col)
        self._logger.info(f"Layout - {time.time() - start_time:.4f} - Title")

        # Show statusbar if enabled in config or now hints found
        if (len(self.data.hints) <= 0) or self.data.config["style"][
            "statusbar_visible"
        ]:
            self._create_statusbar_row(
                f"process: '{self.data.app_process}' - title: '{self.data.app_title}'",
                self.current_col,
                acutal_max_rows,
            )
        self._logger.info(f"Layout - {time.time() - start_time:.4f} - Statusbar")

        self._logger.info(f"{time.time()} - Layout - End")

    def _set_window_style(self):
        """Center a window on the screen.

        root.wait_visibility(root) my bee needed, have to check that!
        """
        root = self.master

        root.attributes("-alpha", self.data.config["style"].get("alpha", 0.8))

        if self.data.platform_os == "Windows":
            root.eval("tk::PlaceWindow %s center" % root.winfo_toplevel())


class ShowHintsHandler(AbstractHandler):
    """Display hints in own window."""

    # Container for data object
    data: HintsData

    def handle(self, data: HintsData) -> HintsData:
        """Take multimon screenshots and add those images to session data.

        Args:
            AbstractHandler (class): self
            data (HintsData): Central data object

        Returns:
            HintsData: Central data object

        """
        self._logger.info("Displaying hints...")

        self.data = data

        root = Tk(className="keyhint")

        # style: dict = self.data.config["style"]
        # Fallback to defaults, if missing
        # font_family = style.get("font_family", "")
        # font_base_size = style.get("font_base_size", 16)
        # background_color = style.get("background_color", "black")

        # self.default_font = font.nametofont("TkDefaultFont")
        # self.default_font.configure(size=int(font_base_size * 0.85), family=font_family)

        # root.option_add("*Font", self.default_font)
        # root.configure(bg="red")

        root.title("keyhint")

        if self.data.config["behavior"]["close_on_mouse_out"]:
            root.bind("<FocusOut>", lambda _: root.destroy())
        if self.data.config["behavior"]["close_on_anykey"]:
            root.bind_all("<Key>", lambda _: root.destroy())
        if self.data.config["behavior"]["close_on_esc"]:
            root.bind_all("<Escape>", lambda _: root.destroy())

        if self.data.platform_os == "Windows":
            root.overrideredirect(True)

        HintsWindow(root, self.data)

        if not data.testrun:
            root.mainloop()

        if self._next_handler:
            return super().handle(data)
        return data
