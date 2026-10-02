import asyncio
import gzip
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
import websockets

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE_PATH):
    EDGE_PATH = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"


def measure_file_and_gen_stats(html_path: Path):
    print("=" * 70)
    print("1. Dashboard Build & Asset Size Performance")
    print("=" * 70)
    
    # 1. File Size
    size_bytes = html_path.stat().st_size
    size_kb = size_bytes / 1024
    size_mb = size_kb / 1024
    
    with open(html_path, "rb") as f:
        content = f.read()
        gzipped = gzip.compress(content)
        gzip_kb = len(gzipped) / 1024
        compression_ratio = (1 - (len(gzipped) / size_bytes)) * 100

    print(f"- Raw File Size: {size_kb:.1f} KB ({size_mb:.2f} MB)")
    print(f"- Gzip Compressed Size (Network Transfer): {gzip_kb:.1f} KB")
    print(f"- Compression Ratio: {compression_ratio:.1f}% reduction")
    
    # 2. Text line & element breakdown
    text_content = content.decode("utf-8", errors="ignore")
    lines = text_content.count("\n")
    script_count = text_content.count("<script")
    style_chars = sum(len(s) for s in text_content.split("<style>")[1:]) if "<style>" in text_content else 0
    table_rows = text_content.count("<tr")
    stock_cards = text_content.count('class="stock-card"')
    
    print(f"- Line Count: {lines:,} lines")
    print(f"- HTML Table Rows: {table_rows:,} rows")
    print(f"- Stock Cards Rendered: {stock_cards:,} cards")
    print(f"- Script Tags: {script_count} tags")

    # 3. Benchmark generation speed (3 runs)
    print("\nBenchmarking generate_report.py execution speed (3 consecutive runs)...")
    durations = []
    for r in range(3):
        t0 = time.perf_counter()
        subprocess.run(
            [sys.executable, "trading_system/generate_report.py", "--out", "gh-pages/index.html"],
            capture_output=True,
            check=True
        )
        dur = time.perf_counter() - t0
        durations.append(dur)
        print(f"  Run {r+1}: {dur:.3f}s")
    
    avg_gen = sum(durations) / len(durations)
    print(f"- Average Generation Time: {avg_gen:.3f}s")

    return {
        "size_kb": size_kb,
        "gzip_kb": gzip_kb,
        "compression_ratio": compression_ratio,
        "lines": lines,
        "table_rows": table_rows,
        "stock_cards": stock_cards,
        "avg_gen_time": avg_gen
    }


