import subprocess
import json
import concurrent.futures

def get_channel_name(url):
    try:
        # Use a longer timeout and more probes
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format_tags=service_name", "-of", "default=noprint_wrappers=1:nokey=1", "-analyzeduration", "5000000", "-probesize", "5000000", url]
        name = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=10).decode().strip()
        if name:
            return name
    except:
        pass
    return None

def main():
    with open("mega_discovery_results.json", "r") as f:
        urls = json.load(f)
    
    print(f"Deep identifying {len(urls)} streams...")
    identified = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(get_channel_name, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            name = future.result()
            if name:
                print(f"IDENTIFIED: {name} @ {url}")
                identified.append({"url": url, "name": name})
    
    with open("identified_streams_deep.json", "w") as f:
        json.dump(identified, f, indent=2)
    print(f"Finished. Identified {len(identified)} streams.")

if __name__ == "__main__":
    main()
