# KeyHint

**_Utility to display keyboard shortcuts or other hints based on the active window on
Linux._**

<p align="center"><br>
<img alt="Tests passing" src="https://github.com/dynobo/keyhint/workflows/Test/badge.svg">
<a href="https://github.com/dynobo/keyhint/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/Code%20style-black-%23000000"></a>
<a href='https://coveralls.io/github/dynobo/keyhint'><img src='https://coveralls.io/repos/github/dynobo/keyhint/badge.svg' alt='Coverage Status' /></a>
</p>

![Keyhint Screenshot](https://raw.githubusercontent.com/dynobo/keyhint/main/keyhint/resources/keyhint.png)

## Prerequisites

- Python 3.11+
- GTK 4.6+ (shipped since Ubuntu 22.04) + related dev packages:
  ```sh
  sudo apt-get install \
     libgirepository1.0-dev \
     libcairo2-dev \
     python3-gi \
     gobject-introspection \
     libgtk-4-dev
  ```
- Wayland & Gnome: The
  [Gnome Extension "Window-Calls"](https://extensions.gnome.org/extension/4724/window-calls/)
  is required to auto-select the cheatsheet based on the current active application.

## Installation

- `pipx install keyhint` (recommended, requires [pipx](https://pipx.pypa.io/))
- _or_ `pip install keyhint`

## Usage

- Configure a **global hotkey** (e.g. `Ctrl + F1`) **via your system settings** to
  launch `keyhint`.
- If KeyHint is launched via hotkey, it detects the current active application and shows
  the appropriate hints. (This feature won't work reliably when KeyHint ist started via
  Menu or Launcher.)

## CLI Options

```
Application Options:
  -c, --cheatsheet=SHEET-ID                 Show cheatsheet with this ID on startup
  -v, --verbose                             Verbose log output for debugging
```

## Cheatsheet Configuration

The content which KeyHint displays is configured using [`toml`](https://toml.io/en/)
configuration files.

KeyHint reads those files from two locations:

1. The [built-in directory](https://github.com/dynobo/keyhint/tree/main/keyhint/config)
1. The user directory, usually located in `~/.config/keyhint`

### How Keyhint selects the cheatsheet to show

- The cheatsheet to be displayed on startup are selected by comparing the value of
  `regex_wmclass` with the wm_class of the active window and the value of `regex_title`
  with the title of the active window.
- The potential cheatsheets are processed alphabetically by filename, the first file
  that matches both wm_class and title are getting displayed.
- Both of `regex_` values are interpreted as **case in-sensitive regular expressions**.
- Check "Debug Info" in the application menu to get insights about the active window and
  the selected cheatsheet file.

### Customize or add cheatsheets

- To **change built-in** cheatsheets, copy
  [the corresponding .toml-file](https://github.com/dynobo/keyhint/tree/main/src/keyhint/config)
  into the config directory. Make your changes in a text editor. As long as you don't
  change the `id` it will overwrite the defaults.
- To **create new** cheatsheets, I suggest you start with
  [one of the existing .toml-file](https://github.com/dynobo/keyhint/tree/main/src/keyhint/config):
  - Place it in the config directory and give it a good file name.
  - Change the value `id` to something unique.
  - Adjust `regex_wmclass` and `regex_title` so it will be selected based on the active
    window. (See [Tips](#tips))
  - Add the `shortcuts` & `label` to a `section`.
  - If you think your cheatsheet might be useful for others, please consider opening a
    pull request or an issue!
- You can always **reset cheatsheets** to the shipped version by deleting the
  corresponding `.toml` files from the config folder.
- You can **include shortcuts from other cheatsheets** by adding
  `include = ["<Cheatsheet ID>"]`

### Examples

#### Hide existing cheatsheets

To hide a cheatsheet, e.g. the
[built-in](https://github.com/dynobo/keyhint/blob/main/keyhint/config/tilix.toml) one
with the ID `tilix`, create a new file `~/.config/keyhint/tilix.toml` with the content:

```toml
id = "tilix"
hidden = true
```

#### Extend existing cheatsheets

To add keybindings to an existing cheatsheet, e.g. the
[built-in](https://github.com/dynobo/keyhint/blob/main/keyhint/config/firefox.toml) one
with the ID `firefox`, create a new file `~/.config/keyhint/firefox.toml` which only
contains the ID and the additional bindings:

```toml
id = "firefox"

[section]
[section."My Personal Favorites"]  # New section
"Ctrl + Shift + Tab" = "Show all Tabs"
# ...
```

#### Add new cheatsheet which never gets auto-selected

To add a new cheatsheet, which never gets automatically selected and displayed by
KeyHint, but remains accessible through KeyHint's cheatsheet dropdown, create a file
`~/.config/keyhint/my-app.toml`:

```toml
id = "my-app"
url = "url-to-my-apps-keybindings"

[match]
regex_wmclass = "a^"  # Patter which never matches
regex_title = "a^"

[section]
[section.General]
"Ctrl + C" = "Copy"
# ...

```

#### Different cheatsheets for different Websites

For showing different browser-cheatsheets depending on the current website, you might
want to use a browser extension like
"[Add URL To Window Title](https://addons.mozilla.org/en-US/firefox/addon/add-url-to-window-title/)"
and configure the `[match]` section to look for the url in the title. E.g.
`~/.config/keyhint/github.toml`

```toml
id = "github.com"

[match]
regex_wmclass = "Firefox"
regex_title = ".*github\\.com.*"  # URL added by browser extensions to window title

[section]
[section.Repositories]
gc = "Goto code tab"
# ...
```

## Contribute

I'm happy about any contribution! Especially I would appreciate submissions to improve
the
[shipped cheatsheets](https://github.com/dynobo/keyhint/tree/main/src/keyhint/config).
(The current set are the cheatsheets I personally use).

## Design Principles

- **Don't run as service**<br>It shouldn't consume resources in the background, even if
  this leads to slightly slower start-up time.
- **No network connection**<br>Everything should run locally without any network
  communication.
- **Dependencies**<br>The fewer dependencies, the better.

## Certification

![WOMM](https://raw.githubusercontent.com/dynobo/lmdiag/master/badge.png)
