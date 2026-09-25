"""Fail closed when a GitHub release already owns the requested tag."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def matching_releases(release_pages, tag):
    """Return every draft or published release with an exact tag match."""
    if not isinstance(release_pages, list):
        raise ValueError("GitHub release response must be a list of pages")

    matches = []
    for page in release_pages:
        if not isinstance(page, list):
            raise ValueError("Each GitHub release response page must be a list")
        for release in page:
            if not isinstance(release, dict):
                raise ValueError("Each GitHub release entry must be an object")
            if release.get("tag_name") == tag:
                matches.append(release)
    return matches


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("release_pages", type=Path)
    parser.add_argument("tag")
    args = parser.parse_args(argv)

    try:
        pages = json.loads(args.release_pages.read_text(encoding="utf-8"))
        matches = matching_releases(pages, args.tag)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(
            "::error::Could not verify existing GitHub releases: {}".format(
                exc
            )
        )
        return 2

    if matches:
        states = ", ".join(
            "draft" if release.get("draft") else "published"
            for release in matches
        )
        print(
            "::error::A {} release already exists for {}. "
            "Delete a stale draft explicitly before rerunning; "
            "published releases are immutable.".format(states, args.tag)
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
