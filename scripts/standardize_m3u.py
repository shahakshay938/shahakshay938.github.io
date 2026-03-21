import os
import re

def standardize_m3u(file_path):
    print(f"Standardizing {file_path}...")
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    if lines and lines[0].startswith("#EXTM3U"):
        new_lines.append(lines[0])
        start_idx = 1
    else:
        start_idx = 0

    i = start_idx
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith("#EXTINF"):
            # 1. Standardize #EXTINF attributes
            # Check for timeshift and aspect-ratio
            if 'timeshift="' not in line:
                line = line.replace(',', ' timeshift="1",', 1) if ',' in line else line + ' timeshift="1"'
            if 'aspect-ratio="' not in line:
                line = line.replace(',', ' aspect-ratio="16:9",', 1) if ',' in line else line + ' aspect-ratio="16:9"'
            
            # Ensure attributes are before the comma
            # Regex to move attributes if they accidentally got placed after the comma
            # (Simple string replacement safer for now)
            
            new_lines.append(line + "\n")
            
            # 2. Add #EXTVLCOPT tags
            new_lines.append("#EXTVLCOPT:network-caching=3000\n")
            new_lines.append("#EXTVLCOPT:http-reconnect=true\n")
            new_lines.append("#EXTVLCOPT:http-continuous=1\n")
            
            # Skip any existing EXTVLCOPT lines (clean state)
            i += 1
            while i < len(lines) and lines[i].startswith("#EXTVLCOPT"):
                i += 1
            
            # 3. Add the URL
            if i < len(lines):
                new_lines.append(lines[i])
        elif line.startswith("#EXTVLCOPT"):
            # skip orphan opts
            pass
        elif line == "" or line.startswith("#EXTM3U"):
            pass
        else:
            # Just in case there are other lines
            new_lines.append(lines[i])
            
        i += 1

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Successfully standardized {len(new_lines)} lines.")

if __name__ == "__main__":
    standardize_m3u("/var/www/html/akshay/iptv/shahakshay938.github.io/latest.m3u")
