# Changelog

## v0.5.2 (2024-10-04)

- Add cheatsheet for Alacritty.
- Changed `cli` cheatsheet to hidden by default.
- Renamed browser- and vscode-extension cheatsheets.

## v0.5.1 (2024-07-04)

- Fix support for older version of `libadwaita`.
- Add cheatsheet for GH copilot.

## v0.5.0 (2024-04-23)

- Breaking changes:
  - Renamed the attribute `regex_process` in `toml`-files to `regex_wmclass`.
  - Renamed the attribute `source` in `toml`-files to `url`.
  - Removed cli-args which are now covered by settings menu.
- Fix duplicate IDs in included sections.
- Add settings menu to ui.
- Add Support KDE + Wayland.
- Focus search field on start.
- Cheatsheets:
  - Moved some CLI commands into separate cheatsheet and include it in terminal apps.
  - Added sheet for Keyhint itself.

## v0.4.3 (2024-02-13)

- Fix background color in GTK 4.6.

## v0.4.2 (2024-02-13)

- Fix missing method in GTK 4.6.

## v0.4.1 (2024-02-04)

- Fix `No module named 'toml'`.

## v0.4.0 (2024-02-04)

- Breaking changes in config files:
  - Switch from yaml to toml format for shortcuts (you can use
    [`yq`](https://mikefarah.gitbook.io/yq/) to convert yaml to toml)
  - The key `hints` is renamed to `section`
- Dropping binary builds! Please install via `pipx install keyhint` instead.
- Add filter for shortcuts or section.
- Add possibility to hide whole cheatsheets via `hidden = true` in config files.
- Add fullscreen mode as default (toggle via `F11`)

## v0.3.0 (2023-02-12)

- Update app to Gtk4
- Adjust hint files

## v0.2.4 (2022-03-09)

- Switch to Nuitka for building binary release

## v0.2.3 (2022-03-06)

- Add accent color for section titles

## v0.2.2 (2022-03-05)

- Add hints for kitty
- Add hints for pop-shell
- Update dependencies

## v0.2.1 (2021-05-18)

- Slightly improve shortcuts for vscode

## v0.2.0 (2021-04-03)

- Complete rewrite
- Drop support for Windows (for now)
- Use GTK+ framework

## v0.1.3 (2020-10-18)

- Switch to TKinter
- Speed improvements

## v0.1.0 (2020-05-15)

- Initial version
