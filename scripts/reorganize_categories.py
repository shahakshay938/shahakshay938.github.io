import os
import re

# Priority list: Higher index = higher priority to keep if multiple exist
PRIORITY = [
    "Other",
    "General",
    "Classic",
    "Culture",
    "Education",
    "Travel",
    "Lifestyle",
    "Cooking",
    "Documentary",
    "Music",
    "Religious",
    "Devotional",
    "Animation",
    "Kids",
    "Sports",
    "Movies",
    "Entertainment",
    "News"
]

def clean_group(group_str):
    if not group_str or group_str.lower() == "undefined":
        return "Entertainment" # Fallback

    # Split by common delimiters
    parts = re.split(r'[;,\/]| and | with | & ', group_str, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        return "Entertainment"

    # Find the one with highest priority
    best_part = parts[0]
    max_priority = -1
    
    for p in parts:
        found = False
        p_clean = p.capitalize()
        if "Movie" in p_clean: p_clean = "Movies"
        if "Document" in p_clean: p_clean = "Documentary"
        if "Relig" in p_clean or "Devot" in p_clean: p_clean = "Religious"
        if "Cooking" in p_clean: p_clean = "Cooking"
        if "Culture" in p_clean: p_clean = "Culture"

        for i, prio in enumerate(PRIORITY):
            if prio.lower() in p_clean.lower():
                if i > max_priority:
                    max_priority = i
                    best_part = prio
                    found = True
        if not found:
            # If not in priority, but has priority -1, keep it if it's the first unknown
            if max_priority == -1:
                best_part = p_clean

    return best_part

def reorganize_m3u(file_path):
    print(f"Reorganizing categories in {file_path}...")
    if not os.path.exists(file_path): return

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.startswith("#EXTINF"):
            # Extract group-title
            match = re.search(r'group-title="([^"]*)"', line)
            if match:
                old_group = match.group(1)
                new_group = clean_group(old_group)
                # Ensure we handle special cases mentioned by user
                if "Education" in old_group and "Outdoor" in old_group:
                    new_group = "Education"
                
                line = line.replace(f'group-title="{old_group}"', f'group-title="{new_group}"')
            new_lines.append(line)
        else:
            new_lines.append(line)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Optimization complete.")

if __name__ == "__main__":
    reorganize_m3u("latest.m3u")
