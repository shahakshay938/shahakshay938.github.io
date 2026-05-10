#!/usr/bin/env python3
"""
merge_playlists.py — Multi-Source IPTV Fusion Engine
===================================================
This script is the core of the playlist management system. 
It performs an additive merge of various M3U sources while preserving 
resolution variants (HD/SD) and protecting manual overrides.

LOGIC FLOW:
1. Parse Existing Playlist: Loads current channels from 'latest.m3u'.
2. Parse Fresh Source: Loads latest channels from sources like 'in.m3u' or JioTV.
3. Additive Merge: 
   - If a stream URL is NEW, it is added as a new entry (restores HD/SD variants).
   - If a stream URL is ALREADY KNOWN, it updates metadata but preserves manual labels.
4. Deduplication: Removes exact URL duplicates to keep the file lean.
"""

import re
import sys
import os

def parse_m3u(filepath):
    """
    Parses an M3U file into a structured list of dictionaries.
    Handles #EXTINF tags, custom headers (#EXTVLCOPT), and stream URLs.
    """
    channels = []
    if not os.path.exists(filepath):
        return channels
        
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            extinf_line = line
            extra_lines = []
            url = ''
            i += 1
            # Capture any extra tags or headers before the URL
            while i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith('#EXT'):
                    extra_lines.append(next_line)
                    i += 1
                elif next_line and not next_line.startswith('#'):
                    url = next_line
                    i += 1
                    break
                else:
                    i += 1
                    break

            # Metadata Extraction
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', extinf_line)
            tvg_id = tvg_id_match.group(1) if tvg_id_match else ''
            
            ua_match = re.search(r'user-agent="([^"]*)"', extinf_line)
            user_agent = ua_match.group(1) if ua_match else ''

            name_match = re.search(r',(.+)$', extinf_line)
            display_name = name_match.group(1).strip() if name_match else ''
            
            group_match = re.search(r'group-title="([^"]*)"', extinf_line)
            group = group_match.group(1) if group_match else ''

            channels.append({
                'extinf': extinf_line,
                'extra': extra_lines,
                'url': url,
                'tvg_id': tvg_id,
                'tvg_id_base': tvg_id.split('@')[0] if tvg_id else '',
                'user_agent': user_agent,
                'name': display_name,
                'group': group,
            })
        else:
            i += 1
    return channels

