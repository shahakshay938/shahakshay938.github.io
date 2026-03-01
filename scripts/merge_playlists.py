#!/usr/bin/env python3
"""
merge_playlists.py — Merge IPTV playlists with detailed changelog
- Takes the existing rich playlist as the base (preserves logos, groups, metadata)
- Updates stream URLs from the new iptv-org source where tvg-id matches
- Adds completely new channels from iptv-org that don't exist in the base
- Outputs a clean, merged M3U file
- Writes a detailed changelog to CHANGELOG.md for GitHub Action commits

Usage: python3 merge_playlists.py <existing.m3u> <new_iptv_org.m3u> <output.m3u> [changelog.md]
"""

import re
import sys
import os

def parse_m3u(filepath):
    """Parse an M3U file into a list of channel dicts."""
    channels = []
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

def merge_playlists(existing_path, new_path, output_path, changelog_path=None):
    print(f"Loading existing playlist: {existing_path}")
    existing = parse_m3u(existing_path)
    print(f"  Found {len(existing)} channels")

    print(f"Loading new playlist: {new_path}")
    new_channels = parse_m3u(new_path)
    print(f"  Found {len(new_channels)} channels")

    existing_by_tvg_id = {}
    existing_by_name = {}
    for ch in existing:
        if ch['tvg_id']:
            existing_by_tvg_id[ch['tvg_id']] = ch
            if ch['tvg_id_base']:
                existing_by_tvg_id[ch['tvg_id_base']] = ch
        if ch['name']:
            existing_by_name[normalize_name(ch['name'])] = ch

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
    modified_channels = []  # Track modifications

    for ch in existing:
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
            ch['extra'] = matched[0].get('extra', [])
            updated += 1
            modified_channels.append({
                'name': ch['name'],
                'old_url': old_url[:80],
                'new_url': ch['url'][:80],
            })

    print(f"  Updated {updated} existing channels with new URLs")

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
        if norm_name and norm_name in existing_by_name:
            continue
        group = guess_group(ch['name']) if ch['name'] else 'Other'
        tvg_name = ch['name']
        extinf = f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-name="{tvg_name}" tvg-logo="" tvg-country="IN" tvg-language="" group-title="{group}",{tvg_name}'
        added_channels.append({'extinf': extinf, 'extra': ch.get('extra', []), 'url': ch['url'], 'name': tvg_name})

    print(f"  Adding {len(added_channels)} new channels from iptv-org")

    # Write merged output
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
    print(f"\n✅ Merged: {total} channels ({len(existing)} existing + {len(added_channels)} new)")

    # Write changelog
    changelog_lines = []
    changelog_lines.append(f"## 📺 Playlist Update Summary\n")
    changelog_lines.append(f"- **Total channels:** {total}")
    changelog_lines.append(f"- **URLs updated:** {updated}")
    changelog_lines.append(f"- **New channels added:** {len(added_channels)}\n")

    if added_channels:
        changelog_lines.append("### 🆕 Newly Added Channels\n")
        for ch in added_channels:
            changelog_lines.append(f"- {ch['name']}")
        changelog_lines.append("")

    if modified_channels:
        changelog_lines.append(f"### 🔄 Modified Stream URLs ({len(modified_channels)} channels)\n")
        # Show first 30 modified channels to keep commit message readable
        for ch in modified_channels[:30]:
            changelog_lines.append(f"- **{ch['name']}**")
        if len(modified_channels) > 30:
            changelog_lines.append(f"- _...and {len(modified_channels) - 30} more_")
        changelog_lines.append("")

    changelog_text = '\n'.join(changelog_lines)

    # Write to file if path provided
    if changelog_path:
        with open(changelog_path, 'w', encoding='utf-8') as f:
            f.write(changelog_text)
        print(f"📋 Changelog written to: {changelog_path}")

    # Also print to stdout for GitHub Actions
    print("\n" + changelog_text)

    # Write summary to GITHUB_STEP_SUMMARY if available
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_file:
        with open(summary_file, 'a', encoding='utf-8') as f:
            f.write(changelog_text)
        print("📋 Written to GITHUB_STEP_SUMMARY")

    # Export counts as env vars for the workflow
    env_file = os.environ.get('GITHUB_ENV')
    if env_file:
        with open(env_file, 'a', encoding='utf-8') as f:
            f.write(f"TOTAL_CHANNELS={total}\n")
            f.write(f"UPDATED_URLS={updated}\n")
            f.write(f"NEW_CHANNELS={len(added_channels)}\n")
            added_names = ', '.join(ch['name'] for ch in added_channels[:10])
            if len(added_channels) > 10:
                added_names += f' (+{len(added_channels) - 10} more)'
            f.write(f"NEW_CHANNEL_NAMES={added_names}\n")
            modified_names = ', '.join(ch['name'] for ch in modified_channels[:10])
            if len(modified_channels) > 10:
                modified_names += f' (+{len(modified_channels) - 10} more)'
            f.write(f"MODIFIED_CHANNEL_NAMES={modified_names}\n")

if __name__ == '__main__':
    if len(sys.argv) >= 4:
        changelog = sys.argv[4] if len(sys.argv) > 4 else None
        merge_playlists(sys.argv[1], sys.argv[2], sys.argv[3], changelog)
    else:
        print("Usage: python3 merge_playlists.py <existing.m3u> <new.m3u> <output.m3u> [changelog.md]")
        sys.exit(1)
