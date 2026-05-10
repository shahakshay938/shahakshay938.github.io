#!/usr/bin/env python3
import json
import os
import re

try:
    from wrapper_utils import resolve_stream_target
except ModuleNotFoundError:
    from scripts.wrapper_utils import resolve_stream_target

STREAM_REPORT = "stream_report.json"
LOOP_REPORT = "loop_report.json"
INPUT_M3U = "latest.m3u"
OUTPUT_M3U = "latest.m3u"
LATENCY_THRESHOLD = 10.0 # Relaxed from 5.0s to 10.0s to recover more stable streams

def load_good_urls():
    good_urls = set()
    
    # Check Stream Health
    if os.path.exists(STREAM_REPORT):
        with open(STREAM_REPORT, 'r') as f:
            s_results = json.load(f)
        for result in s_results:
            if result['status'] == 'OK' and result.get('latency', 0) <= LATENCY_THRESHOLD:
                good_urls.add(result['url'])
                if result.get('resolved_url'):
                    good_urls.add(result['resolved_url'])
    
    # Intersect with Loop Report (if exists)
    if os.path.exists(LOOP_REPORT):
        with open(LOOP_REPORT, 'r') as f:
            l_results = json.load(f)
        bad_loops = set()
        for result in l_results:
            if result['status'] != 'OK':
                bad_loops.add(result['url'])
                if result.get('resolved_url'):
                    bad_loops.add(result['resolved_url'])
        good_urls = good_urls - bad_loops
        
    return good_urls

def filter_m3u(input_path, output_path, good_urls):
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    filtered_lines = ['#EXTM3U\n']
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            extinf = line
            extra = []
            url = ""
            i += 1
            while i < len(lines):
                if lines[i].strip() and not lines[i].strip().startswith('#'):
                    url = lines[i].strip()
                    i += 1
                    break
                else:
                    extra.append(lines[i])
                    i += 1
            
            # Protection Logic
            # 1. Manual markers (Jio Proxy, etc.)
            is_manual = any(marker in extinf for marker in ['(Jio Proxy)', '(Google DAI)', '(Stable Restream)'])
            
            # 2. Protected Channel IDs (Essential channels)
            PROTECTED_IDS = [
                "StarGold.in", "StarGold2.in", "StarGoldSelect.in", "StarGoldThrills.in", "StarGoldRomance.in",
                "SonyMax.in", "SonyMax2.in", "SonyWah.in", "SonyPal.in", "SonyPix.in", "SonyMAXHD.in",
                "Colors.in", "SonySAB.in", "ZeeTV.in", "StarPlus.in", "SonyTen1.in", "StarSports1.in"
            ]
            is_protected_id = any(pid in extinf for pid in PROTECTED_IDS)
            
            # 3. Permanent Base Protection (If it has a jiotv-id or was in the original stable list)
            # We assume anything with significant metadata in the base is worth keeping.
            is_stable_base = 'jiotv-id=' in extinf or 'timeshift=' in extinf
            
            resolved_url = resolve_stream_target(url)
            
            # Keep if:
            # - URL is verified OK
            # - OR it's a manual stream
            # - OR it's a protected channel ID
            # - OR it's a stable base channel (Always keep the old list!)
            if url in good_urls or resolved_url in good_urls or is_manual or is_protected_id or is_stable_base:
                filtered_lines.append(extinf + '\n')
                filtered_lines.extend(extra)
                filtered_lines.append(url + '\n')
        else:
            i += 1
            
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(filtered_lines)
    
    print(f"Filtered playlist saved to {output_path}")
    print(f"Original lines: {len(lines)}, Filtered lines: {len(filtered_lines)}")

if __name__ == "__main__":
    goods = load_good_urls()
    print(f"Found {len(goods)} good URLs (Latency <= {LATENCY_THRESHOLD}s)")
    filter_m3u(INPUT_M3U, OUTPUT_M3U, goods)
