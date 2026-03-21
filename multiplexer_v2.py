import sys
import json
import urllib.request

def fetch_iptv_streams():
    url = "https://iptv-org.github.io/api/streams.json"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Failed to fetch streams.json: {e}")
        return []

def multiplex_playlist():
    print("Fetching raw streams.json developer database...")
    global_streams = fetch_iptv_streams()
    if not global_streams:
        return
        
    print(f"Found {len(global_streams)} raw streams in global database.")
    
    global_map = {}
    for stream in global_streams:
        tvg_id = stream.get("channel")
        if not tvg_id:
            continue
        if tvg_id not in global_map:
            global_map[tvg_id] = []
        global_map[tvg_id].append(stream.get("url"))
        
    print("Reading local latest.m3u...")
    with open("latest.m3u", "r") as f:
        local_lines = f.readlines()
        
    out_lines = []
    i = 0
    injected_count = 0
    
    while i < len(local_lines):
        line = local_lines[i]
        
        # If this is already a (Src X) line from a previous run, skip it safely
        # Wait, if we run it again, we don't want to duplicate the previous Src 2.
        # It's better to just process the primary ones and inject.
        if "(Src " in line:
            # Skip this block entirely (extinf, opts, and url)
            j = i + 1
            while j < len(local_lines):
                if local_lines[j].startswith("http"):
                    i = j + 1
                    break
                j += 1
            if j >= len(local_lines): i = j
            continue
            
        out_lines.append(line)
        
        if line.startswith("#EXTINF"):
            tvg_id = ""
            if 'tvg-id="' in line:
                tvg_id = line.split('tvg-id="')[1].split('"')[0]
                
            lookup_id = tvg_id
            if "@" in lookup_id:
                lookup_id = lookup_id.split("@")[0]
                
            local_url = ""
            j = i + 1
            while j < len(local_lines):
                next_line = local_lines[j]
                out_lines.append(next_line)
                if next_line.startswith("http"):
                    local_url = next_line.strip()
                    i = j
                    break
                elif next_line.startswith("#EXTVLCOPT"):
                    j += 1
                else:
                    break
                    
            if not lookup_id or not local_url:
                i += 1
                continue
                
            if lookup_id in global_map:
                available_urls = global_map[lookup_id]
                unique_urls = []
                for u in available_urls:
                    if u != local_url and u not in unique_urls:
                        unique_urls.append(u)
                        
                src_index = 2
                for u in unique_urls:
                    new_extinf = line
                    
                    if ',' in new_extinf:
                        parts = new_extinf.split(',')
                        base = ','.join(parts[:-1])
                        name = parts[-1].strip()
                        new_extinf = f"{base},{name} (Src {src_index})\n"
                    
                    if 'tvg-name="' in new_extinf:
                        old_name = new_extinf.split('tvg-name="')[1].split('"')[0]
                        new_extinf = new_extinf.replace(f'tvg-name="{old_name}"', f'tvg-name="{old_name} (Src {src_index})"')
                        
                    vlc_opts = [
                        "#EXTVLCOPT:network-caching=5000\n",
                        "#EXTVLCOPT:http-reconnect=true\n",
                        "#EXTVLCOPT:http-continuous=1\n"
                    ]
                    
                    out_lines.append(new_extinf)
                    out_lines.extend(vlc_opts)
                    out_lines.append(u + "\n")
                    src_index += 1
                    injected_count += 1
                    
        i += 1
        
    print(f"Successfully injected {injected_count} raw deduplicated streams!")
    with open("multiplexed_latest.m3u", "w") as f:
        f.writelines(out_lines)

if __name__ == "__main__":
    multiplex_playlist()
