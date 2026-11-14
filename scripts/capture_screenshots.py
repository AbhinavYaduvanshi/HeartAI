"""Script to capture genuine browser screenshots of HeartAI Point 10 UI.

Automates Google Chrome via Chrome DevTools Protocol (CDP) to capture:
1. Desktop Light Theme View
2. Desktop Dark Theme View
3. Desktop Navbar & Controls
4. Clinical Tools Dropdown Menu Open
5. Aarogya Saathi AI Companion in Dark Theme
6. Aarogya Saathi AI Companion in Light Theme
7. Mobile Navigation Drawer (390px viewport)
"""

from __future__ import annotations

import asyncio
import base64
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = Path("reports/screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def send_cdp(
    ws: websockets.WebSocketClientProtocol,
    msg_id: int,
    method: str,
    params: dict | None = None,
) -> dict:
    payload = {"id": msg_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(payload))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get("id") == msg_id:
            return resp


async def capture_screenshot(
    ws: websockets.WebSocketClientProtocol,
    msg_id: int,
    filename: str,
    clip: dict | None = None,
) -> int:
    params: dict = {"format": "png"}
    if clip:
        params["clip"] = clip
    resp = await send_cdp(ws, msg_id, "Page.captureScreenshot", params)
    img_data = base64.b64decode(resp["result"]["data"])
    out_path = OUTPUT_DIR / filename
    out_path.write_bytes(img_data)
    print(f"Captured: {out_path} ({len(img_data):,} bytes)")
    return msg_id + 1


