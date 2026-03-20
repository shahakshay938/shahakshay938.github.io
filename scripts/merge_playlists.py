#!/usr/bin/env python3
"""
merge_playlists.py — Merge IPTV playlists with automated overrides
- Takes the existing rich playlist as the base.
- Updates stream URLs from iptv-org.
- Adds new channels from iptv-org.
- **NEW**: Loads overrides.json to automatically create (Jio) variants for major channels.
- **NEW**: Injects User-Agent headers automatically based on network or channel.
"""

import re
import sys
import os
import json

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
    """Normalize channel name for comparison."""
    name = re.sub(r'\s*\(?\d+p\)?\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\[Not 24/7\]\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*(SD|HD|FHD)\s*', '', name, flags=re.IGNORECASE)
    name = name.strip().lower()
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def guess_group(name):
    """Guess group category from channel name."""
    nl = name.lower()
    if any(w in nl for w in ['news', 'times now', 'ndtv', 'republic', 'india today', 'aaj tak', 'zee news', 'abp']):
        return 'News'
    if any(w in nl for w in ['sports', 'star sports', 'sony ten', 'cricket', 'football']):
        return 'Sports'
    if any(w in nl for w in ['mtv', 'music', 'zing', '9xm', 'b4u music', 'mastiii']):
        return 'Music'
    if any(w in nl for w in ['cartoon', 'nick', 'disney', 'hungama', 'pogo', 'sonic']):
        return 'Kids'
    if any(w in nl for w in ['movie', 'cinema', 'pictures', 'filmy', 'goldmines', 'b4u movie']):
        return 'Movies'
    if any(w in nl for w in ['discovery', 'national geographic', 'animal planet', 'history']):
        return 'Infotainment'
    if any(w in nl for w in ['aastha', 'sanskar', 'peace', 'divya', 'god', 'spiritual']):
        return 'Devotional'
    return 'Entertainment'

def apply_overrides(existing, overrides):
    """Applies overrides: injects User-Agents and creates variant channels."""
    if not overrides:
        return existing

    new_existing = []
    tvg_to_overrides = {}
    
    # Pre-process overrides for quick lookup
    for net_name, net_data in overrides.get('networks', {}).items():
        ua = net_data.get('user_agent', '')
        for ch_data in net_data.get('channels', []):
            tvg_id = ch_data['tvg_id']
            if tvg_id not in tvg_to_overrides:
                tvg_to_overrides[tvg_id] = []
            ch_data['default_ua'] = ua
            tvg_to_overrides[tvg_id].append(ch_data)

    seen_variants = set()
    for ch in existing:
        seen_variants.add(f"{ch['tvg_id']}|{ch['name']}")

    for ch in existing:
        new_existing.append(ch)
        
        # Skip if host channel already has a variant marker or User-Agent
        if '(' in ch['name'] and ')' in ch['name']:
            continue

        # Check if this base channel needs an override
        if ch['tvg_id'] in tvg_to_overrides:
            for ov in tvg_to_overrides[ch['tvg_id']]:
                # 1. Inject User-Agent into base channel if not present
                if not ch.get('user_agent') and ov.get('default_ua'):
                    ch['user_agent'] = ov['default_ua']
                    # Rebuild EXTINF to include user-agent
                    if 'user-agent="' not in ch['extinf']:
                        ch['extinf'] = ch['extinf'].replace('group-title="', f'user-agent="{ch["user_agent"]}" group-title="')

                # 2. Check if we need to create a (Jio) variant
                variant_name = f"{ch['name']} {ov['suffix']}"
                variant_key = f"{ch['tvg_id']}|{variant_name}"
                
                if variant_key not in seen_variants:
                    # Create the variant
                    v_extinf = ch['extinf'].replace(f',{ch["name"]}', f',{variant_name}')
                    # Ensure variant name is used in the name attribute too
                    v_extinf = re.sub(r'tvg-name="[^"]*"', f'tvg-name="{variant_name}"', v_extinf)
                    
                    variant_ch = {
                        'extinf': v_extinf,
                        'extra': ch['extra'].copy(),
                        'url': ov['url_pattern'],
                        'tvg_id': ch['tvg_id'],
                        'tvg_id_base': ch['tvg_id_base'],
                        'user_agent': ov['default_ua'],
                        'name': variant_name,
                        'group': ch['group'],
                    }
                    new_existing.append(variant_ch)
                    seen_variants.add(variant_key)

    return new_existing

