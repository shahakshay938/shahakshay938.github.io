# 🔄 IPTV Automation Life-Cycle

This document visualizes the 24-hour cycle of your IPTV playlist management system.

## 📅 Daily 3:00 AM IST Flow

```mermaid
graph TD
    A[3:00 AM IST Trigger] --> B[Sync Repositories]
    B --> C[Download Fresh Sources in.m3u]
    C --> D[merge_playlists.py]
    D --> E[Fusion Base: March 19]
    E --> F[check_streams.py]
    F --> G[Latency Check: Purge > 5s]
    G --> H[detect_loops.py]
    H --> I[HLS Sequence Scan: Purge Loops]
    I --> J[filter_playlist.py]
    J --> K[Atomic Update: latest.m3u]
    K --> L[Archive To: backups/]
    L --> M[Push to Master: Live in TiViMate]
```

---

## 🛠️ Logic Breakdown

### 1. Permanent Baseline Fusion
*   **The Key:** The **March 19 Stable Version** (Commit `41c1df6`) is now the permanent base for every daily update.
*   **The Strategy:** We only add *new* streams found in external sources to this stable foundation. This ensures your preferred 2-stream Sony SAB setup never changes.

### 2. High-Performance Filtering
*   **Latency Gate:** If a stream takes more than 5 seconds to load on the GitHub runner, it's purged. This ensures your channel switching feels "Instant".
*   **Media Sequence Monitoring:** We monitor the internal HLS manifest. If a stream repeats the same segments twice in 15 seconds, it is marked as **LOOPING** and removed to prevent frustration.

### 3. Safety Snapshot
*   **The Backup:** Every single run creates a dated snapshot. 
*   **Historical Access:** You can always access your historical playlist state at:  
`https://shahakshay938.github.io/backups/playlist-YYYY-MM-DD.m3u`
