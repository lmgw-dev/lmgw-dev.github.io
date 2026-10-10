#!/usr/bin/env python3
"""Screenshot a page of the local preview in headless Chrome, light or dark, as a full page.

Usage: scripts/shot.py <url> <out.png> [--dark] [--width 1440] [--mobile] [--at ID] [--clip-height PX]
       (`just shots` takes every page at desktop and phone width, both schemes, into target/shots/)

Needs google-chrome and python3-websockets. The Chrome profile is a temporary directory removed
on exit: /tmp is RAM on Fedora, and leftover profiles add up.
"""
import argparse
import asyncio
import base64
import json
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import urllib.request

import websockets


async def shoot(args: argparse.Namespace) -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    width = 390 if args.mobile else args.width
    profile = tempfile.mkdtemp(prefix="site-shot-")
    chrome = subprocess.Popen(
        ["google-chrome", "--headless", "--disable-gpu", "--hide-scrollbars",
         f"--remote-debugging-port={port}", f"--user-data-dir={profile}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    try:
        pages = []
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list") as resp:
                    pages = [t for t in json.load(resp) if t.get("type") == "page"]
                if pages:
                    break
            except OSError:
                pass
            await asyncio.sleep(0.2)
        async with websockets.connect(pages[0]["webSocketDebuggerUrl"], max_size=256 * 1024 * 1024) as ws:
            next_id = 0

            async def call(method: str, **params):
                nonlocal next_id
                next_id += 1
                await ws.send(json.dumps({"id": next_id, "method": method, "params": params}))
                while True:
                    reply = json.loads(await ws.recv())
                    if reply.get("id") == next_id:
                        if "error" in reply:
                            raise RuntimeError(f"{method}: {reply['error']}")
                        return reply.get("result", {})

            await call("Emulation.setEmulatedMedia", features=[
                {"name": "prefers-color-scheme", "value": "dark" if args.dark else "light"}])
            await call("Emulation.setDeviceMetricsOverride", width=width, height=900,
                       deviceScaleFactor=1, mobile=args.mobile)
            await call("Page.enable")
            await call("Page.navigate", url=args.url)
            await asyncio.sleep(1.5)
            # Scroll through once so lazy images load, as they would for a reader.
            await call("Runtime.evaluate", awaitPromise=True, expression="""(async () => {
                for (let y = 0; y < document.body.scrollHeight; y += 600) {
                    window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60));
                }
                window.scrollTo(0, 0);
                await Promise.all([...document.images].map(i => i.complete ? 0 : i.decode().catch(() => 0)));
            })()""")
            if args.open_details:
                await call("Runtime.evaluate", expression="document.querySelectorAll('details').forEach(d => d.open = true)")
            metrics = await call("Page.getLayoutMetrics")
            height = int(metrics["cssContentSize"]["height"])
            top = 0
            if args.at:
                # A long page (the API reference is ~100k px): capture a slice from an element's top.
                found = await call("Runtime.evaluate", returnByValue=True, expression=
                    f"(() => {{ const e = document.getElementById({json.dumps(args.at)}); "
                    "return e ? Math.round(e.getBoundingClientRect().top + window.scrollY) : -1; })()")
                top = found["result"]["value"]
                if top < 0:
                    raise SystemExit(f"no element with id {args.at}")
            if args.clip_height:
                height = min(args.clip_height, height - top)
            else:
                height -= top
            shot = await call("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                              clip={"x": 0, "y": top, "width": width, "height": height, "scale": 1})
            with open(args.out, "wb") as f:
                f.write(base64.b64decode(shot["data"]))
            print(f"wrote {args.out} ({width}x{height})")
    finally:
        # The whole process group: Chrome's helpers outlive the browser process and would write
        # into the profile after it was removed.
        os.killpg(chrome.pid, signal.SIGTERM)
        chrome.wait()
        for _ in range(10):
            shutil.rmtree(profile, ignore_errors=True)
            if not os.path.exists(profile):
                break
            time.sleep(0.2)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("url")
    p.add_argument("out")
    p.add_argument("--dark", action="store_true")
    p.add_argument("--width", type=int, default=1440)
    p.add_argument("--at", metavar="ID", help="start at the element with this id instead of the page top")
    p.add_argument("--clip-height", type=int, metavar="PX", help="capture only this many px (a slice of a long page)")
    p.add_argument("--open-details", action="store_true", help="expand every <details> first")
    p.add_argument("--mobile", action="store_true", help="390 px wide, as a phone")
    asyncio.run(asyncio.wait_for(shoot(p.parse_args()), timeout=90))


if __name__ == "__main__":
    main()
