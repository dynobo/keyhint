# KeyHint

**_Linux utility to display keyboard shortcuts or other hints based on the active
window. (GTK 4.6+ required!)_**

<p align="center"><br>
<img alt="Tests passing" src="https://github.com/dynobo/keyhint/workflows/Test/badge.svg">
<a href="https://github.com/dynobo/keyhint/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/Code%20style-black-%23000000"></a>
<a href='https://coveralls.io/github/dynobo/keyhint'><img src='https://coveralls.io/repos/github/dynobo/keyhint/badge.svg' alt='Coverage Status' /></a>
</p>

<p align="center"><br><img src="https://raw.githubusercontent.com/dynobo/keyhint/main/keyhint/resources/keyhint_128.png"></p>

## Prerequisites

- Python 3.11+
- GTK 4.6+ (since Ubuntu 22.04)
- `libcairo2-dev libgirepository1.0-dev`

## Installation

- `pipx install keyhint` (recommended, requires [pipx](https://pipx.pypa.io/))
- _or_ `pip install keyhint`

## Usage

- Configure a **global hotkey** (e.g. `Ctrl + F1`) **via your system settings** to
  launch `keyhint`.
- If KeyHint is launched via hotkey, it detects the current active application and shows
  the appropriate hints.

_KeyHint with shortcuts for VS Code:_

![VS Code Shortcuts](https://raw.githubusercontent.com/dynobo/keyhint/main/keyhint/resources/vscode.png)

## CLI Options

```
Application Options:
  -c, --cheatsheet=SHEET-ID                 Show cheatsheet with this ID on startup
  -d, --default-cheatsheet=SHEET-ID         Cheatsheet to show in case no cheatsheet is found for active application
  -f, --no-fullscreen                       Launch window in normal window state instead of fullscreen mode
  -s, --no-section-sort                     Do not sort sections by size, keep order from config toml file
  -o, --orientation=horizontal|vertical     Orientation and scroll direction. Default: 'vertical'
  -v, --verbose                             Verbose log output for debugging
```

## Configuration

- The **config directory** is `~/.config/keyhint/`.
- To **customize existing** cheatsheets, copy
  [the corresponding .toml-file](https://github.com/dynobo/keyhint/tree/main/src/keyhint/config)
  into the config directory. Make your changes in a text editor. As long as you don't
  change the `id` it will overwrite the defaults.
- To **create new** cheatsheets, I suggest you also start with
  [one of the existing .toml-file](https://github.com/dynobo/keyhint/tree/main/src/keyhint/config):
  - Place it in the config directory and give it a good file name.
  - Change the value `id` to something unique.
  - Adjust `regex_process` and `regex_title` so it will be selected based on the active
    window. (See [Tips](#tips))
  - Add the `shortcuts` & `label` to a `section`.
  - If you think your cheatsheet might be useful for others, please consider opening a
    pull request or an issue.
- You can always **reset a configuration** to the shipped version by deleting the
  `.toml` files from the config folder.
- You can include shortcuts from other cheatsheets add `include = ["<Cheatsheet ID>"]`
  in the top block (same level as `id` and `title`).

## Tips

**Cheatsheet selection:**

- The cheatsheet to be displayed on startup are selected by comparing the value of
  `regex_process` with the wm_class of the active window and the value of `regex_title`
  with the title of the active window.
- The potential cheatsheets are processed alphabetically by filename, the first file
  that matches both wm_class and title are getting displayed.
- Both of `regex_` values are interpreted as **case insensitive regular expressions**.
- Check "Debug Info" in the application menu to get insights about the active window and
  the selected cheatsheet file.

**Available cheatsheets:**

- Check the
  [included toml-files](https://github.com/dynobo/keyhint/tree/main/src/keyhint/config)
  to see which applications are available by default.
- Feel free submit additional `toml-files` for further applications.

**Differentiate cheatsheets per website:**

- For showing different browser-cheatsheets depending on the current website, you might
  want to use a browser extension like
  "[Add URL To Window Title](https://addons.mozilla.org/en-US/firefox/addon/add-url-to-window-title/)"
  and then configure the sections in `<cheatsheet>.toml` to look for the URL in the
  window title.

**KeyHint's shortcuts:**

- `Ctrl+F`: Start filtering
- `Ctrl+S`: Focus sheet selection dropdown (press `Enter` to open it)
- `Esc`: Exit KeyHint
- `→`, `↓`, `l` or `k`: scroll forward
- `←`, `↑`, `h` or `j`: scroll backward
- `PageDown`: scroll page forward
- `PageUP`: scroll page backward

## Contribute

I'm happy about any contribution! Especially I would appreciate submissions to improve
the
[shipped cheatsheets](https://github.com/dynobo/keyhint/tree/main/src/keyhint/config).
(The current set are the cheatsheets I personally use).

## Design Principles

- **Don't run as service**<br>It shouldn't consume resources in the background, even if
  this leads to slower start-up time.
- **No network connection**<br>Everything should run locally without any network
  communication.
- **Dependencies**<br>The fewer dependencies, the better.
- **Multi-Monitors**<br>Supports setups with two or more displays

## Certification

![WOMM](https://raw.githubusercontent.com/dynobo/lmdiag/master/badge.png)
