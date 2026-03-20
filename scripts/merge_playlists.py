#!/usr/bin/env python3
"""
merge_playlists.py — Merge IPTV playlists with focus on updating existing channels.
- Takes the existing rich playlist as the base.
- Updates stream URLs and headers from iptv-org for existing channels.
- Protects manual overrides (Sony SAB variants).
- Avoids adding completely new channels by default to keep the list clean.
"""

import re
import sys
import os

def parse_m3u(filepath):
    """Parse an M3U file into a list of channel dicts."""
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
    """Normalize channel name for basic comparison."""
    name = name.strip().lower()
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def get_quality_score(name, url):
    """Return a score based on perceived quality (HD > SD)."""
    score = 0
    nl = name.lower()
    if '1080p' in nl or 'fhd' in nl or '4k' in nl: score += 10
    if '720p' in nl or 'hd' in nl: score += 5
    if '576p' in nl or 'sd' in nl: score += 1
    # Prefer Jio Proxy URLs if present
    if '103.162.136.235' in url: score += 2
    return score

def clean_display_name(name):
    """Strip quality tags for a 'Single' channel experience."""
    name = re.sub(r'\s*\(?\d+p\)?\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\[Not 24/7\]\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*(SD|HD|FHD)\s*', '', name, flags=re.IGNORECASE)
    return name.strip()

def merge_playlists(existing_path, new_path, output_path, changelog_path=None):
    print(f"Loading existing playlist: {existing_path}")
    existing = parse_m3u(existing_path)
    print(f"  Found {len(existing)} channels")

    print(f"Loading fresh source: {new_path}")
    new_channels = parse_m3u(new_path)
    print(f"  Found {len(new_channels)} fresh channels")

    # Index new channels for fast lookup
    new_by_tvg_id = {}
    new_by_name = {}
    for ch in new_channels:
        if ch['tvg_id_base']:
            if ch['tvg_id_base'] not in new_by_tvg_id:
                new_by_tvg_id[ch['tvg_id_base']] = []
            new_by_tvg_id[ch['tvg_id_base']].append(ch)
        if ch['name']:
            norm = normalize_name(ch['name'])
            if norm not in new_by_name:
                new_by_name[norm] = []
            new_by_name[norm].append(ch)

    updated = 0
    modified_channels = []

    for ch in existing:
        # PROTECTION: Skip updating if the channel is a manual variant or has custom UA
        # We only update the "Standard" channels from the source.
        if '(Jio Proxy)' in ch['name'] or '(Google DAI)' in ch['name'] or 'user-agent' in ch['extinf'].lower():
            continue

        matched = None
        # Priority 1: Match by full tvg-id
        if ch['tvg_id'] and ch['tvg_id'] in new_by_tvg_id:
            matched = new_by_tvg_id[ch['tvg_id']]
        # Priority 2: Match by base tvg-id (@ part removed)
        elif ch['tvg_id_base'] and ch['tvg_id_base'] in new_by_tvg_id:
            matched = new_by_tvg_id[ch['tvg_id_base']]
        # Priority 3: Match by normalized name
        elif ch['name']:
            norm = normalize_name(ch['name'])
            if norm in new_by_name:
                matched = new_by_name[norm]

        if matched and matched[0]['url']:
            # ALWAYS update to ensure fresh parameters/tokens
            ch['url'] = matched[0]['url']
            ch['extra'] = matched[0].get('extra', [])
            updated += 1
            modified_channels.append({'name': ch['name']})

    # Step 1: Group by tvg_id (primary) or normalized name (fallback)
    # This allows us to find SD/HD variants of the same channel.
    groups = {}
    for ch in existing:
        key = ch['tvg_id_base'] if ch['tvg_id_base'] else normalize_name(ch['name'])
        if key not in groups:
            groups[key] = []
        groups[key].append(ch)

    final_list = []
    for key, variants in groups.items():
        # Step 2: Select the best variant based on quality score
        best_ch = max(variants, key=lambda c: get_quality_score(c['name'], c['url']))
        
        # Step 3: Clean the display name for a "Single" experience
        origin_name = best_ch['name']
        best_ch['name'] = clean_display_name(origin_name)
        # Update the name in EXTINF as well
        best_ch['extinf'] = best_ch['extinf'].replace(f',{origin_name}', f',{best_ch["name"]}')
        
        final_list.append(best_ch)

    print(f"  Consolidated {len(existing)} variants into {len(final_list)} single channels")

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for ch in final_list:
            f.write(ch['extinf'] + '\n')
            for extra in ch.get('extra', []):
                f.write(extra + '\n')
            f.write(ch['url'] + '\n')

    print(f"\n✅ Merged: {len(final_list)} high-quality channels synchronized.")

if __name__ == '__main__':
    if len(sys.argv) >= 4:
        merge_playlists(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        print("Usage: merge_playlists.py <existing.m3u> <source.m3u> <output.m3u> [changelog.md]")
        sys.exit(1)
