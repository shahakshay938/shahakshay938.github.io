#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

PUBLISHED_HOSTS = {
    "shahakshay938.github.io",
    "www.shahakshay938.github.io",
}


def parse_wrapper_target(text: str) -> str | None:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return None


def repo_wrapper_path(url: str, repo_root: Path | None = None) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc not in PUBLISHED_HOSTS:
        return None

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    root = repo_root or Path(__file__).resolve().parent.parent

    if len(parts) == 2 and parts[0] == "streams" and parts[1].endswith(".m3u8"):
        return root / "streams" / parts[1]

    if len(parts) == 4 and parts[0] == "backups" and parts[1] == "streams" and parts[3].endswith(".m3u8"):
        return root / "backups" / "streams" / parts[2] / parts[3]

    return None


def read_wrapper_target(path: Path) -> str | None:
    if not path.exists():
        return None
    return parse_wrapper_target(path.read_text(encoding="utf-8", errors="replace"))


def resolve_stream_target(url: str, repo_root: Path | None = None) -> str:
    local_path = repo_wrapper_path(url, repo_root=repo_root)
    if local_path:
        target = read_wrapper_target(local_path)
        if target:
            return target

        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=10) as response:
                remote_text = response.read().decode("utf-8", errors="replace")
            target = parse_wrapper_target(remote_text)
            if target:
                return target
        except Exception:
            pass

    return url

