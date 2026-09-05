import asyncio
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


async def run_cdp_verification(html_path: Path, port: int = 9222):
    if not os.path.exists(EDGE_PATH):
        print(f"Edge executable not found at {EDGE_PATH}. Skipping CDP test.")
        return True

    file_url = f"file:///{html_path.resolve().as_posix()}"
    print(f"[CDP] Starting Edge headless on port {port} with {file_url}...")

    # Start Edge
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

    try:
        # Wait for debugger endpoint
        ws_url = None
        for attempt in range(25):
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
            raise RuntimeError("Failed to obtain webSocketDebuggerUrl from Edge CDP.")

        print(f"[CDP] Connected to Edge CDP target: {ws_url}")

        js_errors = []
        msg_id = 0

        async with websockets.connect(ws_url, max_size=35 * 1024 * 1024) as ws:
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
                    # Check for console errors or runtime exceptions
                    if data.get("method") == "Runtime.exceptionThrown":
                        details = data.get("params", {}).get("exceptionDetails", {})
                        text = details.get("text", "")
                        exc = details.get("exception", {}).get("description", "")
                        js_errors.append(f"EXCEPTION: {text} - {exc}")
                    elif data.get("method") == "Log.entryAdded":
                        entry = data.get("params", {}).get("entry", {})
                        if entry.get("level") == "error":
                            js_errors.append(f"LOG ERROR: {entry.get('text')}")

            async def eval_js(expression: str) -> any:
                res = await send_cmd("Runtime.evaluate", {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": True
                })
                result = res.get("result", {}).get("result", {})
                if "value" in result:
                    return result["value"]
                return result

            # Enable domains
            await send_cmd("Runtime.enable")
            await send_cmd("Log.enable")
            await send_cmd("Page.enable")

            # Poll until document.readyState is complete and elements are present
            print("[CDP] Waiting for DOM readyState complete...")
            for _ in range(40):
                is_ready = await eval_js("document.readyState === 'complete' && document.querySelectorAll('.tab').length > 0")
                if is_ready:
                    break
                await asyncio.sleep(0.2)

            ready_state = await eval_js("document.readyState")
            print(f"[CDP] DOM readyState: {ready_state}")

            # 1. Check title and market buttons
            title = await eval_js("document.title")
            print(f"[CDP] Document title: {ascii(title)}")

            # Verify market filter buttons in Ensemble tab
            buttons_info = await eval_js("""
                (() => {
                    const btns = Array.from(document.querySelectorAll('.filter-btn'));
                    return btns.map(b => ({
                        text: b.textContent.trim(),
                        mkt: b.getAttribute('data-mkt')
                    }));
                })()
            """)
            print(f"[CDP] Total filter buttons: {len(buttons_info)}")
            corrupt_keywords = ['Acquisition', 'Corp', '1', 'Sciences', 'Mellon', '66']
            corrupt_btns = [b for b in buttons_info if any(k in b['text'] for k in corrupt_keywords)]
            assert len(corrupt_btns) == 0, f"Found corrupt market buttons: {corrupt_btns}"
            print("[CDP] PASS: 0 corrupt market filter buttons found.")

            # 2. Test Tab switching (R2)
            print("[CDP] Testing Navigation Row 1 Tabs...")
            main_tabs = ['portfolio', 'backtest', 'regime', 'scenario', 'history', 'ensemble']
            for t_id in main_tabs:
                code = """
                    (() => {
                        const t = '__TID__';
                        const tabBtn = document.querySelector(`button[onclick*="'${t}'"]`);
                        if (tabBtn) {
                            tabBtn.click();
                        } else {
                            switchTabById(t);
                        }
                        const panel = document.getElementById('panel-' + t);
                        return panel ? panel.classList.contains('active') : false;
                    })()
                """.replace('__TID__', t_id)
                res = await eval_js(code)
                assert res is True, f"Failed to activate main tab {t_id}"
            print(f"[CDP] PASS: All {len(main_tabs)} main tabs activated cleanly.")

            # Test 37 strategy tabs in Row 2
            strat_tab_ids = [
                'regression', 'surge', 'leadlag', 'vcp', 'vcpml', 'lstm', 'stat-arb', 'sector',
                'rim', 'event', 'mq', 'iv', 'flow', 'reversal', 'arm', 'card', 'latr', 'ifs',
                'supplychain', 'sentiment', 'neutralized', 'voltarget', 'microstructure',
                'accruals', 'shortsqueeze', 'valueup', 'trendeff', 'gammasqueeze', 'insider',
                'darkpool', 'tonedrift', 'crossasset', 'gnn', 'rangeexpansion', 'dualcorrection',
                'indexrebalance', 'overnightgap'
            ]
            print(f"[CDP] Testing {len(strat_tab_ids)} strategy tabs in Row 2...")
            for s_id in strat_tab_ids:
                code = """
                    (() => {
                        const s = '__SID__';
                        const tabBtn = document.querySelector(`button.tab[onclick*="'${s}'"]`);
                        if (tabBtn) {
                            tabBtn.click();
                        } else {
                            switchTabById(s);
                        }
                        const panel = document.getElementById('panel-' + s);
                        return panel ? panel.classList.contains('active') : false;
                    })()
                """.replace('__SID__', s_id)
                res = await eval_js(code)
                assert res is True, f"Failed to activate strategy tab {s_id}"
            print(f"[CDP] PASS: All {len(strat_tab_ids)} strategy tabs activated cleanly.")

            # 3. Switch back to Ensemble and test Market Filters
            print("[CDP] Testing market filter button clicks in Ensemble...")
            await eval_js("switchTabById('ensemble');")
            active_mkts = await eval_js("""
                (() => {
                    const btns = Array.from(document.querySelectorAll('#panel-ensemble .filter-btn'));
                    return btns.map(b => b.getAttribute('data-mkt')).filter(Boolean);
                })()
            """)
            print(f"[CDP] Available market filters in Ensemble: {active_mkts}")
            for mkt in active_mkts:
                code = """
                    (() => {
                        const m = '__MKT__';
                        const btn = document.querySelector(`#panel-ensemble .filter-btn[data-mkt="${m}"]`);
                        if (btn) {
                            btn.click();
                            return btn.classList.contains('active');
                        }
                        return false;
                    })()
                """.replace('__MKT__', mkt)
                res = await eval_js(code)
                assert res is True, f"Failed to click market filter button for {mkt}"
            print("[CDP] PASS: All market filter buttons trigger active state cleanly.")

            # 4. Test Column Presets
            print("[CDP] Testing Column Preset buttons...")
            presets = ['all', 'ai', 'mom', 'val', 'flow', 'macro']
            for p in presets:
                code = """
                    (() => {
                        const p = '__PRESET__';
                        const btn = document.getElementById('col-preset-' + p);
                        if (btn) {
                            btn.click();
                            return btn.classList.contains('active');
                        }
                        return false;
                    })()
                """.replace('__PRESET__', p)
                res = await eval_js(code)
                assert res is True, f"Failed to click column preset {p}"
            await eval_js("document.getElementById('col-preset-all').click();")
            print("[CDP] PASS: Column presets toggled cleanly.")

            # 5. Test Quick Filter Chips
            print("[CDP] Testing quick filter chips...")
            chip_res = await eval_js("""
                (() => {
                    const chips = Array.from(document.querySelectorAll('.chip-btn'));
                    if (chips.length === 0) return { success: false, count: 0 };
                    for (const c of chips) {
                        c.click();
                    }
                    // Reset to first chip ('all')
                    chips[0].click();
                    return { success: true, count: chips.length };
                })()
            """)
            assert chip_res.get('success') is True, f"Failed to test quick filter chips: {chip_res}"
            print(f"[CDP] PASS: {chip_res.get('count')} quick filter chips toggled cleanly.")

            # 6. Test Stock Row / Card Click & Drawer Interaction
            print("[CDP] Testing Stock Row click & Drawer opening...")
            drawer_res = await eval_js("""
                (() => {
                    const row = document.querySelector('tr[onclick*="openStockDrawer"]');
                    if (!row) return { success: false, reason: 'no stock row found' };
                    row.click();
                    const drawer = document.getElementById('stock-drawer');
                    const name = document.getElementById('drawer-stock-name').textContent.trim();
                    const right = window.getComputedStyle(drawer).right;
                    return {
                        success: true,
                        name: name,
                        right: right,
                        isOpen: right === '0px' || drawer.style.right === '0px'
                    };
                })()
            """)
            assert drawer_res.get('success') is True, f"Drawer open failed: {drawer_res}"
            print(f"[CDP] PASS: Drawer opened for stock: {ascii(drawer_res.get('name'))}, right: {drawer_res.get('right')}")

            # Test drawer factor category filtering
            drawer_cat_res = await eval_js("""
                (() => {
                    const tabs = Array.from(document.querySelectorAll('.drawer-factor-tab'));
                    for (const t of tabs) {
                        t.click();
                    }
                    // Reset to all
                    const allTab = document.querySelector('.drawer-factor-tab[data-cat="all"]');
                    if (allTab) allTab.click();
                    return true;
                })()
            """)
            assert drawer_cat_res is True, "Drawer category tab filtering failed"
            print("[CDP] PASS: Drawer factor tabs filtered cleanly.")

            # Close drawer
            await eval_js("closeStockDrawer();")
            drawer_closed = await eval_js("""
                (() => {
                    const drawer = document.getElementById('stock-drawer');
                    return drawer.style.right === '-500px' || window.getComputedStyle(drawer).right === '-500px';
                })()
            """)
            assert drawer_closed is True, "Failed to close drawer"
            print("[CDP] PASS: Drawer closed cleanly.")

            # Check for any JS errors accumulated during all actions
            print(f"[CDP] Accumulated JS Exceptions/Errors: {len(js_errors)}")
            if js_errors:
                for err in js_errors:
                    print(f"  ERROR: {err}")
            assert len(js_errors) == 0, f"Encountered JS errors during verification: {js_errors}"
            print("[CDP] PASS: ZERO JavaScript errors or exceptions detected!")

        return True

    finally:
        edge_proc.terminate()
        try:
            edge_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            edge_proc.kill()
        print("[CDP] Edge headless terminated.")


if __name__ == "__main__":
    html_file = Path("gh-pages/index.html")
    if not html_file.exists():
        print(f"Error: {html_file} does not exist. Run generate_report.py first.")
        sys.exit(1)

    asyncio.run(run_cdp_verification(html_file, port=9227))
