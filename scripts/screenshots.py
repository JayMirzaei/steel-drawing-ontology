"""Take the README screenshots of the explorer app with a headless browser.

Usage::

    uv sync --group screenshots
    uv run playwright install chromium
    uv run python scripts/screenshots.py

Starts the app on a free local port, drives it with Playwright and writes PNG files into
``docs/screenshots/``. Only the synthetic example is shown.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "screenshots"
VIEWPORT = {"width": 1440, "height": 1000}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_until_up(url: str, seconds: float = 60) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url + "/_stcore/health", timeout=2):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"the app did not start at {url}")


def settle(page: Page) -> None:
    """Wait until Streamlit has finished running the script."""
    page.wait_for_timeout(500)
    page.wait_for_selector("[data-testid='stStatusWidget']", state="detached", timeout=120_000)
    page.wait_for_timeout(800)


def open_tab(page: Page, name: str) -> None:
    page.get_by_role("tab", name=name).click()
    settle(page)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    port = free_port()
    url = f"http://127.0.0.1:{port}"
    command = [
        sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "explorer.py"),
        "--server.headless=true", f"--server.port={port}", "--server.address=127.0.0.1",
        "--browser.gatherUsageStats=false", "--theme.base=light", "--client.toolbarMode=minimal",
    ]  # fmt: skip
    server = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_until_up(url)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport=VIEWPORT)
            page.goto(url)
            page.wait_for_selector("text=Steel drawing ontology explorer", timeout=120_000)
            settle(page)
            page.screenshot(path=OUTPUT / "vocabulary.png")

            open_tab(page, "Ask")
            page.get_by_label("Question").fill("What size is beam B3?")
            page.get_by_label("Question").press("Enter")
            settle(page)
            page.set_viewport_size({"width": VIEWPORT["width"], "height": 1500})
            settle(page)
            page.screenshot(path=OUTPUT / "ask.png")
            page.set_viewport_size(VIEWPORT)

            page.get_by_text("Example: broken variant").click()
            settle(page)
            open_tab(page, "Validate")
            page.screenshot(path=OUTPUT / "validate-broken.png")
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=30)
    for path in sorted(OUTPUT.glob("*.png")):
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
