"""Handler responsible for attaching screenshot(s) to session data."""

# Own
from ..data_model import HintsData
from .. import helpers
from .abstract_handler import AbstractHandler


class DetectApplicationHandler(AbstractHandler):
    """Enrich data with information about the currently active application window."""

    def handle(self, data: HintsData) -> HintsData:
        """Gather information about the currently active application window.

        Arguments
            AbstractHandler {class} -- self
            data {NormcapData} -- NormCap's session data

        Returns
            NormcapData -- Enriched NormCap's session data

        """
        self._logger.debug("Detecting active window..")

        data.wm_class, data.wm_name = helpers.get_active_window_info(data.platform_os)

        if self._next_handler:
            return super().handle(data)
        return data