def normalize_name(name):
    """Simplifies channel names for resilient comparison (lowercase, alphanumeric)."""
    name = name.strip().lower()
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def merge_playlists(existing_path, new_path, output_path, changelog_path=None):
    """
    Main merge orchestrator. Performs an additive fusion of existing and fresh sources.
    Uses 'URL' as the unique identifier to ensure HD/SD variants stay separate.
    """
    print(f"Loading existing playlist: {existing_path}")
    existing = parse_m3u(existing_path)
    print(f"  Found {len(existing)} channels")

    print(f"Loading fresh source: {new_path}")
    new_channels = parse_m3u(new_path)
    print(f"  Found {len(new_channels)} fresh channels")

    # Step 1: Combine New channels into Existing
    # We use URL as the anchor to avoid losing HD/SD quality variants.
    updated = 0
    new = 0
    
    # NEW: Logo Lookup Cache
    logo_cache = {}
    logo_file = 'scripts/logos.json'
    if os.path.exists(logo_file):
        import json
        try:
            with open(logo_file, 'r') as f:
                # Map channel ID to logo URL
                logo_cache = {l.get('channel', ''): l.get('url', '') for l in json.load(f) if l.get('channel')}
        except Exception as e:
            print(f"  ⚠️  Failed to load logos.json: {e}")

    def get_logo(extinf):
        match = re.search(r'tvg-logo="([^"]*)"', extinf)
        return match.group(1) if match else ''

    def inject_logo(extinf, logo_url):
        if not logo_url: return extinf
        if 'tvg-logo=""' in extinf:
            return extinf.replace('tvg-logo=""', f'tvg-logo="{logo_url}"')
        if 'tvg-logo=' not in extinf:
            # Insert before the last comma
            return re.sub(r',(.+)$', f' tvg-logo="{logo_url}",\\1', extinf)
        return extinf

    # NEW: Restriction logic for specific channels the user wants simplified (e.g. Sony SAB)
    SIMPLIFIED_IDS = ["SonySAB.in", "SonyPal.in"]
    
    for ch in new_channels:
        # 1. Protection for Simplified IDs
        if ch['tvg_id'] in SIMPLIFIED_IDS:
            existing_for_id = [e for e in existing if e['tvg_id'] == ch['tvg_id']]
            if len(existing_for_id) >= 2:
                url_exists = any(ex['url'] == ch['url'] for ex in existing)
                if not url_exists:
                    continue

        # 2. Regular Additive Merge Logic
        found_exact = False
        for ex_ch in existing:
            if ex_ch['url'] == ch['url']:
                # PRESERVE metadata if it's better in existing
                existing_logo = get_logo(ex_ch['extinf'])
                new_logo = get_logo(ch['extinf'])
                
                # If existing has a logo and new doesn't, preserve existing
                if existing_logo and not new_logo:
                    ch['extinf'] = inject_logo(ch['extinf'], existing_logo)
                
                # UPDATE: Refresh metadata but PROTECT manual labels (e.g. "Jio Proxy")
                if "(Jio Proxy)" not in ex_ch['name']:
                     ex_ch['name'] = ch['name']
                ex_ch['extinf'] = ch['extinf']
                ex_ch['tvg_id'] = ch['tvg_id']
                found_exact = True
                updated += 1
                break
        
        if not found_exact:
            # AUTO-FILL logo for new channels if missing
            if not get_logo(ch['extinf']) and ch['tvg_id']:
                logo_url = logo_cache.get(ch['tvg_id'])
                if logo_url:
                    ch['extinf'] = inject_logo(ch['extinf'], logo_url)
            
            existing.append(ch)
            new += 1

    # Step 2: Final Deduplication
    final_list = []
    seen = set()
    for ch in existing:
        dedup_key = f"{ch['name']}|{ch['url']}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        final_list.append(ch)

    print(f"  Final playlist contains {len(final_list)} unique streams (HD & SD separate)")

    # Step 3: Write to Disk
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for ch in final_list:
            f.write(ch['extinf'] + '\n')
            for extra in ch.get('extra', []):
                f.write(extra + '\n')
            f.write(ch['url'] + '\n')

    print(f"\n✅ Merged: {len(final_list)} high-quality channels synchronized.")

if __name__ == '__main__':
    # Usage: merge_playlists.py <base.m3u> [source1.m3u ...] <output.m3u>
    # The last argument is always the output path.
    # The first argument is the permanent base (existing channels).
    # All middle arguments are additional sources to merge in.
    if len(sys.argv) < 3:
        print("Usage: merge_playlists.py <base.m3u> [extra_source.m3u ...] <output.m3u>")
        sys.exit(1)

    base_path = sys.argv[1]
    output_path = sys.argv[-1]
    source_paths = sys.argv[2:-1]  # everything between base and output

    if not source_paths:
        # Only base + output provided: just copy base to output (no online sources)
        with open(base_path, 'rb') as src, open(output_path, 'wb') as dst:
            dst.write(src.read())
        print(f"No sources provided — copied base to {output_path}")
        sys.exit(0)

    # Merge each source sequentially into the base
    import tempfile
    current = base_path
    for i, src in enumerate(source_paths):
        is_last = (i == len(source_paths) - 1)
        dest = output_path if is_last else tempfile.mktemp(suffix='.m3u')
        print(f"\n── Merging source {i+1}/{len(source_paths)}: {src} ──")
        merge_playlists(current, src, dest)
        if not is_last and current != base_path:
            os.remove(current)
        current = dest
