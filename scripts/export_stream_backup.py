#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

try:
    from wrapper_utils import repo_wrapper_path
except ModuleNotFoundError:
    from scripts.wrapper_utils import repo_wrapper_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Snapshot the current wrapped playlist and its wrapper files into backups."
    )
    parser.add_argument("--input-playlist", required=True)
    parser.add_argument("--source-streams-dir", required=False)
    parser.add_argument("--output-playlist", required=True)
    parser.add_argument("--output-streams-dir", required=True)
    parser.add_argument("--public-base-url", required=True)
    return parser.parse_args()


def rewrite_playlist_urls(input_playlist: Path, output_playlist: Path, public_base_url: str, has_stream_snapshot: bool) -> None:
    lines = input_playlist.read_text(encoding="utf-8", errors="replace").splitlines()
    rewritten: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            wrapper_path = repo_wrapper_path(stripped)
            if wrapper_path and has_stream_snapshot:
                rewritten.append(f"{public_base_url.rstrip('/')}/{wrapper_path.name}")
                continue
        rewritten.append(line)

    output_playlist.parent.mkdir(parents=True, exist_ok=True)
    output_playlist.write_text("\n".join(rewritten) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_playlist = Path(args.input_playlist)
    source_streams_dir = Path(args.source_streams_dir) if args.source_streams_dir else None
    output_playlist = Path(args.output_playlist)
    output_streams_dir = Path(args.output_streams_dir)

    has_stream_snapshot = bool(source_streams_dir and source_streams_dir.exists())
    if has_stream_snapshot:
        if output_streams_dir.exists():
            shutil.rmtree(output_streams_dir)
        shutil.copytree(source_streams_dir, output_streams_dir)

    rewrite_playlist_urls(
        input_playlist=input_playlist,
        output_playlist=output_playlist,
        public_base_url=args.public_base_url,
        has_stream_snapshot=has_stream_snapshot,
    )

    if has_stream_snapshot:
        print(f"Archived stream wrappers to {output_streams_dir}")
    print(f"Archived playlist snapshot to {output_playlist}")


if __name__ == "__main__":
    main()
