# Changelog

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
