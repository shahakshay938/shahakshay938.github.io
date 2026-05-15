#!/usr/bin/env python3
import threading
import requests
import json
import concurrent.futures
import subprocess
import os

# Known Astra Proxy IPs (We can expand this list over time)
IPS = [
    "103.122.249.134:8000", 
    "103.253.18.58:8000", 
    "103.157.248.140:8000",
    "103.111.19.141:8000",
    "103.229.254.25:7001"
]

# Common ID Prefixes
ID_RANGES = ["a00", "a01", "a04", "a05", "a06", "a07", "a0h"]
SUFFIXES = "abcdefghijklmnopqrstuvwxyz0123456789"

def get_channel_name(url):
    try:
        # Quick check for service_name in tags
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format_tags=service_name", "-of", "default=noprint_wrappers=1:nokey=1", "-connect_timeout", "1", url]
        name = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=2).decode().strip()
        if name:
            return name
    except:
        pass
    return None

def check_url(url):
    try:
        # First do a HEAD request to check if 200 OK
        r = requests.head(url, timeout=1)
        if r.status_code == 200:
            name = get_channel_name(url)
            return {"url": url, "name": name or "Astra Stream"}
    except:
        pass
    return None

def main():
    urls = []
    for ip in IPS:
        for r in ID_RANGES:
            for s in SUFFIXES:
                urls.append(f"http://{ip}/play/{r}{s}")
    
    print(f"🚀 Starting Deep Discovery for {len(urls)} potential streams...")
    results = []
    # Using more workers for faster scan in GH Actions
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_url = {executor.submit(check_url, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            res = future.result()
            if res:
                print(f"  ✨ Found: {res['name']} @ {res['url']}")
                results.append(res)
    
    # Save as a temporary M3U for the repair script
    with open("/tmp/discovery_source.m3u", "w") as f:
        f.write("#EXTM3U\n")
        for res in results:
            f.write(f"#EXTINF:-1,{res['name']}\n")
            f.write(f"{res['url']}\n")
            
    print(f"✅ Discovery complete. Found {len(results)} active Astra streams.")

if __name__ == "__main__":
    main()
