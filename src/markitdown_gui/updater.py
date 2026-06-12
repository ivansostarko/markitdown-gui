"""Update check against GitHub Releases.

The app never downloads or installs anything by itself — it only compares
versions and points the user to the releases page.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Optional

from markitdown_gui import __version__

REPO = "ivansostarko/markitdown-gui"
REPO_URL = f"https://github.com/{REPO}"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"{REPO_URL}/releases/latest"


@dataclass(frozen=True)
class UpdateInfo:
    current: str
    latest: str
    url: str

    @property
    def available(self) -> bool:
        return _version_tuple(self.latest) > _version_tuple(self.current)


def _version_tuple(version: str) -> tuple[int, int, int]:
    """'v1.2.3' / '1.2' / '1.2.3-beta' -> (1, 2, 3) — lenient on purpose."""
    parts: list[int] = []
    for chunk in version.strip().lstrip("vV").split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    parts += [0, 0, 0]
    return (parts[0], parts[1], parts[2])


def check_for_update(timeout: float = 6.0) -> Optional[UpdateInfo]:
    """Return the latest release info, or None if the check failed
    (offline, rate-limited, no releases yet, …). Never raises."""
    try:
        request = urllib.request.Request(
            RELEASES_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"markitdown-gui/{__version__}",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
        latest = str(data.get("tag_name") or "").strip()
        if not latest:
            return None
        return UpdateInfo(__version__, latest, str(data.get("html_url") or RELEASES_PAGE))
    except Exception:
        return None