async def run_cdp_performance(html_path: Path, port: int = 9223):
    print("\n" + "=" * 70)
    print("2. Browser Runtime & Rendering Performance (Headless Edge CDP)")
    print("=" * 70)

    if not os.path.exists(EDGE_PATH):
        print("Edge executable not found. Skipping CDP browser test.")
        return {}

    file_url = f"file:///{html_path.resolve().as_posix()}"
    edge_proc = subprocess.Popen([
        EDGE_PATH,
        "--headless=new",
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1920,1080",
        file_url
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    metrics_result = {}

    try:
        # Wait for debugger
        ws_url = None
        for _ in range(25):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=1) as resp:
                    tabs = json.loads(resp.read().decode("utf-8"))
                    for t in tabs:
                        if t.get("type") == "page":
                            ws_url = t.get("webSocketDebuggerUrl")
                            break
                    if ws_url:
                        break
            except Exception:
                time.sleep(0.3)

        if not ws_url:
            raise RuntimeError("Could not connect to CDP.")

        async with websockets.connect(ws_url, max_size=35 * 1024 * 1024) as ws:
            msg_id = 0
            async def send_cmd(method: str, params: dict = None):
                nonlocal msg_id
                msg_id += 1
                cmd = {"id": msg_id, "method": method, "params": params or {}}
                await ws.send(json.dumps(cmd))
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if data.get("id") == msg_id:
                        return data

            async def eval_js(expr: str):
                res = await send_cmd("Runtime.evaluate", {
                    "expression": expr,
                    "returnByValue": True,
                    "awaitPromise": True
                })
                return res.get("result", {}).get("result", {}).get("value")

            # Enable CDP domains
            await send_cmd("Page.enable")
            await send_cmd("Performance.enable")
            await send_cmd("DOM.enable")

            # Wait for readyState complete
            for _ in range(30):
                ready = await eval_js("document.readyState")
                if ready == "complete":
                    break
                await asyncio.sleep(0.2)

            # 1. Navigation Timing Metrics (ms)
            nav_perf = await eval_js("""
                (function() {
                    const nav = performance.getEntriesByType('navigation')[0];
                    if (nav) {
                        return {
                            dns: nav.domainLookupEnd - nav.domainLookupStart,
                            tcp: nav.connectEnd - nav.connectStart,
                            ttfb: nav.responseStart - nav.requestStart,
                            domInteractive: nav.domInteractive - nav.startTime,
                            domContentLoaded: nav.domContentLoadedEventEnd - nav.startTime,
                            loadComplete: nav.loadEventEnd - nav.startTime,
                            domDuration: nav.domComplete - nav.domInteractive
                        };
                    }
                    const t = performance.timing;
                    return {
                        domInteractive: t.domInteractive - t.navigationStart,
                        domContentLoaded: t.domContentLoadedEventEnd - t.navigationStart,
                        loadComplete: t.loadEventEnd - t.navigationStart,
                        domDuration: t.domComplete - t.domInteractive
                    };
                })()
            """)

            print(f"- DOM Interactive: {nav_perf.get('domInteractive', 0):.1f} ms")
            print(f"- DOMContentLoaded Event: {nav_perf.get('domContentLoaded', 0):.1f} ms")
            print(f"- Full Page Load Complete: {nav_perf.get('loadComplete', 0):.1f} ms")
            print(f"- DOM Parsing & Construction Duration: {nav_perf.get('domDuration', 0):.1f} ms")

            # 2. Performance.getMetrics
            cdp_metrics_raw = await send_cmd("Performance.getMetrics")
            cdp_metrics = {m["name"]: m["value"] for m in cdp_metrics_raw.get("result", {}).get("metrics", [])}

            dom_nodes = cdp_metrics.get("Nodes", 0)
            layout_count = cdp_metrics.get("LayoutCount", 0)
            layout_duration_ms = cdp_metrics.get("LayoutDuration", 0) * 1000
            recalc_style_duration_ms = cdp_metrics.get("RecalcStyleDuration", 0) * 1000
            script_duration_ms = cdp_metrics.get("ScriptDuration", 0) * 1000
            task_duration_ms = cdp_metrics.get("TaskDuration", 0) * 1000
            js_heap_used_mb = cdp_metrics.get("JSHeapUsedSize", 0) / (1024 * 1024)
            js_heap_total_mb = cdp_metrics.get("JSHeapTotalSize", 0) / (1024 * 1024)

            print(f"- Total DOM Nodes: {int(dom_nodes):,} nodes")
            print(f"- Total Layout Count: {int(layout_count)}")
            print(f"- Layout Calculation Duration: {layout_duration_ms:.1f} ms")
            print(f"- Style Recalculation Duration: {recalc_style_duration_ms:.1f} ms")
            print(f"- V8 Script Execution Duration: {script_duration_ms:.1f} ms")
            print(f"- Total Main-Thread Task Duration: {task_duration_ms:.1f} ms")
            print(f"- V8 JS Heap Used: {js_heap_used_mb:.2f} MB / {js_heap_total_mb:.2f} MB")

            # 3. Interactive Response Latencies
            print("\nMeasuring Component Interaction Latencies (ms)...")

            # A. View Mode Switch Latency (Table -> Card -> Table)
            t_card_switch = await eval_js("""
                (function() {
                    const t0 = performance.now();
                    setViewMode('card');
                    const t1 = performance.now();
                    setViewMode('table');
                    return t1 - t0;
                })()
            """)
            print(f"- Table -> Card View Switching Latency: {t_card_switch:.2f} ms (Target: < 50ms)")

            # B. Quick Filter Execution Latency (TOP 10, Surge, Watchlist)
            t_filter = await eval_js("""
                (function() {
                    const t0 = performance.now();
                    applyQuickFilter('top10');
                    const t1 = performance.now();
                    applyQuickFilter('all');
                    return t1 - t0;
                })()
            """)
            print(f"- Quick Filter (TOP 10) Latency: {t_filter:.2f} ms (Target: < 50ms)")

            # C. Realtime Stock Search Latency (typing simulation)
            t_search = await eval_js("""
                (function() {
                    const input = document.getElementById('stock-search-input');
                    if (!input) return 0;
                    input.value = '삼성';
                    const t0 = performance.now();
                    filterStockTables();
                    const t1 = performance.now();
                    input.value = '';
                    filterStockTables();
                    return t1 - t0;
                })()
            """)
            print(f"- Realtime Search Filter Latency ('삼성'): {t_search:.2f} ms (Target: < 50ms)")

            # D. Mobile Viewport (390 x 844) Simulation
            print("\nSimulating Mobile Viewport (iPhone 14 / 390x844)...")
            await send_cmd("Emulation.setDeviceMetricsOverride", {
                "width": 390,
                "height": 844,
                "deviceScaleFactor": 3,
                "mobile": True
            })
            await asyncio.sleep(0.3)

            t_mobile_nav = await eval_js("""
                (function() {
                    const t0 = performance.now();
                    switchMobileNav('portfolio');
                    const t1 = performance.now();
                    switchMobileNav('ensemble');
                    return t1 - t0;
                })()
            """)
            print(f"- Mobile Bottom Nav Switching Latency: {t_mobile_nav:.2f} ms")

            t_hub_toggle = await eval_js("""
                (function() {
                    const t0 = performance.now();
                    openStrategyHub();
                    const t1 = performance.now();
                    closeStrategyHub();
                    return t1 - t0;
                })()
            """)
            print(f"- Mobile 37-Strategy Hub Slide-Up Latency: {t_hub_toggle:.2f} ms")

            metrics_result = {
                "dom_interactive_ms": nav_perf.get("domInteractive", 0),
                "dom_content_loaded_ms": nav_perf.get("domContentLoaded", 0),
                "load_complete_ms": nav_perf.get("loadComplete", 0),
                "dom_nodes": int(dom_nodes),
                "js_heap_used_mb": js_heap_used_mb,
                "js_heap_total_mb": js_heap_total_mb,
                "layout_duration_ms": layout_duration_ms,
                "script_duration_ms": script_duration_ms,
                "task_duration_ms": task_duration_ms,
                "card_switch_ms": t_card_switch,
                "filter_ms": t_filter,
                "search_ms": t_search,
                "mobile_nav_ms": t_mobile_nav,
                "hub_toggle_ms": t_hub_toggle,
            }

    finally:
        edge_proc.terminate()
        try:
            edge_proc.wait(timeout=3)
        except Exception:
            edge_proc.kill()

    return metrics_result


def inspect_quant_metrics():
    print("\n" + "=" * 70)
    print("3. Quant & Trading Model Performance (Dashboard Data)")
    print("=" * 70)

    res_dir = Path("trading_system/result")
    
    # 1. Coverage
    cov_path = res_dir / "strategy_data_coverage_report.txt"
    if cov_path.exists():
        with open(cov_path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        
        tot_syms = 0
        healthy_count = 0
        for l in lines:
            if "Total Evaluated Symbols:" in l:
                try:
                    tot_syms = int(l.split(":")[-1].strip())
                except Exception:
                    pass
            if "100.0%" in l or "HEALTHY" in l or "Valid)" in l:
                healthy_count += 1
        
        print(f"- Evaluated Symbols: {tot_syms:,} symbols")
        print(f"- Strategies with 100% Data Coverage: {healthy_count} / 37 strategies")

    # 2. Portfolio Allocation
    port_path = res_dir / "portfolio_allocation.txt"
    if port_path.exists():
        with open(port_path, encoding="utf-8", errors="ignore") as f:
            port_text = f.read()
        print(f"- Portfolio Allocation File Size: {len(port_text.splitlines())} lines")

    # 3. Ensemble Predictions
    ens_path = res_dir / "ensemble_predictions.txt"
    if ens_path.exists():
        with open(ens_path, encoding="utf-8", errors="ignore") as f:
            ens_lines = f.readlines()
        print(f"- Ensemble Output Lines: {len(ens_lines):,}")


def main():
    html_path = Path("gh-pages/index.html")
    if not html_path.exists():
        print(f"Error: {html_path} does not exist.")
        sys.exit(1)

    file_stats = measure_file_and_gen_stats(html_path)
    cdp_metrics = asyncio.run(run_cdp_performance(html_path))
    inspect_quant_metrics()

    print("\n" + "=" * 70)
    print("Dashboard Performance Benchmark Summary")
    print("=" * 70)
    print(f"• Generation Latency: {file_stats['avg_gen_time']:.2f}s (Clean offline build)")
    print(f"• HTML Payload: {file_stats['size_kb']:.1f} KB (Gzip: {file_stats['gzip_kb']:.1f} KB)")
    print(f"• DOM Ready: {cdp_metrics.get('dom_content_loaded_ms', 0):.1f} ms")
    print(f"• Full Load: {cdp_metrics.get('load_complete_ms', 0):.1f} ms")
    print(f"• V8 Heap: {cdp_metrics.get('js_heap_used_mb', 0):.2f} MB")
    print(f"• Card Switch Latency: {cdp_metrics.get('card_switch_ms', 0):.2f} ms")
    print(f"• Instant Search Filter: {cdp_metrics.get('search_ms', 0):.2f} ms")
    print(f"• Mobile Nav Touch Response: {cdp_metrics.get('mobile_nav_ms', 0):.2f} ms")
    print("=" * 70)


if __name__ == "__main__":
    main()
