# Playlist Sources

This directory holds the **permanent base playlist** — the hand-curated set of streams
that forms the foundation for every daily merge. Automation never overwrites this file.

## Files

| File | Purpose |
|------|---------|
| `base.m3u` | Permanent base — Astra private streams, manually verified channels, dual-stream Sony setup. **Never touched by GitHub Actions.** |

## How merging works

Every daily run:
1. Starts with `sources/base.m3u` (permanent curated base)
2. Pulls fresh streams from each online source listed in `update-playlist.yml`
3. Additively merges: new URLs are added, existing URLs get refreshed metadata
4. Runs stream verification (ffprobe latency + HLS loop detection)
5. Removes failing streams, writes filtered result to `latest.m3u`

## Adding a new source

In `.github/workflows/update-playlist.yml`, add a `curl` download step and pass the
downloaded file to `scripts/merge_playlists.py` as an additional argument. The merge
script accepts unlimited source files — each is merged left-to-right into the result.

## Protected channels

Channels with these labels in their name survive filtering even if ffprobe marks them slow:
- `(Jio Proxy)` — alternate routing
- `(Google DAI)` — dynamic ad insertion streams
- `(Stable Restream)` — injected via `scripts/inject_stable.py`
