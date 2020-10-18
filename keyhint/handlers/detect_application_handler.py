"""Handler responsible for attaching screenshot(s) to session data."""

# Own
from ..data_model import HintsData
from .. import helpers
from .abstract_handler import AbstractHandler


class DetectApplicationHandler(AbstractHandler):
    """Enrich data with information about the currently active application window."""

    def handle(self, data: HintsData) -> HintsData:
        """Gather information about the currently active application window.

        Args:
            AbstractHandler (class): self
            data (HintsData): Central data object

        Returns:
            HintsData: Central data object
        """
        self._logger.debug("Detecting active window..")

        if data.testrun:
            data.app_process, data.app_title = "code", "VS Code"
        else:
            data.app_process, data.app_title = helpers.get_active_window_info(
                data.platform_os
            )

        if self._next_handler:
            return super().handle(data)
