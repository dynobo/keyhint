"""Handler responsible for attaching screenshot(s) to session data."""

# Standard
from pathlib import Path
import shutil
import os
import yaml

# Own
from .. import helpers
from ..data_model import HintsData
from .abstract_handler import AbstractHandler


class LoadConfigsHandler(AbstractHandler):
    """Reads information from application specific json file."""

    # Container for data object
    data: HintsData
    keyhint_dir: str = "keyhint"
    config_file: str = "config.yaml"
    hints_file: str = "hints.yaml"
    pkg_config_dir: Path = Path(__file__).parent.parent / "config"

    def handle(self, data: HintsData) -> HintsData:
        """Load config and hint files, or create default ones.

        Args:
            data (HintsData): Central data object

        Raises:
            ValueError: In case no config path could be detected

        Returns:
            HintsData: Central data object

        """
        self._logger.debug("Loading hints data...")
        self.data = data

        config_path = helpers.get_users_config_path()
        if not config_path:
            raise ValueError("Couldn't detect config path!")

        data.config_path = config_path / self.keyhint_dir

        self._create_default_configs()
        self._load_configs()

        if self._next_handler:
            return super().handle(self.data)
        return self.data

    def _load_yaml(self, file_path):
        """Load data from yaml."""
        data = {}
        with open(file_path) as file:
            try:
                data = yaml.safe_load(file)
            except yaml.YAMLError as exc:
                self._logger.error("Exception while loading hints.yaml!")
                self._logger.error(exc)
        return data

    def _create_default_configs(self):
        """Check if config/hint yamls exist, if not, copy from defaults."""
        config_file = self.data.config_path / self.config_file
        hints_file = self.data.config_path / self.hints_file

        if not config_file.exists():
            os.makedirs(self.data.config_path, exist_ok=True)
            default_config = self.pkg_config_dir / self.config_file
            shutil.copy(default_config, config_file)

        if not hints_file.exists():
            os.makedirs(self.data.config_path, exist_ok=True)
            default_hints = self.pkg_config_dir / self.hints_file
            shutil.copy(default_hints, hints_file)

    def _load_configs(self):
        """Load config/hint yamls to central data object."""
        self.data.config = self._load_yaml(self.data.config_path / self.config_file)
        self.data.hints = self._load_yaml(self.data.config_path / self.hints_file)
