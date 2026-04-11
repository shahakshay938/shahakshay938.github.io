import sys

def inject():
    with open("latest.m3u", "r") as f:
        lines = f.readlines()
        
    new_channels = {
        "Sony Max HD (1080p)": ("Sony Max HD (Stable)", "http://103.99.249.139/sonymax/index.m3u8"),
        "Star Gold HD (1080p)": ("Star Gold HD (Stable)", "http://103.99.249.139/stargold/index.m3u8"),
        "Zee Cinema HD (576p)": ("Zee Cinema (Stable)", "http://103.99.249.139/zeecinema/index.m3u8"),
        "Sony Yay! (576p)": ("Sony Yay! (Stable)", "http://103.99.249.139/sonyyay/index.m3u8"),
    }
    
    out_lines = []
    inject_queue = []
    
    for line in lines:
        out_lines.append(line)
        
        if line.startswith("#EXTINF"):
            for trigger, (new_name, new_url) in new_channels.items():
                if f'tvg-name="{trigger}"' in line or (trigger in line and 'tvg-name="' not in line):
                    new_extinf = line.replace(trigger, new_name)
                    vlc_opts = [
                        "#EXTVLCOPT:network-caching=5000\n",
                        "#EXTVLCOPT:http-reconnect=true\n",
                        "#EXTVLCOPT:http-continuous=1\n"
                    ]
                    inject_queue = [new_extinf] + vlc_opts + [new_url + "\n"]
        elif line.startswith("http") and inject_queue:
            out_lines.extend(inject_queue)
            inject_queue = [] # clear queue
            
    with open("latest.m3u", "w") as f:
        f.writelines(out_lines)

if __name__ == '__main__':
    inject()