def merge_playlists(existing_path, new_path, output_path, changelog_path=None):
    # Load Overrides
    overrides = {}
    overrides_path = os.path.join(os.path.dirname(__file__), 'overrides.json')
    if os.path.exists(overrides_path):
        try:
            with open(overrides_path, 'r') as f:
                overrides = json.load(f)
            print(f"Loaded {len(overrides.get('networks', {}))} networks from overrides.json")
        except Exception as e:
            print(f"Error loading overrides: {e}")

    print(f"Loading existing playlist: {existing_path}")
    existing = parse_m3u(existing_path)
    
    # APPLY OVERRIDES FIRST
    existing = apply_overrides(existing, overrides)
    print(f"  Processed {len(existing)} channels (including variants)")

    print(f"Loading new playlist: {new_path}")
    new_channels = parse_m3u(new_path)
    
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

    matched_new_ids = set()
    updated = 0
    modified_channels = []

    for ch in existing:
        # PROTECTION: Skip updating if the channel has a custom User-Agent 
        # or if it's a manual override variant
        if ch.get('user_agent') or ('(' in ch['name'] and ')' in ch['name']):
            continue

        matched = None
        if ch['tvg_id'] and ch['tvg_id'] in new_by_tvg_id:
            matched = new_by_tvg_id[ch['tvg_id']]
            matched_new_ids.add(ch['tvg_id'])
        elif ch['tvg_id_base'] and ch['tvg_id_base'] in new_by_tvg_id:
            matched = new_by_tvg_id[ch['tvg_id_base']]
            matched_new_ids.add(ch['tvg_id_base'])
        elif ch['name']:
            norm = normalize_name(ch['name'])
            if norm in new_by_name:
                matched = new_by_name[norm]
                matched_new_ids.add(norm)

        if matched and matched[0]['url'] and matched[0]['url'] != ch['url']:
            old_url = ch['url']
            ch['url'] = matched[0]['url']
            updated += 1
            modified_channels.append({'name': ch['name'], 'old_url': old_url[:50], 'new_url': ch['url'][:50]})

    added_channels = []
    seen_new = set()
    for ch in new_channels:
        tvg_base = ch['tvg_id_base']
        norm_name = normalize_name(ch['name']) if ch['name'] else ''
        if tvg_base in matched_new_ids or norm_name in matched_new_ids:
            continue
        dedup_key = f"{tvg_base}|{ch['url']}"
        if dedup_key in seen_new:
            continue
        seen_new.add(dedup_key)
        
        group = guess_group(ch['name']) if ch['name'] else 'Other'
        extinf = f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-name="{ch["name"]}" group-title="{group}",{ch["name"]}'
        added_channels.append({'extinf': extinf, 'extra': ch.get('extra', []), 'url': ch['url'], 'name': ch['name']})

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for ch in existing:
            f.write(ch['extinf'] + '\n')
            for extra in ch.get('extra', []):
                f.write(extra + '\n')
            f.write(ch['url'] + '\n')
        for ch in added_channels:
            f.write(ch['extinf'] + '\n')
            for extra in ch.get('extra', []):
                f.write(extra + '\n')
            f.write(ch['url'] + '\n')

    total = len(existing) + len(added_channels)
    print(f"\n✅ Merged: {total} channels. {updated} URLs updated. {len(added_channels)} new.")

if __name__ == '__main__':
    if len(sys.argv) >= 4:
        merge_playlists(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        print("Usage: merge_playlists.py <existing> <new> <output> [changelog]")
        sys.exit(1)
