#!/usr/bin/env python3
import json
import os
import re

STREAM_REPORT = "stream_report.json"
LOOP_REPORT = "loop_report.json"
INPUT_M3U = "latest.m3u"
OUTPUT_M3U = "latest.m3u"
LATENCY_THRESHOLD = 5.0

def load_good_urls():
    good_urls = set()
    
    # Check Stream Health
    if os.path.exists(STREAM_REPORT):
        with open(STREAM_REPORT, 'r') as f:
            s_results = json.load(f)
        good_urls = {r['url'] for r in s_results if r['status'] == 'OK' and r.get('latency', 0) <= LATENCY_THRESHOLD}
    
    # Intersect with Loop Report (if exists)
    if os.path.exists(LOOP_REPORT):
        with open(LOOP_REPORT, 'r') as f:
            l_results = json.load(f)
        bad_loops = {r['url'] for r in l_results if r['status'] != 'OK'}
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
            
            # Special case: Always keep manual Sony variants even if they weren't in the report
            # Or if they are in the report and OK
            is_manual = '(Jio Proxy)' in extinf or '(Google DAI)' in extinf or '(Stable Restream)' in extinf
            
            if url in good_urls or is_manual:
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
