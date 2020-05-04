"""Defines the data model for the whole program."""

# Default
import platform
from pathlib import Path
from dataclasses import dataclass, field


@dataclass()
class HintsData:
    """DataClass containing all information.

    It is instantiated "empty" and enriched step by step, before
    the final hint window is rendered based on it's attributes.

    """

    # Many attributes are fina for a data class
    # pylint: disable=too-many-instance-attributes

    # Information about active info
    wm_class: str = ""
    wm_name: str = ""

    # Set data Path
    data_path = Path(__file__).parent.parent / "data"

    # Index of available applications
    index: dict = field(default_factory=dict)

    # Currently detected 'application' (based on regex on wm_class)
    app_name: str = ""
    app_wm_class_regex: str = ""

    # Currently detected 'context' (based on regex on wm_name)
    context_name: str = ""
    context_wm_name_regex: str = ""

    # Contains grouped hints, organized like
    # {group_a: {keys_1: description_1, keys_2: desc...}, group_b {...}, ...},
    hints: dict = field(default_factory=dict)

    # Control visual appearance of hint
    style_theme: str = "dark"
    style_alpha: float = 0.7
    style_font_family: str = ""
    style_font_base_size: int = 14
    style_max_rows: int = 20

    def __repr__(self):
        """Create string representation of dataclass.

        Returns
            str -- Representation of class

        """
        string = f"\n{'='*20} <dataclass> {'='*20}\n"

        for attr in dir(self):
            # Skip internal attributes
            if attr.startswith("_"):
                continue

            # Convert other attributes to strings
            if attr == "index":
                string += f"{attr}: \n"
                for elem in getattr(self, attr):
                    string += f"  {elem}\n"
            elif attr == "hints":
                string += f"{attr}:\n"
                for group, keys in getattr(self, attr).items():
                    string += f"  {group}:\n"
                    for key, val in keys.items():
                        string += f"    {key}: {val}\n"
            else:
                string += f"{attr}: {getattr(self, attr)}\n"

        string += f"{'='*20} </dataclass> {'='*19}"
        return string

    @property
    def platform_os(self) -> str:
        """Return either 'Linux', 'Darwin' or 'Windows'."""
        return platform.system()
