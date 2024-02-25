import logging
import os
import tomllib
from copy import deepcopy
from pathlib import Path

import keyhint

logger = logging.getLogger(__name__)


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
        print(exc)  # noqa: T201
        result = {}

    return result


def load_default_sheets() -> list[dict]:
    """Load default keyhints from toml files shipped with the package.

    Returns:
        List[dict]: List of application keyhints and meta info.
    """
    default_sheet_path = Path(__file__).parent / "config"
    sheets = [_load_toml(f) for f in default_sheet_path.glob("*.toml")]
    logger.info("Loaded %s default cheatsheets.", len(sheets))
    return sorted(sheets, key=lambda k: k["id"])


def load_user_sheets() -> list[dict]:
    """Load cheatsheets from toml files in the users .config/keyhint/ directory.

    Returns:
        List[dict]: List of application keyhints and meta info.
    """
    files = keyhint.config.CONFIG_PATH.glob("*.toml")
    sheets = [_load_toml(f) for f in files]
    logger.info("Loaded %s user cheatsheets.", len(sheets))
    return sorted(sheets, key=lambda k: k["id"])


def _expand_includes(sheets: list[dict]) -> list[dict]:
    new_sheets = []
    for s in sheets:
        for include in s.get("include", []):
            included_sheets = [c for c in sheets if c["id"] == include]
            if not included_sheets:
                message = f"Cheatsheet '{include}' included by '{s['id']}' not found!"
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
        existed = False
        for sheet in sheets:
            # Update default sheet by user sheet (if existing)
            if sheet["id"] == user_sheet["id"]:
                user_sheet_sections = user_sheet.pop("section")
                sheet.update(user_sheet)
                sheet["section"].update(user_sheet_sections)
                existed = True
                break
        # If it didn't exist, append as new
        if not existed:
            sheets.append(user_sheet)

    sheets = _expand_includes(sheets)
    sheets = _remove_hidden(sheets)
    sheets = _remove_empty_sections(sheets)
    return sheets  # noqa: RET504


if __name__ == "__main__":
    load_sheets()
