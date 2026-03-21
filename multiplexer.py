import sys
import urllib.request

def fetch_iptv_org():
    url = "https://iptv-org.github.io/iptv/index.m3u"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8').splitlines()
    except Exception as e:
        print(f"Failed to fetch iptv-org index.m3u: {e}")
        return []

def parse_m3u(lines):
    channels = []
    current_extinf = None
    tvg_id = ""
    tvg_name = ""
    
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith("#EXTINF"):
            current_extinf = line
            if 'tvg-id="' in line:
                tvg_id = line.split('tvg-id="')[1].split('"')[0]
                if "@" in tvg_id:
                    tvg_id = tvg_id.split("@")[0]
            if 'tvg-name="' in line:
                tvg_name = line.split('tvg-name="')[1].split('"')[0]
            elif ',' in line:
                tvg_name = line.split(',')[-1].strip()
        elif line.startswith("http"):
            if current_extinf:
                channels.append({
                    "tvg_id": tvg_id,
                    "tvg_name": tvg_name,
                    "url": line,
                    "extinf": current_extinf
                })
            current_extinf = None
            tvg_id = ""
            tvg_name = ""
    return channels

def multiplex_playlist():
    print("Fetching massive global database from iptv-org...")
    global_lines = fetch_iptv_org()
    if not global_lines:
        return
    
    global_channels = parse_m3u(global_lines)
    print(f"Found {len(global_channels)} total streams in global database.")
    
    global_map = {}
    for c in global_channels:
        if not c["tvg_id"]: continue
        if c["tvg_id"] not in global_map:
            global_map[c["tvg_id"]] = []
        global_map[c["tvg_id"]].append(c["url"])
        
    print("Reading local latest.m3u...")
    with open("latest.m3u", "r") as f:
        local_lines = f.readlines()
        
    out_lines = []
    i = 0
    injected_count = 0
    
    while i < len(local_lines):
        line = local_lines[i]
        out_lines.append(line)
        
        if line.startswith("#EXTINF"):
            tvg_id = ""
            if 'tvg-id="' in line:
                tvg_id = line.split('tvg-id="')[1].split('"')[0]
                
            lookup_id = tvg_id
            if "@" in lookup_id:
                lookup_id = lookup_id.split("@")[0]
                
            block_lines = []
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
                        "#EXTVLCOPT:network-caching=3000\n",
                        "#EXTVLCOPT:http-reconnect=true\n",
                        "#EXTVLCOPT:http-continuous=1\n"
                    ]
                    
                    out_lines.append(new_extinf)
                    out_lines.extend(vlc_opts)
                    out_lines.append(u + "\n")
                    src_index += 1
                    injected_count += 1
                    
        i += 1
        
    print(f"Successfully injected {injected_count} deduplicated alternative streams!")
    with open("multiplexed_latest.m3u", "w") as f:
        f.writelines(out_lines)

if __name__ == "__main__":
    multiplex_playlist()
