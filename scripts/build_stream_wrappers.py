#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

try:
    from wrapper_utils import read_wrapper_target, resolve_stream_target
except ModuleNotFoundError:
    from scripts.wrapper_utils import read_wrapper_target, resolve_stream_target

DEFAULT_PUBLIC_BASE = "https://shahakshay938.github.io/streams"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate stable HLS wrapper files and rewrite a playlist to point at them."
    )
    parser.add_argument("playlist", nargs="?", default="latest.m3u")
    parser.add_argument("--output-dir", default="streams")
    parser.add_argument("--public-base-url", default=DEFAULT_PUBLIC_BASE)
    parser.add_argument("--index-file", default=None)
    return parser.parse_args()


def parse_m3u(path: Path) -> tuple[str, list[dict[str, object]]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if lines and lines[0].startswith("#EXTM3U"):
        header = lines[0]
        start_idx = 1
    else:
        header = "#EXTM3U"
        start_idx = 0

    entries: list[dict[str, object]] = []
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("#EXTINF:"):
            i += 1
            continue

        extinf = lines[i]
        extra: list[str] = []
        url = ""
        i += 1
        while i < len(lines):
            current = lines[i].strip()
            if current.startswith("#"):
                extra.append(lines[i])
                i += 1
                continue
            if current:
                url = current
                i += 1
                break
            i += 1

        tvg_match = re.search(r'tvg-id="([^"]*)"', extinf)
        name_match = re.search(r",(.+)$", extinf)

        entries.append(
            {
                "extinf": extinf,
                "extra": extra,
                "url": url,
                "tvg_id": tvg_match.group(1) if tvg_match else "",
                "name": name_match.group(1).strip() if name_match else "",
            }
        )

    return header, entries


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug or "channel"


def build_slug_plan(entries: list[dict[str, object]]) -> list[str]:
    base_slugs = []
    for entry in entries:
        tvg_id = str(entry.get("tvg_id") or "")
        name = str(entry.get("name") or "")
        base_slugs.append(slugify(tvg_id) if tvg_id else slugify(name))

    counts = Counter(base_slugs)
    planned: list[str] = []
    used: set[str] = set()

    for entry, base_slug in zip(entries, base_slugs):
        name_slug = slugify(str(entry.get("name") or ""))
        candidate = base_slug

        if counts[base_slug] > 1:
            if name_slug and name_slug != base_slug:
                candidate = f"{base_slug}-{name_slug}"
            else:
                candidate = f"{base_slug}-stream"

        original_candidate = candidate
        suffix = 2
        while candidate in used:
            candidate = f"{original_candidate}-{suffix}"
            suffix += 1

        used.add(candidate)
        planned.append(candidate)

    return planned


def wrapper_contents(name: str, target_url: str) -> str:
    safe_name = (name or "Primary").replace('"', "'")
    return "\n".join(
        [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
            f'#EXT-X-STREAM-INF:BANDWIDTH=1,NAME="{safe_name}"',
            target_url,
            "",
        ]
    )


def load_existing_index(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def choose_target_url(
    slug: str,
    playlist_url: str,
    wrapper_path: Path,
    old_index: dict[str, dict[str, object]],
) -> tuple[str, bool]:
    existing_target = read_wrapper_target(wrapper_path)
    if not existing_target:
        return playlist_url, False

    previous_auto_url = str(old_index.get(slug, {}).get("auto_source_url") or "")
    if previous_auto_url:
        if existing_target != previous_auto_url:
            return existing_target, True
        return playlist_url, False

    if existing_target != playlist_url:
        return existing_target, True

    return playlist_url, False


def write_rewritten_playlist(
    playlist_path: Path,
    header: str,
    entries: list[dict[str, object]],
    slugs: list[str],
    public_base_url: str,
) -> None:
    lines = [header]
    for entry, slug in zip(entries, slugs):
        lines.append(str(entry["extinf"]))
        lines.extend(str(extra) for extra in entry["extra"])
        lines.append(f"{public_base_url.rstrip('/')}/{slug}.m3u8")
    playlist_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    playlist_path = Path(args.playlist)
    output_dir = Path(args.output_dir)
    index_path = Path(args.index_file) if args.index_file else output_dir / "index.json"

    header, entries = parse_m3u(playlist_path)
    slugs = build_slug_plan(entries)

    output_dir.mkdir(parents=True, exist_ok=True)
    old_index = load_existing_index(index_path)

    new_index: dict[str, dict[str, object]] = {}
    kept_files = {index_path.name}
    manual_overrides = 0

    for entry, slug in zip(entries, slugs):
        wrapper_path = output_dir / f"{slug}.m3u8"
        kept_files.add(wrapper_path.name)

        source_url = resolve_stream_target(str(entry["url"]))
        target_url, manual_override = choose_target_url(slug, source_url, wrapper_path, old_index)
        manual_overrides += int(manual_override)

        wrapper_path.write_text(
            wrapper_contents(str(entry["name"]), target_url),
            encoding="utf-8",
        )

        new_index[slug] = {
            "name": str(entry["name"]),
            "tvg_id": str(entry["tvg_id"]),
            "playlist_source_url": source_url,
            "auto_source_url": source_url,
            "wrapper_target_url": target_url,
            "public_url": f"{args.public_base_url.rstrip('/')}/{slug}.m3u8",
            "mode": "manual" if target_url != source_url else "auto",
        }

    for path in output_dir.glob("*.m3u8"):
        if path.name not in kept_files:
            path.unlink()

    index_path.write_text(
        json.dumps(dict(sorted(new_index.items())), indent=2) + "\n",
        encoding="utf-8",
    )

    write_rewritten_playlist(
        playlist_path=playlist_path,
        header=header,
        entries=entries,
        slugs=slugs,
        public_base_url=args.public_base_url,
    )

    print(f"Generated {len(entries)} wrapper playlists in {output_dir}")
    if manual_overrides:
        print(f"Preserved {manual_overrides} manual wrapper override(s)")


if __name__ == "__main__":
    main()
