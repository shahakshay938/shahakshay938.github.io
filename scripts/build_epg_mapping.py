#!/usr/bin/env python3
"""
build_epg_mapping.py — Build and maintain JioTV EPG → Playlist channel ID mapping

This script:
1. Extracts all channels from the JioTV EPG (numeric IDs + display names + logos)
2. Extracts all channels from our M3U playlist (text tvg-ids + display names)
3. Auto-maps them using fuzzy name matching
4. Saves the mapping as channel_mapping.json for manual review & overrides
5. Updates the M3U playlist with a `jiotv-id` custom attribute on each matched channel
6. Converts the JioTV EPG XML to use our tvg-id format so players can match them

Usage:
  python3 build_epg_mapping.py <playlist.m3u> <jiotv_epg.xml.gz> <output_epg.xml.gz> [mapping.json]
"""

import re
import sys
import json
import gzip
import os

def normalize(name):
    """Normalize channel name for fuzzy matching."""
    name = name.strip().lower()
    # Remove quality/resolution tags
    name = re.sub(r'\s*\(?\d+p\)?\s*', '', name)
    name = re.sub(r'\s*\[not 24/7\]\s*', '', name)
    # Remove HD/SD/FHD suffix
    name = re.sub(r'\s+(hd|sd|fhd|uhd|4k)\s*$', '', name)
    name = re.sub(r'\s+(hd|sd|fhd|uhd|4k)\s+', ' ', name)
    # Remove common suffixes
    name = re.sub(r'\s*\d+$', '', name)  # trailing numbers like "2"
    # Keep only alphanumeric
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def extract_jiotv_channels(epg_path):
    """Extract channel info from JioTV EPG XML."""
    if epg_path.endswith('.gz'):
        with gzip.open(epg_path, 'rt', encoding='utf-8', errors='replace') as f:
            data = f.read()
    else:
        with open(epg_path, 'r', encoding='utf-8', errors='replace') as f:
            data = f.read()

    channels = {}
    # Match channel definitions
    for match in re.finditer(r'<channel\s+id="([^"]*)">\s*<display-name>([^<]*)</display-name>(?:\s*<icon\s+src="([^"]*)")?', data):
        cid, name, icon = match.group(1), match.group(2).strip(), match.group(3) or ''
        channels[cid] = {
            'id': cid,
            'name': name,
            'icon': icon,
            'normalized': normalize(name),
        }

    return channels, data

