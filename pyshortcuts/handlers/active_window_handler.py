"""Handler responsible for attaching screenshot(s) to session data."""
# Standard
import os
import subprocess
import re

# Own
from ..data_model import ShortCutsData
from .abstract_handler import AbstractHandler


class ActiveWindowHandler(AbstractHandler):
    def handle(self, request: ShortCutsData) -> ShortCutsData:
        """Take multimon screenshots and add those images to session data.

        Arguments:
            AbstractHandler {class} -- self
            request {NormcapData} -- NormCap's session data

        Returns:
            NormcapData -- Enriched NormCap's session data
        """
        self._logger.debug("Detecting active window..")

        request.wm_class, request.wm_name = self.get_active_window_info()

        if self._next_handler:
            return super().handle(request)
        else:
            return request

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
