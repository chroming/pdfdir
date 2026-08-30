# -*- coding:utf-8 -*-

"""Check whether a newer GitHub release is available."""

from urllib import parse

from packaging.version import Version
import requests


UPDATE_AVAILABLE = "update"
UP_TO_DATE = "current"


def _version(tag, split="."):
    value = str(tag).strip()
    if split != ".":
        value = value.replace(split, ".")
    return Version(value)


def _compare_tag(l_tag, c_tag, split="."):
    """Return whether ``l_tag`` is newer according to PEP 440."""
    return _version(l_tag, split) > _version(c_tag, split)


def _check_release(github_url, current_tag, split="."):
    release = Release(github_url)
    latest_tag = release.latest_tag
    if not latest_tag:
        raise ValueError(
            "The latest GitHub release response did not include tag_name"
        )
    state = (
        UPDATE_AVAILABLE
        if _compare_tag(latest_tag, current_tag, split)
        else UP_TO_DATE
    )
    return state, release


def check_for_update(github_url, current_tag, split="."):
    """Return ``"update"`` or ``"current"``; propagate check failures."""
    state, _release = _check_release(github_url, current_tag, split=split)
    return state


def is_updated(github_url, current_tag, with_dl=False, split="."):
    """
    Check if github repository release is updated

    :param github_url: The repository url
    :param current_tag: Current version tag
    :param with_dl: If has update, return latest download link . Default False
    :param split: The split char in version string. Default '.'
    :return: True/False or download link

    """
    state, release = _check_release(github_url, current_tag, split=split)
    if state == UPDATE_AVAILABLE:
        return release.get_latest_dl() if with_dl else True
    return False


class Release(object):
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
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("GitHub release response must be a JSON object")
        return payload

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
