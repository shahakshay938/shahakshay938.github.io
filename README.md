# 🛡️ IPTV Playlist Maintenance System

This repository hosts an automated mechanism built to maintain a **100% stable, high-performance** IPTV playlist.

## 🚀 Core Links
| Type | Format | URL |
| :--- | :--- | :--- |
| **Stable File** | M3U Playlist | `https://shahakshay938.github.io/latest.m3u` |
| **Stable File** | EPG Guide | `https://shahakshay938.github.io/epg.xml.gz` |
| **Backup File** | M3U Playlist | `https://shahakshay938.github.io/backups/playlist-2026-03-31.m3u` |
| **Base File** | M3U Playlist | `https://shahakshay938.github.io/backups/playlist-2026-03-19.m3u` |

---

## 📡 1. Multi-Source Integration (HD/SD Strategy)
*   **Final Sony SAB Preference:** Per the stable state from **March 19**, the playlist is locked to exactly **2 distinct Sony SAB streams** (SD and HD). This prevents the "Multi-Source" clutter shown in recent automated tests.
*   **Additive Merge:** For all other channels, the system preserves **HD** and **SD** variants as separate entries.
*   **Manual Overrides:** Custom Jio Proxy and Google DAI streams are protected and prioritized.
*   **Unique Stream Verification:** The merge logic uses the **Stream URL** as the primary key. If a channel has multiple URLs, all functional versions are kept.

---

## 🕵️ 2. The "Quality Pulse" Engine (Daily Verification)
Every 24 hours, the system executes recursive checks to ensure zero "Dead" or "Looping" channels:

### A. Latency & Reachability (`check_streams.py`)
*   **Engine:** Uses `ffprobe` to attempt a real-time stream decode.
*   **Threshold:** Any channel with a LOAD time **> 5 seconds** is automatically purged.
*   **Video Validation:** Confirms a real video stream (v:0) is present.

### B. Loop Detection (`detect_loops.py`)
*   **The Problem:** Many restreams "loop" (circular buffering).
*   **Mechanism:** Monitors the `EXT-X-MEDIA-SEQUENCE` in the HLS playlist over a 15-second window.
*   **The Purge:** If the sequence doesn't advance, the stream is flagged as **Looping** and removed.

---

## 💾 3. Automated Daily Backups
The system features a robust archival mechanism to prevent data loss:
*   **Folder:** All backups are stored in the [**`backups/`**](https://github.com/shahakshay938/shahakshay938.github.io/tree/master/backups) directory.
*   **Format:** Files are suffixed with the date: `playlist-YYYY-MM-DD.m3u`.
*   **Restoration:** You can always revert to a previous day's state by using the dated URLs.

---

## 🤖 4. GitHub Action Automation
The entire pipeline is automated in `.github/workflows/update-playlist.yml`:
1.  **3:00 AM IST:** Script clones the repo.
2.  **Merge:** `merge_playlists.py` fusions sources (keeping HD/SD separate).
3.  **Pulse:** `detect_loops.py` and `check_streams.py` purge malfunctioning links.
4.  **Backup:** Copies the current stable state to the `backups/` folder.
5.  **Push:** Optimized files and dated backups are pushed to the master branch.

---
> [!IMPORTANT]
> **Total Verified Channels (Current):** 350
> **Status:** 100% Automated | Multi-Variant Enabled | Daily Backups Active