"""Handler responsible for attaching screenshot(s) to session data."""
# Standard
import os
import subprocess
import re

# Own
from ..data_model import HintsData
from .abstract_handler import AbstractHandler


class DetectApplicationHandler(AbstractHandler):
    def handle(self, data: HintsData) -> HintsData:
        """Take multimon screenshots and add those images to session data.

        Arguments:
            AbstractHandler {class} -- self
            data {NormcapData} -- NormCap's session data

        Returns:
            NormcapData -- Enriched NormCap's session data
        """
        self._logger.debug("Detecting active window..")

        data.wm_class, data.wm_name = self.get_active_window_info()

        if self._next_handler:
            return super().handle(data)
        else:
            return data

    def get_active_window_info(self):

        root = subprocess.Popen(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"], stdout=subprocess.PIPE
        )
        stdout, stderr = root.communicate()

        m = re.search(b"^_NET_ACTIVE_WINDOW.* ([\w]+)$", stdout)

        if m != None:
            window_id = m.group(1)
            window = subprocess.Popen(
                ["xprop", "-id", window_id, "WM_NAME", "WM_CLASS"],
                stdout=subprocess.PIPE,
            )
            stdout, stderr = window.communicate()
        else:
            return None

        wm_name = wm_class = None

        match = re.search(b'WM_NAME\(\w+\) = "(?P<name>.+)"', stdout)
        if match != None:
            wm_name = match.group("name").decode("utf8")

        match = re.search(b'WM_CLASS\(\w+\) = "(?P<class>.+?)"', stdout)
        if match != None:
            wm_class = match.group("class").decode("utf8")

        return wm_class, wm_name

    def _test_for_wayland(self):
        """Check if we are running on Wayland DE.

        Returns:
            [bool] -- {True} if probably Wayland

        """
        result = False
        if "WAYLAND_DISPLAY" in os.environ:
            self._logger.info(
                "Wayland DE detected. Falling back to alternative screenshot approach..."
            )
            result = True
        return result
