"""Test helper methods."""

# Standard
import logging
import platform

# Own
from .context import keyhint

helpers = keyhint.helpers


def test_helpers_init_logging():
    """Test if function returns a logger."""
    logger = helpers.init_logging("test_logger")
    assert isinstance(logger, logging.Logger)


def test_get_active_window_info():
    app_process, app_title = helpers.get_active_window_info(platform.system())
    assert isinstance(app_process, str)
    assert isinstance(app_title, str)


def test_get_active_window_info_win():
    if platform.system() == "Windows":
        app_process, app_title = helpers.get_active_window_info_win()
        assert isinstance(app_process, str)
        assert isinstance(app_title, str)
    else:
        assert True


def test_get_active_window_info_x():
    if platform.system() == "Linux":
        app_process, app_title = helpers.get_active_window_info_x()
        assert isinstance(app_process, str)
        assert isinstance(app_title, str)
    else:
        assert True


def test_remove_emojis():
    emojis = [
        "watch:\u231a",
        "nerd:\uF913",
        "brain:\uF9E0",
        "unicorn:\uF984",
        "pizza:\uF355",
        "joystick:\uF579",
        "megaphone:\uF4E3",
    ]
    emoji_str = "".join(emojis)
    expected_clean_str = "watch:nerd:brain:unicorn:pizza:joystick:megaphone:"
    actual_clean_str = helpers.remove_emojis(emoji_str)
    assert expected_clean_str == actual_clean_str


def test_is_using_wayland():
    using_wayland = helpers.is_using_wayland()
    assert using_wayland in [True, False]


def test_get_users_config_path():
    config_path = helpers.get_users_config_path()
    assert config_path.exists()
