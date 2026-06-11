"""
Qoder Stress Test - Bombardir request ke 9router Qoder endpoint
Pakai ini buat test apakah fallback + clean error patch bekerja.
Pantau console log 9router sambil jalanin script ini.
"""
import http.client
import json
import threading
import time
import sys

# Config
HOST = "localhost"
PORT = 20128
TOTAL_REQUESTS = 50
CONCURRENT = 5  # requests at a time
MODEL = "qd/qmodel_latest"

# Load API key
with open(r'C:\Users\andre\AppData\Roaming\9router\db.json') as f:
    db = json.load(f)
API_KEY = db['apiKeys'][0]['key']

# Stats
stats = {"success": 0, "error_clean": 0, "error_raw": 0, "other": 0}
lock = threading.Lock()
start_time = time.time()

def send_request(req_id):
    try:
        conn = http.client.HTTPConnection(HOST, PORT, timeout=60)
        body = json.dumps({
            "model": MODEL,
            "messages": [{"role": "user", "content": f"Test request #{req_id}. Say hi in 3 words."}],
            "max_tokens": 10,
            "stream": False
        })
        
        conn.request("POST", "/v1/chat/completions", body, {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "application/json"
        })
        
        resp = conn.getresponse()
        data = resp.read().decode()
        conn.close()
        
        elapsed = time.time() - start_time
        
        with lock:
            try:
                j = json.loads(data)
                if 'choices' in j:
                    stats["success"] += 1
                    content = j['choices'][0]['message']['content'][:40]
                    print(f"  [{elapsed:5.1f}s] #{req_id:3d} ✅ HTTP {resp.status} | {content}")
                elif 'error' in j:
                    msg = j['error'].get('message', '')
                    if 'isQueued' in msg or '10605' in msg:
                        stats["error_raw"] += 1
                        print(f"  [{elapsed:5.1f}s] #{req_id:3d} ❌ RAW JSON | {msg[:80]}...")
                    elif 'queue' in msg.lower():
                        stats["error_clean"] += 1
                        print(f"  [{elapsed:5.1f}s] #{req_id:3d} 🔄 CLEAN | {msg[:80]}")
                    else:
                        stats["other"] += 1
                        print(f"  [{elapsed:5.1f}s] #{req_id:3d} ⚠️  OTHER {resp.status} | {msg[:80]}")
                else:
                    stats["other"] += 1
                    print(f"  [{elapsed:5.1f}s] #{req_id:3d} ❓ HTTP {resp.status} | unknown")
            except:
                stats["other"] += 1
                print(f"  [{elapsed:5.1f}s] #{req_id:3d} 💥 PARSE ERROR | {data[:60]}")
                
    except Exception as e:
        with lock:
            stats["other"] += 1
            print(f"  [{time.time()-start_time:5.1f}s] #{req_id:3d} 💥 EXCEPTION | {e}")


def main():
    print(f"╔══════════════════════════════════════════╗")
    print(f"║  Qoder Stress Test - {TOTAL_REQUESTS} requests      ║")
    print(f"║  Model: {MODEL:<33s}║")
    print(f"║  Concurrent: {CONCURRENT:<28d}║")
    print(f"╚══════════════════════════════════════════╝")
    print()
    
    # Send requests in batches
    for batch_start in range(0, TOTAL_REQUESTS, CONCURRENT):
        batch_end = min(batch_start + CONCURRENT, TOTAL_REQUESTS)
        threads = []
        
        for i in range(batch_start, batch_end):
            t = threading.Thread(target=send_request, args=(i + 1,))
            threads.append(t)
            t.start()
        
        # Wait for batch to complete
        for t in threads:
            t.join(timeout=90)
        
        # Small delay between batches
        if batch_end < TOTAL_REQUESTS:
            time.sleep(0.5)
    
    # Summary
    elapsed = time.time() - start_time
    print()
    print(f"{'='*44}")
    print(f"  RESULTS ({elapsed:.1f}s total)")
    print(f"{'='*44}")
    print(f"  ✅ Success:       {stats['success']}")
    print(f"  🔄 Clean error:   {stats['error_clean']}  ← patch working!")
    print(f"  ❌ Raw JSON:      {stats['error_raw']}  ← patch NOT working!")
    print(f"  ⚠️  Other:         {stats['other']}")
    print(f"{'='*44}")
    
    if stats['error_raw'] > 0:
        print(f"\n  ❌ FAIL: {stats['error_raw']} raw JSON errors detected!")
        print(f"  Patch might not be active. Restart 9router.")
    elif stats['error_clean'] > 0:
        print(f"\n  ✅ PASS: All errors are clean!")
        print(f"  Patch is working correctly.")
    else:
        print(f"\n  ℹ️  No errors encountered - Qoder was not queued.")
        print(f"  Try again when Qoder is busy.")


if __name__ == "__main__":
    main()