async def run_automation():
    # 1. Start NiceGUI demo server on port 8080
    print("Starting NiceGUI server...")
    server_proc = subprocess.Popen(
        [sys.executable, "motion_demo.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 2. Start Chrome in headless mode with remote debugging
    chrome_user_data = tempfile.mkdtemp(prefix="heartai_chrome_")
    chrome_port = 9222
    print(f"Starting Chrome with user-data-dir: {chrome_user_data}")
    chrome_proc = subprocess.Popen(
        [
            CHROME_PATH,
            "--headless=new",
            f"--remote-debugging-port={chrome_port}",
            "--remote-allow-origins=*",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={chrome_user_data}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Wait for NiceGUI to be ready
        print("Waiting for NiceGUI server on http://127.0.0.1:8080...")
        async with httpx.AsyncClient() as client:
            for _ in range(30):
                try:
                    r = await client.get("http://127.0.0.1:8080/")
                    if r.status_code == 200:
                        print("NiceGUI server is ready!")
                        break
                except Exception:
                    await asyncio.sleep(0.5)
            else:
                raise RuntimeError("Timeout waiting for NiceGUI server")

            # Wait for Chrome CDP port
            print("Connecting to Chrome CDP...")
            for _ in range(20):
                try:
                    r = await client.get(f"http://127.0.0.1:{chrome_port}/json")
                    tabs = r.json()
                    pages = [t for t in tabs if t.get("type") == "page"]
                    if pages:
                        ws_url = pages[0]["webSocketDebuggerUrl"]
                        print(f"Connected to page tab: {ws_url}")
                        break
                except Exception:
                    await asyncio.sleep(0.5)
            else:
                raise RuntimeError("Timeout waiting for Chrome CDP")

        # Connect WebSocket to tab
        async with websockets.connect(ws_url, max_size=20 * 1024 * 1024) as ws:
            mid = 1
            await send_cdp(ws, mid, "Page.enable")
            mid += 1
            await send_cdp(ws, mid, "DOM.enable")
            mid += 1
            await send_cdp(ws, mid, "Runtime.enable")
            mid += 1

            # Desktop viewport
            await send_cdp(
                ws,
                mid,
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": 1440,
                    "height": 920,
                    "deviceScaleFactor": 1,
                    "mobile": False,
                },
            )
            mid += 1

            # Navigate to HeartAI
            print("Navigating to HeartAI...")
            await send_cdp(ws, mid, "Page.navigate", {"url": "http://127.0.0.1:8080/"})
            mid += 1
            await asyncio.sleep(3.0)  # Allow GSAP, NiceGUI WS and CSS to fully hydrate

            # Ensure Light theme
            await send_cdp(
                ws,
                mid,
                "Runtime.evaluate",
                {
                    "expression": "window.HeartAIMotion && window.HeartAIMotion.setTheme('light');"
                },
            )
            mid += 1
            await asyncio.sleep(0.8)

            # 1. Desktop Light Theme View
            mid = await capture_screenshot(ws, mid, "01_desktop_light_theme.png")

            # 3. Desktop Navbar close-up / header view (Light Theme)
            mid = await capture_screenshot(
                ws,
                mid,
                "03_desktop_navbar.png",
                clip={"x": 0, "y": 0, "width": 1440, "height": 110, "scale": 1},
            )

            # 4. Open Clinical Tools dropdown
            print("Opening Clinical Tools dropdown...")
            await send_cdp(
                ws,
                mid,
                "Runtime.evaluate",
                {
                    "expression": "document.querySelector('[data-dropdown-toggle=\"tools-dropdown\"]').click();"
                },
            )
            mid += 1
            await asyncio.sleep(0.6)
            mid = await capture_screenshot(
                ws,
                mid,
                "04_clinical_tools_dropdown.png",
                clip={"x": 300, "y": 0, "width": 600, "height": 450, "scale": 1},
            )

            # Close dropdown
            await send_cdp(
                ws,
                mid,
                "Runtime.evaluate",
                {
                    "expression": "document.querySelectorAll('.heartai-dropdown-menu').forEach(m => m.classList.add('hidden'));"
                },
            )
            mid += 1
            await asyncio.sleep(0.3)

            # Switch to Dark theme
            print("Switching to Dark Theme...")
            await send_cdp(
                ws,
                mid,
                "Runtime.evaluate",
                {
                    "expression": "window.HeartAIMotion && window.HeartAIMotion.setTheme('dark');"
                },
            )
            mid += 1
            await asyncio.sleep(0.8)

            # 2. Desktop Dark Theme View
            mid = await capture_screenshot(ws, mid, "02_desktop_dark_theme.png")

            # 5. Open Aarogya Saathi AI dialog in Dark Theme
            print("Opening Aarogya Saathi dialog (Dark Theme)...")
            await send_cdp(
                ws,
                mid,
                "Runtime.evaluate",
                {
                    "expression": "document.querySelector('.aarogya-avatar-btn').click();"
                },
            )
            mid += 1
            await asyncio.sleep(1.2)  # NiceGUI modal animation
            mid = await capture_screenshot(
                ws,
                mid,
                "05_aarogya_saathi_dark_theme.png",
                clip={"x": 250, "y": 80, "width": 940, "height": 780, "scale": 1},
            )

            # Switch to Light Theme while modal is open
            print("Switching to Light Theme with Aarogya Saathi dialog open...")
            await send_cdp(
                ws,
                mid,
                "Runtime.evaluate",
                {
                    "expression": "window.HeartAIMotion && window.HeartAIMotion.setTheme('light');"
                },
            )
            mid += 1
            await asyncio.sleep(0.8)

            # 6. Aarogya Saathi AI dialog in Light Theme
            mid = await capture_screenshot(
                ws,
                mid,
                "06_aarogya_saathi_light_theme.png",
                clip={"x": 250, "y": 80, "width": 940, "height": 780, "scale": 1},
            )

            # Close dialogs
            print("Closing dialogs and setting mobile viewport...")
            await send_cdp(
                ws,
                mid,
                "Runtime.evaluate",
                {
                    "expression": "document.querySelectorAll('.q-dialog').forEach(d => { const closeBtn = d.querySelector('button[aria-label=\"Close\"]') || d.querySelector('.q-dialog__backdrop'); if(closeBtn) closeBtn.click(); });"
                },
            )
            mid += 1
            await asyncio.sleep(0.6)

            # Mobile Viewport (iPhone / modern mobile standard: 390 x 844)
            await send_cdp(
                ws,
                mid,
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": 390,
                    "height": 844,
                    "deviceScaleFactor": 2,
                    "mobile": True,
                },
            )
            mid += 1
            await asyncio.sleep(0.5)

            # Open Mobile Navigation Drawer
            print("Opening Mobile Navigation drawer...")
            await send_cdp(
                ws,
                mid,
                "Runtime.evaluate",
                {
                    "expression": "window.HeartAIMotion && window.HeartAIMotion.toggleMobileNav();"
                },
            )
            mid += 1
            await asyncio.sleep(0.8)

            # 7. Mobile Navigation Drawer View
            mid = await capture_screenshot(ws, mid, "07_mobile_navigation_drawer.png")

            print("\nALL SCREENSHOTS SUCCESSFULLY CAPTURED FROM LIVE HEADLESS BROWSER SESSION!")

    finally:
        print("Cleaning up processes...")
        try:
            chrome_proc.terminate()
            chrome_proc.wait(timeout=3)
        except Exception:
            chrome_proc.kill()

        try:
            server_proc.terminate()
            server_proc.wait(timeout=3)
        except Exception:
            server_proc.kill()

        try:
            shutil.rmtree(chrome_user_data, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(run_automation())
