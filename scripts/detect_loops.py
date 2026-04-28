#!/usr/bin/env python3
import urllib.request
import time
import re
import concurrent.futures
import json
import os

try:
    from wrapper_utils import resolve_stream_target
except ModuleNotFoundError:
    from scripts.wrapper_utils import resolve_stream_target

# Configuration
INPUT_M3U = "latest.m3u"
WAIT_TIME = 15  # Seconds between checks
MAX_WORKERS = 50 # Increased for faster GitHub Actions execution

def get_hls_metadata(url, ua=None):
    try:
        req = urllib.request.Request(url)
        if ua:
            req.add_header('User-Agent', ua)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8', errors='ignore')
            
            # Find Media Sequence
            seq_match = re.search(r'#EXT-X-MEDIA-SEQUENCE:(\d+)', content)
            seq = int(seq_match.group(1)) if seq_match else None
            
            # Find the last segment URL
            segments = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith('#')]
            last_segment = segments[-1] if segments else None
            
            return {'seq': seq, 'last_segment': last_segment, 'is_live': '#EXT-X-ENDLIST' not in content}
    except Exception as e:
        return {'error': str(e)}

def check_loop(channel):
    url = channel['url']
    resolved_url = resolve_stream_target(url)
    ua = channel['ua']
    name = channel['name']
    
    # Check 1
    m1 = get_hls_metadata(resolved_url, ua)
    if 'error' in m1 or not m1['is_live']:
        return {'name': name, 'url': url, 'resolved_url': resolved_url, 'status': 'STALE_OR_ERROR'}
    
    time.sleep(WAIT_TIME)
    
    # Check 2
    m2 = get_hls_metadata(resolved_url, ua)
    if 'error' in m2:
        return {'name': name, 'url': url, 'resolved_url': resolved_url, 'status': 'ERROR_ON_SECOND_CHECK'}

    # Logic: If sequence is the same AND it's a live stream, it's a loop or stuck
    s1 = m1.get('seq')
    s2 = m2.get('seq')
    if s1 is not None and s2 is not None:
        if s1 == s2 and m1['last_segment'] == m2['last_segment']:
            return {'name': name, 'url': url, 'resolved_url': resolved_url, 'status': 'LOOPING', 'seq': s1}
        diff = s2 - s1
    else:
        diff = 0
    
    return {'name': name, 'url': url, 'resolved_url': resolved_url, 'status': 'OK', 'seq_diff': diff}

def main():
    print(f"Reading playlist: {INPUT_M3U}")
    # Reuse parse logic or just grep URLs
    with open(INPUT_M3U, 'r') as f:
        lines = f.readlines()
    
    channels = []
    # Only check High-Priority channels to save time (or all if we have time)
    # For now, let's check ALL 442 channels in the filtered list
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            extinf = line
            i += 1
            while i < len(lines):
                if lines[i].strip() and not lines[i].strip().startswith('#'):
                    url = lines[i].strip()
                    break
                i += 1
            ua_match = re.search(r'user-agent="([^"]*)"', extinf)
            name_match = re.search(r',(.+)$', extinf)
            channels.append({
                'name': name_match.group(1).strip() if name_match else "Unknown",
                'url': url,
                'ua': ua_match.group(1) if ua_match else None
            })
        i += 1

    print(f"Verifying {len(channels)} channels for loops...")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_loop, ch): ch for ch in channels}
        count = 0
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            count += 1
            if count % 10 == 0: print(f"  Progress: {count}/{len(channels)} checked...")

    with open("loop_report.json", 'w') as f:
        json.dump(results, f, indent=4)
    
    loops = [r for r in results if r['status'] == 'LOOPING']
    print(f"\nLoop Detection Complete!")
    print(f"Total: {len(results)}, Loops Found: {len(loops)}")
    for l in loops:
        print(f"  🚨 LOOPING: {l['name']}")

if __name__ == "__main__":
    main()
