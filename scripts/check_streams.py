#!/usr/bin/env python3
import subprocess
import json
import concurrent.futures
import time
import re
import os
import sys

# Configuration
INPUT_M3U = "/var/www/html/akshay/iptv/shahakshay938.github.io/latest.m3u"
OUTPUT_REPORT = "stream_report.json"
MAX_WORKERS = 10 # Adjust based on CPU/Network
TIMEOUT = 10  # Seconds to wait for ffprobe

def parse_m3u(filepath):
    channels = []
    if not os.path.exists(filepath): return []
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            extinf = line
            url = ""
            i += 1
            while i < len(lines):
                if lines[i].strip() and not lines[i].strip().startswith('#'):
                    url = lines[i].strip()
                    i += 1
                    break
                i += 1
            
            ua_match = re.search(r'user-agent="([^"]*)"', extinf)
            ua = ua_match.group(1) if ua_match else None
            
            name_match = re.search(r',(.+)$', extinf)
            name = name_match.group(1).strip() if name_match else "Unknown"
            
            channels.append({'name': name, 'url': url, 'ua': ua, 'extinf': extinf})
        else:
            i += 1
    return channels

def verify_stream(channel):
    url = channel['url']
    ua = channel['ua']
    name = channel['name']
    
    cmd = [
        'ffprobe', 
        '-v', 'error', 
        '-show_entries', 'format=duration', 
        '-select_streams', 'v:0', 
        '-show_streams', 
        '-of', 'json',
        '-connect_timeout', '5',
        url
    ]
    
    # Add User-Agent if present
    if ua:
        cmd.insert(1, '-user_agent')
        cmd.insert(2, ua)
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        latency = time.time() - start_time
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if 'streams' in data and len(data['streams']) > 0:
                return {'name': name, 'status': 'OK', 'latency': round(latency, 2), 'url': url}
            else:
                return {'name': name, 'status': 'NO_VIDEO', 'latency': round(latency, 2), 'url': url}
        else:
            return {'name': name, 'status': 'ERROR', 'error': result.stderr.strip()[:100], 'url': url}
            
    except subprocess.TimeoutExpired:
        return {'name': name, 'status': 'TIMEOUT', 'url': url}
    except Exception as e:
        return {'name': name, 'status': 'CRASH', 'error': str(e), 'url': url}

def main():
    print(f"Reading playlist: {INPUT_M3U}")
    channels = parse_m3u(INPUT_M3U)
    print(f"Found {len(channels)} channels. Starting verification with {MAX_WORKERS} workers...")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_ch = {executor.submit(verify_stream, ch): ch for ch in channels}
        
        count = 0
        for future in concurrent.futures.as_completed(future_to_ch):
            res = future.result()
            results.append(res)
            count += 1
            if count % 10 == 0:
                print(f" Progress: {count}/{len(channels)} checked...")

    # Save report
    with open(OUTPUT_REPORT, 'w') as f:
        json.dump(results, f, indent=4)
        
    ok_count = len([r for r in results if r['status'] == 'OK'])
    print(f"\nVerification Complete!")
    print(f"Total: {len(results)}")
    print(f"OK: {ok_count}")
    print(f"Failed/Suspect: {len(results) - ok_count}")
    print(f"Report saved to {OUTPUT_REPORT}")

if __name__ == "__main__":
    main()
