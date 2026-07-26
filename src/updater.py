"""
Check if github repository release is updated.
"""

import json
import logging
from urllib import parse, request

from packaging.version import InvalidVersion, Version

logger = logging.getLogger(__name__)


def _compare_tag(l_tag, c_tag, split="."):
    try:
        latest = Version(l_tag.replace(split, "."))
        current = Version(c_tag.replace(split, "."))
    except (AttributeError, InvalidVersion):
        return False
    return latest > current


def is_updated(github_url, current_tag, with_dl=False, split="."):
    """
    Check if github repository release is updated

    :param github_url: The repository url
    :param current_tag: Current version tag
    :param with_dl: If has update, return latest download link . Default False
    :param split: The split char in version string. Default '.'
    :return: True/False or download link

    """
    release = Release(github_url)
    if not release.latest_tag:
        return False
    if _compare_tag(release.latest_tag, current_tag, split):
        return True if not with_dl else release.get_latest_dl()
    else:
        return False


class Release:
    def __init__(self, url):
        """
        Github release object.
        :param url: The github repository url
        """
        url_path = parse.urlparse(url).path
        self.url = url

        self.base_api_url = "https://api.github.com/repos" + (
            url_path if url_path.endswith("releases") else url_path + "/releases"
        )
        self.latest_response = self._get_response("/latest")
        self.latest_tag = self.latest_response.get("tag_name")

    def get_latest_dl(self, name=None, order_num=0):
        """
        Get the latest update download link.
        :param name: the file name you want to get
        :param order_num: the order number you want to get
        :return: latest download link
        """
        return self._get_download_url(self.latest_response, name, order_num)

    def _get_response(self, url_path):
        url = self.base_api_url + url_path
        try:
            api_request = request.Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "pdfdir",
                },
            )
            with request.urlopen(api_request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError) as e:
            logger.warning("Get release info failed: %s", e)
            return {}

    @staticmethod
    def _get_download_url(response, name=None, order_num=0):
        """
        Get the download link in response.
        :param response: Github api response json
        :param name: the file name you want to get
        :param order_num: the order number you want to get
        :return: download link
        """
        assets = response.get("assets")
        if not assets:
            return None

        if name:
            for asset in assets:
                if asset.get("name") == name:
                    return asset.get("browser_download_url")
        else:
            return assets[order_num].get("browser_download_url")
