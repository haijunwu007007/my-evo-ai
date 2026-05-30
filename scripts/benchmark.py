"""
AUTO-EVO-AI V0.1 — 性能压测脚本
上市生产级: API吞吐量/延迟/P99
"""
import time, json, threading, statistics, urllib.request

HOST = "http://127.0.0.1:8765"

def bench(concurrency: int = 10, total: int = 200, endpoint: str = "/api/status"):
    latencies = []
    errors = 0
    lock = threading.Lock()
    done = [0]

    def worker():
        nonlocal errors
        while True:
            with lock:
                if done[0] >= total:
                    break
                done[0] += 1
            start = time.perf_counter()
            try:
                r = urllib.request.urlopen(f"{HOST}{endpoint}", timeout=10)
                r.read()
                lat = (time.perf_counter() - start) * 1000
                with lock:
                    latencies.append(lat)
            except Exception:
                with lock:
                    errors += 1

    threads = [threading.Thread(target=worker) for _ in range(concurrency)]
    t0 = time.perf_counter()
    for t in threads: t.start()
    for t in threads: t.join()
    elapsed = time.perf_counter() - t0

    if not latencies:
        return {"error": "no successful requests", "errors": errors}

    latencies.sort()
    return {
        "endpoint": endpoint,
        "concurrency": concurrency,
        "total": total,
        "elapsed_s": round(elapsed, 2),
        "throughput_rps": round(total / elapsed, 1),
        "p50_ms": round(statistics.median(latencies), 1),
        "p95_ms": round(latencies[int(len(latencies)*0.95)], 1),
        "p99_ms": round(latencies[int(len(latencies)*0.99)], 1),
        "avg_ms": round(statistics.mean(latencies), 1),
        "min_ms": round(min(latencies), 1),
        "max_ms": round(max(latencies), 1),
        "errors": errors,
    }

if __name__ == "__main__":
    endpoints = ["/api/status", "/api/modules/categories", "/api/scheduler/status"]
    for ep in endpoints:
        r = bench(concurrency=5, total=50, endpoint=ep)
        print(f"\n{'='*50}\n{ep}\n{'='*50}")
        for k, v in r.items():
            print(f"  {k}: {v}")
