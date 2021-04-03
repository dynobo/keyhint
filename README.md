# KeyHint

**_Display keyboard shortcuts or other hints based on the the active window. (GTK, Linux only!)_**

<p align="center"><br>
<img alt="Tests passing" src="https://github.com/dynobo/keyhint/workflows/Test/badge.svg">
<a href="https://github.com/dynobo/keyhint/blob/master/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/Code%20style-black-%23000000"></a>
<a href='https://coveralls.io/github/dynobo/keyhint'><img src='https://coveralls.io/repos/github/dynobo/keyhint/badge.svg' alt='Coverage Status' /></a>
</p>

<p align="center"><br><img src="https://raw.githubusercontent.com/dynobo/keyhint/refactoring/src/keyhint/resources/keyhint_128.png"></p>

## Usage

- Install from **PyPi** with `pip install keyhint` and run `keyhint`.
- _Or_ download the **AppImage** from [releases](https://github.com/dynobo/keyhint/releases), make it executable and run it.
- Configure a **global hotkey** (e.g. `F1`) to start KeyHint on demand.

_KeyHint with KeyBindings for VS Code:_

![VS Code Shortcuts](https://raw.githubusercontent.com/dynobo/keyhint/master/src/keyhint/resources/vscode.png)

## CLI Options

```
Application Options:
  -h, --hint=HINT-ID             Show hints by specified ID
  -d, --default-hint=HINT-ID     Hint to show in case no hints for active application were found
  -v, --verbose                  Verbose log output for debugging
  --display=DISPLAY              X display to use
```

## Configuration

- The **config directory** is `~/.config/keyhint/`.
- To **customize existing** hints, copy [the corresponding .yaml-file](https://github.com/dynobo/keyhint/tree/master/src/keyhint/config) into the config directory. Make your changes in a text editor. As long as you don't change the `id` it will overwrite the defaults.
- To **create new** hints, I suggest you also start with [one of the existing .yaml-file](https://github.com/dynobo/keyhint/tree/master/src/keyhint/config):
  - Place it in the config directory and give it a good file name.
  - Change the value `id` to something unique.
  - Adjust `regex_process` and `regex_title` so it will be selected based on the active window. (See [Tips](#tips))
  - Add the `hints` to be displayed. 
  - If you think the hints might be useful for others, please consider opening a pull request or an issue.
- You can always **reset a configuration** to the shipped version by deleting the `.yaml` files from the config folder.

## Tips

**Hints selection:**

- The hints to be displayed on startup are selected by comparing the value of `regex_process` with the wm_class of the active window and the value of `regex_title` with the title of the active window. 
- The potential hints are processed alphabetically by filename, the first file that matches both wm_class and title are gettin displayed. 
- Both of `regex_` values are interpreted as **case insensitive regular expressions**.
- Check "Debug Info" in the application menu to get insights about the active window and the selected hints file.

**Available hints:**

- Check the [included yaml-files](https://github.com/dynobo/keyhint/tree/master/src/keyhint/config) to see wich applications are available by default.
- Feel free submit additional `yaml-files` for further applications.

**Differentiate hints per website:**

- For showing different browser-hints depending on the current website, you might want to use a browser extension like "[Add URL To Window Title](https://addons.mozilla.org/en-US/firefox/addon/add-url-to-window-title/)" and then configure the sections in `hints.yaml` to look for the URL in the window title.

## Contribute

I'm happy about any contribution! Especially I would appreciate submissions to improve the [shipped hints](https://github.com/dynobo/keyhint/tree/master/src/keyhint/config). (The current set are the hints I personally use).

## Design Principles

- **Don't run as service**<br>It shouldn't consume resources in the background, even if this leads to slower start-up time.
- **No network connection**<br>Everything should run locally without any network communication.
- **Dependencies**<br>The fewer dependencies, the better.
- **Multi-Monitors**<br>Supports setups with two or more displays

## Certification

![WOMM](https://raw.githubusercontent.com/dynobo/lmdiag/master/badge.png)
