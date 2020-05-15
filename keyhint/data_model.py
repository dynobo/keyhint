"""Defines the data model for the whole program."""

# Default
import platform
from pathlib import Path
from dataclasses import dataclass, field
from typing import Union
import pprint


@dataclass()
class HintsData:
    """DataClass containing all information.

    It is instantiated "empty" and enriched step by step, before
    the final hint window is rendered based on it's attributes.
    """

    # Indicates unit tests
    testrun: bool = False

    # Information about active info
    app_process: str = ""
    app_title: str = ""

    # Set data Path
    config_path: Union[Path, None] = None

    # Contains grouped hints
    hints: list = field(default_factory=list)

    # Contains information from yaml config, about behavior and look
    config: dict = field(default_factory=dict)

    def __repr__(self):
        """Create string representation of dataclass.

        Returns:
            str: Representation of class
        """
        text = f"\n{'='*20} <dataclass> {'='*20}\n"

        for attr in dir(self):
            # Skip internal attributes
            if attr.startswith("_"):
                continue

            # Convert other attributes to strings
            if attr in ["config", "hints"]:
                text += f"{attr}:\n"
                text += pprint.pformat(getattr(self, attr), width=100)
                text += "\n"

            else:
                text += f"{attr}: {getattr(self, attr)}\n"

        text += f"{'='*20} </dataclass> {'='*19}"
        return text

    @property
    def platform_os(self) -> str:
        """Return either 'Linux', 'Darwin' or 'Windows'."""
        return platform.system()