def extract_playlist_channels(m3u_path):
    """Extract channel info from M3U playlist."""
    channels = []
    with open(m3u_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
            tvg_id = tvg_id_match.group(1) if tvg_id_match else ''
            name_match = re.search(r',(.+)$', line)
            display_name = name_match.group(1).strip() if name_match else ''
            tvg_name_match = re.search(r'tvg-name="([^"]*)"', line)
            tvg_name = tvg_name_match.group(1) if tvg_name_match else display_name

            channels.append({
                'tvg_id': tvg_id,
                'tvg_id_base': tvg_id.split('@')[0] if tvg_id else '',
                'name': display_name,
                'tvg_name': tvg_name,
                'normalized': normalize(display_name),
                'normalized_tvg': normalize(tvg_name),
                'line_num': i,
                'extinf': line,
            })
        i += 1

    return channels, lines

def build_mapping(playlist_channels, jiotv_channels):
    """Build mapping between playlist tvg-ids and JioTV numeric IDs."""
    mapping = {}
    unmatched_playlist = []
    unmatched_jiotv = list(jiotv_channels.keys())

    # Build JioTV lookup by normalized name
    jiotv_by_norm = {}
    for cid, ch in jiotv_channels.items():
        norm = ch['normalized']
        if norm not in jiotv_by_norm:
            jiotv_by_norm[norm] = []
        jiotv_by_norm[norm].append(ch)

    for pch in playlist_channels:
        matched = None
        match_method = ''

        # Strategy 1: Exact normalized name match
        norm = pch['normalized']
        if norm in jiotv_by_norm:
            matched = jiotv_by_norm[norm][0]
            match_method = 'exact_name'

        # Strategy 2: Try tvg-name normalized
        if not matched and pch['normalized_tvg'] != norm:
            if pch['normalized_tvg'] in jiotv_by_norm:
                matched = jiotv_by_norm[pch['normalized_tvg']][0]
                match_method = 'tvg_name'

        # Strategy 3: Partial match (our name contains JioTV name or vice versa)
        if not matched:
            for jnorm, jchs in jiotv_by_norm.items():
                if len(jnorm) >= 4 and len(norm) >= 4:
                    if jnorm in norm or norm in jnorm:
                        matched = jchs[0]
                        match_method = 'partial'
                        break

        # Strategy 4: Word-level matching (at least 2 shared words)
        if not matched:
            pwords = set(norm.split())
            if len(pwords) >= 2:
                best_score = 0
                for jnorm, jchs in jiotv_by_norm.items():
                    jwords = set(jnorm.split())
                    common = pwords & jwords
                    score = len(common) / max(len(pwords), len(jwords))
                    if score > best_score and score >= 0.6:
                        best_score = score
                        matched = jchs[0]
                        match_method = f'word_match({score:.0%})'

        if matched:
            key = pch['tvg_id'] or pch['name']
            mapping[key] = {
                'tvg_id': pch['tvg_id'],
                'playlist_name': pch['name'],
                'jiotv_id': matched['id'],
                'jiotv_name': matched['name'],
                'jiotv_icon': matched['icon'],
                'match_method': match_method,
                'verified': match_method == 'exact_name',
            }
            if matched['id'] in unmatched_jiotv:
                unmatched_jiotv.remove(matched['id'])
        else:
            unmatched_playlist.append({
                'tvg_id': pch['tvg_id'],
                'name': pch['name'],
            })

    return mapping, unmatched_playlist, unmatched_jiotv

def update_playlist_with_jiotv_ids(lines, playlist_channels, mapping):
    """Add jiotv-id attribute to each matched channel in the M3U."""
    updated_lines = list(lines)

    for pch in playlist_channels:
        key = pch['tvg_id'] or pch['name']
        if key in mapping:
            m = mapping[key]
            jiotv_id = m['jiotv_id']
            jiotv_icon = m['jiotv_icon']
            old_line = pch['extinf']

            # Add jiotv-id attribute if not already present
            if 'jiotv-id=' not in old_line:
                # Insert jiotv-id after tvg-id
                new_line = re.sub(
                    r'(tvg-id="[^"]*")',
                    rf'\1 jiotv-id="{jiotv_id}"',
                    old_line
                )
            else:
                # Update existing jiotv-id
                new_line = re.sub(
                    r'jiotv-id="[^"]*"',
                    f'jiotv-id="{jiotv_id}"',
                    old_line
                )

            # Update logo if empty and JioTV has one
            if jiotv_icon and 'tvg-logo=""' in new_line:
                new_line = new_line.replace('tvg-logo=""', f'tvg-logo="{jiotv_icon}"')

            updated_lines[pch['line_num']] = new_line + '\n'

    return updated_lines

def convert_epg_ids(epg_data, mapping):
    """Convert JioTV EPG XML to use our tvg-id format."""
    # Build reverse mapping: jiotv_id -> tvg_id
    reverse_map = {}
    for key, m in mapping.items():
        reverse_map[m['jiotv_id']] = m['tvg_id']

    converted = 0

    def replace_channel_id(match):
        nonlocal converted
        jiotv_id = match.group(1)
        if jiotv_id in reverse_map:
            converted += 1
            return f'channel="{reverse_map[jiotv_id]}"'
        return match.group(0)

    def replace_channel_def_id(match):
        jiotv_id = match.group(1)
        if jiotv_id in reverse_map:
            return f'id="{reverse_map[jiotv_id]}"'
        return match.group(0)

    # Replace IDs in <channel id="..."> and <programme channel="...">
    result = re.sub(r'id="(\d+)"', replace_channel_def_id, epg_data)
    result = re.sub(r'channel="(\d+)"', replace_channel_id, result)

    return result, converted

def main():
    if len(sys.argv) < 4:
        print("Usage: python3 build_epg_mapping.py <playlist.m3u> <jiotv_epg.xml.gz> <output_epg.xml.gz> [mapping.json]")
        sys.exit(1)

    m3u_path = sys.argv[1]
    epg_path = sys.argv[2]
    output_epg_path = sys.argv[3]
    mapping_path = sys.argv[4] if len(sys.argv) > 4 else 'channel_mapping.json'

    print("=" * 60)
    print("🔄 JioTV EPG → Playlist Channel Mapper")
    print("=" * 60)

    # Load existing mapping for manual overrides
    existing_mapping = {}
    if os.path.exists(mapping_path):
        with open(mapping_path, 'r') as f:
            existing_mapping = json.load(f)
        print(f"📋 Loaded {len(existing_mapping)} existing mappings from {mapping_path}")

    # Extract channels
    print(f"\n📡 Extracting JioTV channels from: {epg_path}")
    jiotv_channels, epg_data = extract_jiotv_channels(epg_path)
    print(f"   Found {len(jiotv_channels)} JioTV channels")

    print(f"\n📺 Extracting playlist channels from: {m3u_path}")
    playlist_channels, m3u_lines = extract_playlist_channels(m3u_path)
    print(f"   Found {len(playlist_channels)} playlist channels")

    # Build mapping
    print(f"\n🔗 Building channel mapping...")
    auto_mapping, unmatched_playlist, unmatched_jiotv = build_mapping(playlist_channels, jiotv_channels)

    # Merge with existing overrides (manual overrides take precedence)
    for key, val in existing_mapping.items():
        if val.get('manual_override', False):
            auto_mapping[key] = val

    # Stats
    exact = sum(1 for v in auto_mapping.values() if v['match_method'] == 'exact_name')
    partial = sum(1 for v in auto_mapping.values() if 'partial' in v['match_method'])
    word = sum(1 for v in auto_mapping.values() if 'word_match' in v['match_method'])
    manual = sum(1 for v in auto_mapping.values() if v.get('manual_override', False))

    print(f"\n📊 Mapping Results:")
    print(f"   ✅ Total mapped: {len(auto_mapping)}")
    print(f"      - Exact name match: {exact}")
    print(f"      - tvg-name match: {sum(1 for v in auto_mapping.values() if v['match_method'] == 'tvg_name')}")
    print(f"      - Partial match: {partial}")
    print(f"      - Word match: {word}")
    print(f"      - Manual override: {manual}")
    print(f"   ❌ Unmatched playlist channels: {len(unmatched_playlist)}")
    print(f"   ❌ Unmatched JioTV channels: {len(unmatched_jiotv)}")

    # Save mapping
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(auto_mapping, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Mapping saved to: {mapping_path}")

    # Update playlist with jiotv-id attributes
    print(f"\n📝 Updating playlist with jiotv-id attributes...")
    updated_lines = update_playlist_with_jiotv_ids(m3u_lines, playlist_channels, auto_mapping)
    with open(m3u_path, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)
    print(f"   Updated {len(auto_mapping)} channels in {m3u_path}")

    # Convert EPG IDs and save
    print(f"\n🔄 Converting JioTV EPG IDs to playlist format...")
    converted_epg, converted_count = convert_epg_ids(epg_data, auto_mapping)
    print(f"   Converted {converted_count} programme entries")

    with gzip.open(output_epg_path, 'wt', encoding='utf-8') as f:
        f.write(converted_epg)
    output_size = os.path.getsize(output_epg_path)
    print(f"   Saved converted EPG to: {output_epg_path} ({output_size / 1024:.0f}KB)")

    # Write summary to GITHUB_STEP_SUMMARY if available
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_file:
        with open(summary_file, 'a', encoding='utf-8') as f:
            f.write(f"\n## 🔗 EPG Channel Mapping\n")
            f.write(f"- **Mapped:** {len(auto_mapping)} channels\n")
            f.write(f"- **Unmatched (playlist):** {len(unmatched_playlist)}\n")
            f.write(f"- **Converted programmes:** {converted_count}\n")

    # Print unmatched for debugging
    if unmatched_playlist:
        print(f"\n⚠️  Unmatched playlist channels (need manual mapping):")
        for ch in sorted(unmatched_playlist, key=lambda x: x['name'])[:20]:
            print(f"   - {ch['name']} (tvg-id: {ch['tvg_id']})")
        if len(unmatched_playlist) > 20:
            print(f"   ... and {len(unmatched_playlist) - 20} more")

    print(f"\n✅ Done! EPG mapping complete.")

if __name__ == '__main__':
    main()
