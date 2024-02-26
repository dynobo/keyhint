import logging
import os
import re
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any

from keyhint import config

logger = logging.getLogger("keyhint")


def _load_toml(file_path: str | os.PathLike) -> dict:
    """Load a toml file from resource path or other path.

    Args:
        file_path: Filename in resources, or complete path to file.
        from_resources: Set to true to load from resource. Defaults
            to False.

    Returns:
        [description]
    """
    try:
        with Path(file_path).open("rb") as fh:
            result = tomllib.load(fh)
    except Exception as exc:
        logger.warning("Could not loading toml file %s: %s", file_path, exc)
        result = {}

    return result


def load_default_sheets() -> list[dict]:
    """Load default keyhints from toml files shipped with the package.

    Returns:
        List[dict]: List of application keyhints and meta info.
    """
    default_sheet_path = Path(__file__).parent / "config"
    sheets = [_load_toml(f) for f in default_sheet_path.glob("*.toml")]
    logger.debug("Found %s default sheets.", len(sheets))
    return sorted(sheets, key=lambda k: k["id"])


def load_user_sheets() -> list[dict]:
    """Load cheatsheets from toml files in the users .config/keyhint/ directory.

    Returns:
        List[dict]: List of application keyhints and meta info.
    """
    files = config.CONFIG_PATH.glob("*.toml")
    sheets = [_load_toml(f) for f in files]
    logger.debug("Found %s user sheets in %s/.", len(sheets), config.CONFIG_PATH)
    return sorted(sheets, key=lambda k: k["id"])


def _expand_includes(sheets: list[dict]) -> list[dict]:
    new_sheets = []
    for s in sheets:
        for include in s.get("include", []):
            included_sheets = [c for c in sheets if c["id"] == include]
            if not included_sheets:
                message = f"Sheet '{include}' included by '{s['id']}' not found!"
                raise ValueError(message)
            included_sheet = deepcopy(included_sheets[0])
            included_sheet["section"] = {
                f"[{included_sheet['id']}] {k}": v
                for k, v in included_sheet["section"].items()
            }
            s["section"].update(included_sheet["section"])
        new_sheets.append(s)
    return new_sheets


def _remove_empty_sections(sheets: list[dict]) -> list[dict]:
    for sheet in sheets:
        sheet["section"] = {k: v for k, v in sheet["section"].items() if v}
    return sheets


def _remove_hidden(sheets: list[dict]) -> list[dict]:
    return [s for s in sheets if not s.get("hidden", False)]


def _update_or_append(sheets: list[dict], new_sheet: dict) -> list[dict]:
    for sheet in sheets:
        if sheet["id"] == new_sheet["id"]:
            # Update existing default sheet by user sheet
            sheet["section"].update(new_sheet.pop("section", {}))
            sheet["match"].update(new_sheet.pop("match", {}))
            sheet.update(new_sheet)
            break
    else:
        # If default sheet didn't exist, append as new
        sheets.append(new_sheet)
    return sheets


def load_sheets() -> list[dict]:
    """Load unified default keyhints and keyhints from user config.

    First the default keyhints are loaded, then they are update (added/overwritten)
    by the keyhints loaded from user config.

    Returns:
        List[dict]: List of application keyhints and meta info.
    """
    sheets = load_default_sheets()
    user_sheets = load_user_sheets()

    for user_sheet in user_sheets:
        sheets = _update_or_append(sheets, user_sheet)

    sheets = _expand_includes(sheets)
    sheets = _remove_hidden(sheets)
    sheets = _remove_empty_sections(sheets)
    logger.debug("Loaded %s sheets.", len(sheets))
    return sheets


def get_sheet_by_id(sheets: list[dict], sheet_id: str) -> dict[str, Any]:
    return next(sheet for sheet in sheets if sheet["id"] == sheet_id)


def get_sheet_id_by_active_window(
    sheets: list[dict], wm_class: str, window_title: str
) -> str | None:
    matching_sheets = [
        h
        for h in sheets
        if re.search(h["match"]["regex_wmclass"], wm_class, re.IGNORECASE)
        and re.search(h["match"]["regex_title"], window_title, re.IGNORECASE)
    ]

    if not matching_sheets:
        return None

    # First sort by secondary criterion
    matching_sheets.sort(key=lambda h: len(h["match"]["regex_title"]), reverse=True)

    # Then sort by primary criterion
    matching_sheets.sort(key=lambda h: len(h["match"]["regex_wmclass"]), reverse=True)

    # First element is (hopefully) the best fitting sheet id
    return matching_sheets[0]["id"]


if __name__ == "__main__":
    load_sheets()
