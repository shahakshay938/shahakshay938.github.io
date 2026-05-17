#!/usr/bin/env python3
import re
import os
import json
import argparse

# Default Paths
BASE_M3U = "sources/base.m3u"
NEW_SOURCE = "/tmp/source_iptv_org.m3u"
OUTPUT_M3U = "sources/base.m3u"

def parse_m3u(filepath):
    channels = []
    if not os.path.exists(filepath): return []
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    parts = content.split('#EXTINF:')
    for part in parts[1:]:
        lines = part.strip().split('\n')
        extinf = '#EXTINF:' + lines[0]
        url = ""
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith('#'): continue
            url = line
            break
        
        name_match = re.search(r',(.+)$', extinf)
        name = name_match.group(1).strip() if name_match else "Unknown"
        
        tvg_id_match = re.search(r'tvg-id="([^"]*)"', extinf)
        tvg_id = tvg_id_match.group(1) if tvg_id_match else ""
        
        channels.append({'name': name, 'url': url, 'extinf': extinf, 'tvg_id': tvg_id})
    return channels

def normalize_name(name):
    # Remove HD, 1080p, 720p, etc. for better fuzzy matching
    n = name.lower()
    n = re.sub(r'\(.*?\)', '', n)
    n = n.replace('hd', '').replace('sd', '').replace('fhd', '')
    n = re.sub(r'[^a-z0-9]', '', n)
    return n.strip()

def extract_stream_id(url):
    match = re.search(r'/play/([^/]+)', url)
    if match:
        val = match.group(1)
        if '.' in val:
            val = val.split('.')[0]
        return val
    return None

def main():
    parser = argparse.ArgumentParser(description="Repair dead Astra links in base playlist using a fresh source.")
    parser.add_argument('--base', default=BASE_M3U, help="Path to the permanent base M3U")
    parser.add_argument('--source', default=NEW_SOURCE, help="Path to the fresh source M3U (reference)")
    parser.add_argument('--output', default=OUTPUT_M3U, help="Where to save the repaired base")
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"⚠️ Source file {args.source} not found. Skipping repair.")
        return

    print(f"Loading Base: {args.base}")
    base_channels = parse_m3u(args.base)
    print(f"Loading Fresh Source: {args.source}")
    new_channels = parse_m3u(args.source)
    
    # Map by normalized name and tvg-id
    new_map = {}
    id_map = {}
    for ch in new_channels:
        norm_name = normalize_name(ch['name'])
        # Store the URL
        if norm_name not in new_map:
            new_map[norm_name] = ch['url']
        
        # Also map by tvg-id base (before @)
        if ch['tvg_id']:
            tvg_base = ch['tvg_id'].split('@')[0].lower()
            new_map[tvg_base] = ch['url']
            
        # Map by stream ID
        sid = extract_stream_id(ch['url'])
        if sid:
            id_map[sid] = ch['url']
            
    # Load failed URLs from stream_report.json if it exists
    failed_urls = set()
    report_path = "stream_report.json"
    if os.path.exists(report_path):
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
                for item in report_data:
                    if item.get('status') != 'OK':
                        failed_urls.add(item.get('url'))
            print(f"Loaded {len(failed_urls)} failed stream URLs from {report_path}")
        except Exception as e:
            print(f"⚠️ Could not load stream report: {e}")

    repaired_count = 0
    for ch in base_channels:
        # We want to repair a base channel if:
        # 1. It is an Astra link (to keep it synced to the best/latest working server)
        # 2. It has a backup fallback URL (which are often dead or old snapshots)
        # 3. It was marked as failing, timed out, or had an error in our stream report
        is_astra = any(p in ch['url'] for p in ['103.', '116.', '149.71.', 'workers.dev', '/play/'])
        is_backup = 'backups/' in ch['url'] or 'shahakshay938.github.io' in ch['url']
        is_failed = ch['url'] in failed_urls
        
        if is_astra or is_backup or is_failed:
            norm_name = normalize_name(ch['name'])
            tvg_base = ch['tvg_id'].split('@')[0].lower() if ch['tvg_id'] else None
            
            replacement_url = None
            # Priority 1: tvg-id match
            if tvg_base and tvg_base in new_map:
                replacement_url = new_map[tvg_base]
            # Priority 2: Name match
            elif norm_name in new_map:
                replacement_url = new_map[norm_name]
                
            # Priority 3: Stream ID match (for matching Astra proxy shifts)
            if not replacement_url:
                old_sid = extract_stream_id(ch['url'])
                if old_sid and old_sid in id_map:
                    replacement_url = id_map[old_sid]
                
            if replacement_url and ch['url'] != replacement_url:
                # Validation: If we are replacing an active Astra stream, we should only replace it with another Astra/Worker stream
                is_repl_valid = True
                if is_astra and not any(p in replacement_url for p in ['103.', '116.', '149.71.', 'workers.dev', '/play/']):
                    is_repl_valid = False
                    
                if is_repl_valid:
                    print(f"🔧 Repairing {ch['name']}:")
                    print(f"   Old: {ch['url']}")
                    print(f"   New: {replacement_url}")
                    ch['url'] = replacement_url
                    repaired_count += 1
                
    print(f"✅ Self-healing complete. Repaired {repaired_count} channels in base.")
    
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for ch in base_channels:
            f.write(ch['extinf'] + '\n')
            f.write(ch['url'] + '\n')
            
if __name__ == "__main__":
    main()
