import os
import sys
import re
import time
import asyncio
import random
import threading
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Callable, Dict, Any, Tuple, Union

# Set Playwright global cache
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "ms-playwright"
)

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright._impl._driver import compute_driver_executable


@dataclass
class ResolvedLink:
    index: int
    original_url: str
    part_name: str
    direct_url: Optional[str] = None
    elapsed_sec: float = 0.0
    attempts: int = 1
    status: str = "pending"  # "pending" | "resolved" | "failed" | "cancelled"


def detect_browser_channel() -> Optional[str]:
    """Detect installed Edge or Chrome browser channel."""
    chrome_path = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Google", "Chrome", "Application", "chrome.exe"
    )
    edge_path = os.path.join(
        os.environ.get("PROGRAMFILES(X86)", os.environ.get("PROGRAMFILES", "")),
        "Microsoft", "Edge", "Application", "msedge.exe"
    )
    edge_path_local = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Microsoft", "Edge", "Application", "msedge.exe"
    )

    if os.path.exists(edge_path) or os.path.exists(edge_path_local):
        return "msedge"
    elif os.path.exists(chrome_path):
        return "chrome"
    return None


class ResolutionEngine:
    """
    High-performance multi-tab link resolution engine for fuckingfast.co.
    Features:
      - Concurrent tab worker pool (3-4x speedup)
      - Cloudflare Turnstile automatic bypass
      - Automated retry queue for dropped/timed-out links
      - Real-time ETA and per-link speed metrics
      - Memory-efficient tab reuse
      - Instant cancellation handling without UI deadlocks
    """

    def __init__(self, concurrency: int = 3, max_retries: int = 2, headless: bool = False):
        self.concurrency = max(1, min(concurrency, 8))
        self.max_retries = max(0, max_retries)
        self.headless = headless

    async def _launch_browser(self, p) -> Browser:
        channel = detect_browser_channel()
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--window-position=-3000,-3000",
            "--window-size=1280,720",
            "--no-first-run",
            "--no-default-browser-check"
        ]

        if channel:
            try:
                return await p.chromium.launch(
                    headless=self.headless,
                    channel=channel,
                    args=launch_args
                )
            except Exception:
                pass

        # Fallback to default chromium
        try:
            return await p.chromium.launch(headless=self.headless, args=launch_args)
        except Exception:
            try:
                res = compute_driver_executable()
                if isinstance(res, tuple) and len(res) == 2:
                    driver_exe, driver_cli = res
                    subprocess.run(
                        [str(driver_exe), str(driver_cli), "install", "chromium"],
                        capture_output=True,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    )
            except Exception:
                pass
            return await p.chromium.launch(headless=self.headless, channel=channel)

    async def _resolve_single_link(self, page: Page, ff_url: str, cancel_event: Optional[Union[threading.Event, asyncio.Event]]) -> Tuple[Optional[str], float]:
        """
        Navigate to a fuckingfast.co URL, wait for Cloudflare Turnstile token, and extract direct download URL.
        """
        if cancel_event and cancel_event.is_set():
            return None, 0.0

        direct_url = None

        def on_response(response):
            nonlocal direct_url
            if "/go" in response.url or "dl.fuckingfast.co" in response.url:
                headers = response.headers
                if "hx-redirect" in headers:
                    direct_url = headers["hx-redirect"]
                elif "location" in headers:
                    direct_url = headers["location"]

        page.on("response", on_response)
        t0 = time.time()

        try:
            await page.goto(ff_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for turnstile token or dlCleared
            token = ""
            for _ in range(60):
                if cancel_event and cancel_event.is_set():
                    return None, time.time() - t0
                try:
                    token = await page.evaluate("() => window.turnstileToken || ''")
                    cleared = await page.evaluate("() => window.dlCleared || false")
                    if token or cleared:
                        break
                except Exception:
                    pass
                await asyncio.sleep(0.1)

            # If token not present, try clicking the Cloudflare turnstile checkbox frame
            if not token and not (cancel_event and cancel_event.is_set()):
                for frame in page.frames:
                    if "turnstile" in frame.url or "cloudflare" in frame.url:
                        try:
                            await frame.click("body", timeout=1200)
                        except Exception:
                            pass
                for _ in range(35):
                    if cancel_event and cancel_event.is_set():
                        return None, time.time() - t0
                    try:
                        token = await page.evaluate("() => window.turnstileToken || ''")
                        if token:
                            break
                    except Exception:
                        pass
                    await asyncio.sleep(0.1)

            if cancel_event and cancel_event.is_set():
                return None, time.time() - t0

            # Execute fetch to /go endpoint
            part_id = ff_url.split("fuckingfast.co/")[1].split("#")[0].strip("/")
            js_script = f"""
                async () => {{
                    const resp = await fetch('/f/{part_id}/go', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'HX-Request': 'true'
                        }},
                        body: 'cf-turnstile-response=' + encodeURIComponent(window.turnstileToken || '')
                    }});
                    return resp.headers.get('HX-Redirect') || resp.headers.get('Location') || '';
                }}
            """
            try:
                res = await page.evaluate(js_script)
                if res:
                    direct_url = res
            except Exception:
                pass

        except Exception:
            pass
        finally:
            page.remove_listener("response", on_response)

        if direct_url and "#" in ff_url:
            part_hash = ff_url.split("#", 1)[1]
            if part_hash and "#" not in direct_url:
                direct_url = f"{direct_url}#{part_hash}"

        elapsed = time.time() - t0
        return direct_url, elapsed

    async def fetch_pastebin_links(self, pastebin_url: str, log_cb: Optional[Callable[[str], None]] = None) -> List[str]:
        """
        Fetch and decrypt a FitGirl pastebin page using browser context.
        """
        import scraper

        if log_cb:
            log_cb(f"Phase 1: Fetching and decrypting pastebin: {pastebin_url}")

        async with async_playwright() as p:
            browser = await self._launch_browser(p)
            context = await browser.new_context(viewport={"width": 1280, "height": 720})
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
            page = await context.new_page()
            await page.goto(pastebin_url, wait_until="networkidle", timeout=45000)
            await asyncio.sleep(1.5)

            content = await page.content()
            links = scraper.extract_links_from_pastebin_html(content)
            await browser.close()
            return links

    async def resolve_all_async(
        self,
        urls: List[str],
        on_progress: Optional[Callable[[int, int, float, float, int, str, Optional[str], str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        on_retry_pass: Optional[Callable[[int, int, int], None]] = None,
        on_start_part: Optional[Callable[[str, int], None]] = None,
        cancel_event: Optional[Union[threading.Event, asyncio.Event]] = None
    ) -> List[ResolvedLink]:
        """
        Resolve a list of fuckingfast.co URLs concurrently with automatic retries and clean cancellation.
        """
        if not urls:
            return []

        total_count = len(urls)
        results: List[ResolvedLink] = []
        for i, u in enumerate(urls):
            part_name = u.split("#")[-1] if "#" in u else u.split("/")[-1]
            results.append(ResolvedLink(index=i, original_url=u, part_name=part_name))

        def log(msg: str):
            if on_log:
                on_log(msg)

        log(f"Starting resolution engine: {total_count} links across {self.concurrency} concurrent tabs (max {self.max_retries} retries)")

        t_start = time.time()
        completed_durations: List[float] = []

        async with async_playwright() as p:
            browser = await self._launch_browser(p)
            context = await browser.new_context(viewport={"width": 1280, "height": 720})
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")

            # Worker pages
            pages: List[Page] = []
            for _ in range(self.concurrency):
                pg = await context.new_page()
                pg.on("download", lambda dl: asyncio.create_task(dl.cancel()))
                pages.append(pg)

            known_pages = set(pages)

            async def on_new_page(pop: Page):
                if pop not in known_pages:
                    try:
                        await pop.close()
                    except Exception:
                        pass

            context.on("page", lambda pop: asyncio.create_task(on_new_page(pop)))

            # Resolution Passes (Pass 1 + Retries)
            pending_indices = list(range(total_count))
            current_attempt = 1

            while pending_indices and current_attempt <= (self.max_retries + 1):
                if cancel_event and cancel_event.is_set():
                    log("Resolution stopped (cancellation received).")
                    break

                if current_attempt > 1:
                    log(f"🔁 Auto-Retry Pass {current_attempt}/{self.max_retries + 1}: Retrying {len(pending_indices)} failed links...")
                    if on_retry_pass:
                        on_retry_pass(len(pending_indices), current_attempt, self.max_retries + 1)
                    await asyncio.sleep(random.uniform(1.0, 2.0))

                queue = asyncio.Queue()
                for idx in pending_indices:
                    queue.put_nowait(idx)

                active_workers = min(self.concurrency, len(pending_indices))

                async def worker(worker_id: int, page: Page):
                    while not queue.empty():
                        if cancel_event and cancel_event.is_set():
                            break
                        try:
                            idx = queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break

                        item = results[idx]
                        item.attempts = current_attempt
                        item.status = "resolving"

                        if on_start_part:
                            try:
                                on_start_part(item.part_name, worker_id)
                            except Exception:
                                pass

                        direct_url, elapsed = await self._resolve_single_link(page, item.original_url, cancel_event)
                        item.elapsed_sec = elapsed

                        if cancel_event and cancel_event.is_set():
                            item.status = "cancelled"
                            break

                        if direct_url:
                            item.direct_url = direct_url
                            item.status = "resolved"
                            completed_durations.append(elapsed)
                            log(f"⚡ [Tab {worker_id}] Resolved {item.part_name} in {elapsed:.1f}s")
                        else:
                            item.status = "failed"
                            log(f"⚠️ [Tab {worker_id}] Failed {item.part_name} ({elapsed:.1f}s)")

                        resolved_so_far = sum(1 for r in results if r.status == "resolved")
                        avg_speed = (sum(completed_durations) / len(completed_durations)) if completed_durations else 4.0
                        remaining_links = total_count - resolved_so_far
                        eta = (remaining_links * avg_speed) / max(1, self.concurrency)

                        if on_progress:
                            on_progress(
                                resolved_so_far,
                                total_count,
                                avg_speed,
                                eta,
                                active_workers,
                                item.part_name,
                                item.direct_url,
                                item.status
                            )

                workers = [
                    asyncio.create_task(worker(i + 1, pages[i]))
                    for i in range(active_workers)
                ]

                await asyncio.gather(*workers, return_exceptions=True)

                if cancel_event and cancel_event.is_set():
                    break

                # Find which links are still failed
                pending_indices = [i for i, r in enumerate(results) if r.status != "resolved"]
                current_attempt += 1

            await browser.close()

        total_elapsed = time.time() - t_start
        resolved_count = sum(1 for r in results if r.status == "resolved")
        avg_per_link = total_elapsed / resolved_count if resolved_count > 0 else 0
        if not (cancel_event and cancel_event.is_set()):
            log(f"🚀 Speed Pipeline Finished: {resolved_count}/{total_count} resolved in {total_elapsed:.1f}s (Avg {avg_per_link:.1f}s/part)!")
        else:
            log(f"🛑 Pipeline Cancelled: {resolved_count}/{total_count} resolved before cancellation.")

        return results

    def resolve_all(
        self,
        urls: List[str],
        on_progress: Optional[Callable[[int, int, float, float, int, str, Optional[str], str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        on_retry_pass: Optional[Callable[[int, int, int], None]] = None,
        on_start_part: Optional[Callable[[str, int], None]] = None,
        cancel_event: Optional[Union[threading.Event, asyncio.Event]] = None
    ) -> List[ResolvedLink]:
        """Synchronous wrapper for resolve_all_async."""
        return asyncio.run(self.resolve_all_async(urls, on_progress, on_log, on_retry_pass, on_start_part, cancel_event))
