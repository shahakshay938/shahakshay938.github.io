# 🔄 IPTV Automation Life-Cycle

This document visualizes the 24-hour cycle of your IPTV playlist management system.

## 📅 Daily 3:00 AM IST Flow

```mermaid
graph TD
    A[3:00 AM IST Trigger] --> B[Sync Repositories]
    B --> C[Download Fresh Sources in.m3u]
    C --> D[merge_playlists.py]
    D --> E[Fusion Base: March 19]
    E --> F[Verification: FFprobe & Loops]
    F --> G[Generate Stable streams/*.m3u8]
    G --> H{Changes Detected?}
    H -- No --> I[End: No unnecessary commits]
    H -- Yes --> J[Backup: Archive Old Stable + wrappers]
    J --> K[Update: latest.m3u & README]
    K --> L[Push to Master: Live Sync]
```

---

## 🛠️ Logic Breakdown

### 1. Permanent Baseline Fusion
*   **The Key:** The **March 19 Stable Version** (Commit `41c1df6`) is now the permanent base for every daily update.
*   **The Strategy:** We only add *new* streams found in external sources to this stable foundation. This ensures your preferred 2-stream Sony SAB setup never changes.

### 2. High-Performance Filtering
*   **Latency Gate:** If a stream takes more than 5 seconds to load on the GitHub runner, it's purged. This ensures your channel switching feels "Instant".
*   **Media Sequence Monitoring:** We monitor the internal HLS manifest. If a stream repeats the same segments twice in 15 seconds, it is marked as **LOOPING** and removed to prevent frustration.

### 3. Smart Differential Update
*   **Stable URL Layer:** The published playlist always points at repo-hosted `streams/*.m3u8` wrapper files, so upstream source swaps do not change player-facing URLs.
*   **The Check:** The system compares both `latest.m3u` and the generated `streams/` wrapper files against the current live state.
*   **The Trigger:** If and only if changes are found, the system archives the old version and pushes the update. This keeps your commit history clean and meaningful.
