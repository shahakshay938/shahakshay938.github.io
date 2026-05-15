import re
import os

INPUT_M3U = "latest.m3u"
OUTPUT_M3U = "latest.m3u"

def parse_m3u_advanced(filepath):
    channels = []
    if not os.path.exists(filepath): return []
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    parts = content.split('#EXTINF:')
    for part in parts[1:]:
        lines = part.strip().split('\n')
        extinf = '#EXTINF:' + lines[0]
        
        extra_lines = []
        url = ""
        for line in lines[1:]:
            line = line.strip()
            if not line: continue
            if line.startswith('#'):
                extra_lines.append(line)
            else:
                url = line
                break
        
        name_match = re.search(r',(.+)$', extinf)
        name = name_match.group(1).strip() if name_match else "Unknown"
        
        tvg_id_match = re.search(r'tvg-id="([^"]*)"', extinf)
        tvg_id = tvg_id_match.group(1) if tvg_id_match else ""
        
        channels.append({
            'name': name,
            'url': url,
            'extinf': extinf,
            'extra': extra_lines,
            'tvg_id': tvg_id
        })
    return channels

def clean_metadata(ch):
    extinf = ch['extinf']
    name = ch['name']
    
    # Premium Logo Mappings
    PREMIUM_LOGOS = {
        "Sony Max": "https://i.imgur.com/vHqY8f3.png",
        "Sony Wah": "https://i.imgur.com/K6mU8X8.png",
        "Sony Max 2": "https://i.imgur.com/pZ6v7Zl.png",
        "Star Gold": "https://i.imgur.com/7Kk3m8m.png",
        "Star Gold 2": "https://i.imgur.com/G0ZfzZr.png",
        "Star Gold Thrills": "https://i.imgur.com/azqtpYh.png",
        "Star Gold Romance": "https://i.imgur.com/gSWv9U3.png",
        "Star Gold Select": "https://i.imgur.com/6UqU6U6.png",
        "Sony SAB": "https://i.imgur.com/w2Y2f2t.png",
        "Star Sports 1": "https://i.imgur.com/E5jjKHI.png",
        "Star Sports 1 Hindi": "https://i.imgur.com/vH9AasC.png",
        "Colors": "https://i.imgur.com/QvY0YVv.png",
        "Colors Cineplex": "https://i.imgur.com/QvY0YVv.png"
    }
    
    # 1. Apply Premium Logos
    for key, logo in PREMIUM_LOGOS.items():
        if key.lower() in name.lower():
            if 'tvg-logo="' in extinf:
                # Replace existing logo if it's not a premium one already
                if "i.imgur.com" not in extinf:
                    extinf = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{logo}"', extinf)
            else:
                extinf = extinf.replace(',', f' tvg-logo="{logo}",', 1)

    # 2. Define Group Rules
    MOVIES = ["Gold", "Max", "Pictures", "Movies", "Cinema", "Filmy", "Action", "Wah", "Pix", "Cineplex"]
    SPORTS = ["Sports", "Cricket", "Football", "Ten", "Six"]
    KIDS = ["Nick", "Disney", "Pogo", "Cartoon", "Hungama", "Sonic", "Yay"]
    NEWS = ["News", "Aaj Tak", "ABP", "India TV", "NDTV", "Republic", "Zee 24"]
    ENTERTAINMENT = ["Sony SAB", "Colors", "StarPlus", "Zee TV", "Star Vijay", "&TV", "Zee Cafe"]
    
    new_group = None
    if any(k.lower() in name.lower() for k in MOVIES):
        new_group = "Movies"
    elif any(k.lower() in name.lower() for k in SPORTS):
        new_group = "Sports"
    elif any(k.lower() in name.lower() for k in KIDS):
        new_group = "Kids"
    elif any(k.lower() in name.lower() for k in NEWS):
        new_group = "News"
    elif any(k.lower() in name.lower() for k in ENTERTAINMENT):
        new_group = "Entertainment"
    
    if new_group:
        if 'group-title="' in extinf:
            extinf = re.sub(r'group-title="[^"]*"', f'group-title="{new_group}"', extinf)
        else:
            extinf = extinf.replace(',', f' group-title="{new_group}",', 1)
            
    ch['extinf'] = extinf
    return ch

def main():
    channels = parse_m3u_advanced(INPUT_M3U)
    print(f"Loaded {len(channels)} channels.")
    
    # Deduplicate by (Name + URL)
    final_dict = {}
    for ch in channels:
        key = f"{ch['name']}|{ch['url']}"
        if key not in final_dict:
            final_dict[key] = clean_metadata(ch)
        else:
            # Prefer entries with jiotv-id (meaning they are from the stable base)
            if 'jiotv-id=' in ch['extinf'] and 'jiotv-id=' not in final_dict[key]['extinf']:
                final_dict[key] = clean_metadata(ch)
                
    final_list = list(final_dict.values())
    print(f"Deduplicated to {len(final_list)} channels.")
    
    with open(OUTPUT_M3U, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for ch in final_list:
            f.write(ch['extinf'] + '\n')
            for extra in ch['extra']:
                f.write(extra + '\n')
            f.write(ch['url'] + '\n')
            
    print(f"Cleaned playlist saved to {OUTPUT_M3U}")

if __name__ == "__main__":
    main()
