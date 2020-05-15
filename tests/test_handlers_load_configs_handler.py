# Default
from pathlib import Path

# Own
from .context import keyhint

LoadConfigsHandler = keyhint.handlers.load_configs_handler.LoadConfigsHandler
config_dir = Path(__file__).parent.parent / "keyhint" / "config"


def test_handle_result():
    """Does the handle return a valid HintsData object?"""
    handler = LoadConfigsHandler()
    data = keyhint.data_model.HintsData()
    result = handler.handle(data)
    assert isinstance(result, keyhint.data_model.HintsData)


def test_load_yaml():
    """Does the config yaml gets's loaded correctly?"""
    handler = LoadConfigsHandler()
    data = handler._load_yaml(config_dir / "config.yaml")
    assert isinstance(data, dict)
    assert "style" in data.keys()
    assert "behavior" in data.keys()


def test_create_default_configs():
    """Are the default configs created, if necessary?"""
    handler = LoadConfigsHandler()

    # Prepare data
    handler.data = keyhint.data_model.HintsData()
    config_path = keyhint.helpers.get_users_config_path()
    handler.data.config_path = config_path / handler.keyhint_dir

    it_worked = True
    try:
        handler._create_default_configs()
    except:  # noqa
        it_worked = False

    assert (handler.data.config_path / "hints.yaml").exists()
    assert (handler.data.config_path / "config.yaml").exists()
    assert it_worked
