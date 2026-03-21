# 🛠️ IPTV System Maintenance Guide

This guide explains how to maintain, troubleshoot, and revise the automated IPTV playlist system.

## 📁 Repository Structure
*   **`.github/workflows/update-playlist.yml`**: The "Heart" of the system. Controls the daily 3 AM IST schedule.
*   **`backups/playlist-2026-03-19.m3u`**: The **Permanent Base** used for every daily fusion.
*   **`scripts/`**: Contains the Python logic engines.
*   **`latest.m3u`**: The live, optimized playlist file.
*   **`backups/`**: Historical snapshots for manual recovery.

---

## 🔧 Common Revisions

### 1. Adding a New Stream Source
If you find a new M3U source you want to integrate:
1.  Open `.github/workflows/update-playlist.yml`.
2.  Add a `curl` command to download the new source in the "Download latest streams" step.
3.  Add the new file as a "Fresh" source in the `merge_playlists.py` execution line.

### 2. Changing the Latency Threshold
If you want to be stricter (fewer, faster channels) or more lenient (more channels, slower loading):
1.  Open `scripts/filter_playlist.py`.
2.  Change the `LATENCY_THRESHOLD` value (default is `5.0` seconds).

### 3. Protecting a Specific Channel
The system already protects channels with `(Jio Proxy)`, `(Google DAI)`, or `(Stable Restream)` in their names. 
To protect a new type:
1.  Open `scripts/filter_playlist.py`.
2.  Add your new keyword to the `is_manual` check.

---

## 💾 How to Restore a Backup
If the live `latest.m3u` becomes unstable:
1.  Go to the [**`backups/`**](https://github.com/shahakshay938/shahakshay938.github.io/tree/master/backups) folder.
2.  Identify a stable date (e.g., `playlist-2026-03-21.m3u`).
3.  Copy the content of that backup into your live `latest.m3u` file.
4.  Commit and Push.

---

## 🏃 Local Execution
To run the verification pulse manually on your own machine:
1.  Navigate to the `scripts/` folder.
2.  Run: `python3 check_streams.py`
3.  Run: `python3 detect_loops.py`
4.  Run: `python3 filter_playlist.py`
*Ensure `ffprobe` is installed on your system.
