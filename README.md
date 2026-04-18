# 🛡️ IPTV Playlist Maintenance System

Automated pipeline to maintain a stable, verified Indian IPTV playlist with EPG guide.

## 🚀 Core Links

| Type | Format | URL |
| :--- | :--- | :--- |
| **Stable Playlist** | M3U | `https://shahakshay938.github.io/latest.m3u` |
| **EPG Guide** | XMLTV (gz) | `https://shahakshay938.github.io/epg.xml.gz` |
| **Latest Backup** | M3U | `https://shahakshay938.github.io/backups/playlist-2026-04-18.m3u` |
| **Permanent Base** | M3U | `https://shahakshay938.github.io/sources/base.m3u` |

---

## 📁 Repository Structure

```
shahakshay938.github.io/
├── .github/workflows/
│   ├── update-playlist.yml   # Daily 3 AM IST — stream verification + playlist update
│   └── update-epg.yml        # Every 6 hours — EPG refresh (JioTV → epg.pw fallback)
├── scripts/                  # All Python processing scripts
├── sources/
│   └── base.m3u              # Permanent hand-curated base — never modified by automation
├── backups/
│   ├── playlist-YYYY-MM-DD.m3u   # Daily playlist snapshots (14-day retention)
│   └── epg/
│       └── epg-YYYY-MM-DD.xml.gz # EPG snapshots (7-day retention)
├── latest.m3u                # Live verified playlist
├── epg.xml.gz                # Current EPG guide
└── channel_mapping.json      # JioTV → tvg-id channel mapping
```

---

## 📡 Multi-Source Integration

- **Permanent base** (`sources/base.m3u`) — hand-curated channels including Astra private streams, dual Sony SAB streams, Jio Proxy routes. Never touched by automation.
- **Daily sources** — iptv-org India + any additional sources configured in the workflow.
- **Additive merge** — new stream URLs are added; existing URLs get refreshed metadata; manual overrides (`(Jio Proxy)`, `(Google DAI)`, `(Stable Restream)`) are always preserved.
- **HD/SD variants** — kept as separate entries using stream URL as the unique key.

---

## 🕵️ Daily Stream Verification (3 AM IST)

1. **Download** fresh iptv-org India streams
2. **Merge** with permanent base (additive, URL-keyed)
3. **ffprobe check** — latency > 10s → removed; no video stream → removed
4. **Loop detection** — `EXT-X-MEDIA-SEQUENCE` monitored over 15s; stuck streams → removed
5. **Standardize** — VLC network options, timeshift, aspect-ratio applied uniformly
6. **Normalize categories** — single genre per channel, consistent group-title values
7. **Filter** — only verified streams survive to `latest.m3u`
8. **Backup** — previous `latest.m3u` archived to `backups/playlist-YYYY-MM-DD.m3u`

---

## 📋 EPG Updates (Every 6 Hours)

| Priority | Source | Method |
| :--- | :--- | :--- |
| Primary | JioTV (mitthu786/tvepg) | Fuzzy-mapped via `build_epg_mapping.py` — numeric JioTV IDs converted to our `tvg-id` format |
| Fallback | epg.pw India | Used directly — IDs natively match `ChannelName.in` tvg-id format |

EPG backup archived to `backups/epg/epg-YYYY-MM-DD.xml.gz` (7-day retention).

---

## 💾 Backup Restoration

Navigate to `backups/` and use the dated file URL directly in any IPTV player.
Backups are kept for 14 days (playlists) and 7 days (EPG).
The permanent base at `sources/base.m3u` is always available as a stable fallback.

---

> [!IMPORTANT]
> **Total Verified Channels (Current):** 424
> **Status:** 100% Automated | Multi-Variant | Daily Backups | EPG Every 6h
