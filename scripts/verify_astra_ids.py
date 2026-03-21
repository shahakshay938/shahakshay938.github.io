import subprocess
import json
import concurrent.futures
import sys

SERVERS = [
    "http://103.229.254.25:7001/play/",
    "http://116.90.120.151:8000/play/",
    "http://66.102.120.18:8000/play/"
]

IDS = [
    "a02t", "a032", "a033", "a034", "a06r", "a070", "a077", "a07a", "a09p", 
    "a09q", "a09r", "a09s", "a09v", "a09w", "a0a1", "a0cs", "a0cx", "a0d0", 
    "a0d1", "a0db", "a0dc", "a0dk", "a0dl", "a0dp", "a0ds", "a0dt", "a0du", 
    "a0ed", "a0gp", "a0gs", "a0gw", "a0gz", "a0h0", "a0h1", "a0h2", "a0h4", 
    "a0h5", "a0ha", "a0hb", "a0hc", "a0he", "a0hf", "a0hi", "a0hj", "a0ho", 
    "a0hp", "a0i3", "a0i4", "a0ib", "a0ie", "a0ig", "a0ij", "a0il", "a0in", 
    "a0io", "a0is", "a0it", "a0j1", "a0j6", "a0jb", "a0jc", "a0jf", "a0jh", 
    "a0ji", "a0k2", "a0ka", "a0kc", "a0kf", "a0kl", "a0km", "a0kt", "a0ku"
]

def check_id(server, id_str):
    url = f"{server}{id_str}/index.m3u8"
    try:
        # Use GET instead of HEAD, longer timeout
        cmd_curl = ["curl", "-L", "--connect-timeout", "5", "--max-time", "10", "-s", "-o", "/dev/null", "-w", "%{http_code}", url]
        http_code = subprocess.check_output(cmd_curl).decode().strip()
        if http_code != "200":
            return None
        
        # Extract metadata
        cmd_ffp = [
            "ffprobe", "-v", "error", "-analyzeduration", "10000000", "-probesize", "10000000",
            "-show_entries", "format_tags=service_name:stream=width,height,bit_rate",
            "-of", "json", url
        ]
        output = subprocess.check_output(cmd_ffp, timeout=15, stderr=subprocess.STDOUT).decode()
        data = json.loads(output)
        
        width = data['streams'][0].get('width', 0)
        height = data['streams'][0].get('height', 0)
        res = f"{width}x{height}"
        name = data.get('format', {}).get('tags', {}).get('service_name', 'Unknown')
        bitrate = int(data.get('format', {}).get('bit_rate', 0)) // 1000
        
        return {"id": id_str, "server": server, "name": name, "res": res, "bitrate": f"{bitrate}kbps", "hd": (width >= 1280)}
    except Exception as e:
        return None

def main():
    results = []
    print(f"Aggressive Audit: Checking {len(IDS)} IDs across {len(SERVERS)} servers...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(check_id, s, i): (s, i) for s in SERVERS for i in IDS}
        for future in concurrent.futures.as_completed(future_to_url):
            res = future.result()
            if res:
                results.append(res)
                print(f"Found: {res['id']} @ {res['server']} -> {res['name']} ({res['res']} @ {res['bitrate']})")
    
    with open("astra_audit_report.json", "w") as f:
        json.dump(results, f, indent=4)
    
    print(f"\nAudit complete. {len(results)} active IDs found.")

if __name__ == "__main__":
    main()
