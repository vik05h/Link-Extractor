import os
import sys
import io
import time
import subprocess
import threading
import multiprocessing
import pyperclip
import customtkinter as ctk

# Force Playwright to use the user's global browser cache
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "ms-playwright"
)

from playwright.sync_api import sync_playwright
from playwright._impl._driver import compute_driver_executable

# Set appearance mode and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def detect_browser_channel():
    """Detect which real browser is installed (Edge or Chrome)."""
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


class LinkExtractorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FitGirl Link Extractor - Auto Captcha & Direct Link Grabber")
        self.geometry("900x700")
        self.minsize(750, 550)

        self.pastebin_links = []
        self.resolved_links = []
        self.is_running = False
        self.cancel_requested = False

        self._create_ui()

    def _create_ui(self):
        # ── Header ──
        header = ctk.CTkFrame(self, corner_radius=10)
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header,
            text="⚡ FitGirl Direct Link Extractor for JDownloader 2",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            header,
            text="Paste a FitGirl pastebin URL. This app will automatically bypass Cloudflare Turnstile "
                 "and extract TRUE direct download links (dl.fuckingfast.co) WITHOUT starting browser downloads. "
                 "Simply copy and paste them into JDownloader 2!",
            font=ctk.CTkFont(size=12),
            text_color="gray70",
            wraplength=800,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 15))

        # ── URL Input ──
        input_frame = ctk.CTkFrame(self, corner_radius=10)
        input_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            input_frame,
            text="Pastebin URL:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        entry_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        entry_row.pack(fill="x", padx=15, pady=(0, 15))

        self.url_entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="https://paste.fitgirl-repacks.site/?a213e0a5ff89ce97#BA7xr...",
            font=ctk.CTkFont(size=13),
            height=38
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.start_btn = ctk.CTkButton(
            entry_row,
            text="Extract & Resolve All",
            command=self._on_start,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38, width=170,
            fg_color="#1f538d", hover_color="#14375e"
        )
        self.start_btn.pack(side="right")

        # ── Progress ──
        self.progress_frame = ctk.CTkFrame(self, corner_radius=10)
        self.progress_frame.pack(fill="x", padx=20, pady=(5, 5))

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Ready",
            font=ctk.CTkFont(size=13),
            text_color="#4CAF50"
        )
        self.progress_label.pack(side="left", padx=15, pady=10)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=300)
        self.progress_bar.pack(side="right", padx=15, pady=10)
        self.progress_bar.set(0)

        self.cancel_btn = ctk.CTkButton(
            self.progress_frame,
            text="Cancel",
            command=self._on_cancel,
            font=ctk.CTkFont(size=12),
            height=30, width=80,
            fg_color="#757575", hover_color="#616161",
            state="disabled"
        )
        self.cancel_btn.pack(side="right", padx=5, pady=10)

        # ── Results Tabs ──
        middle = ctk.CTkFrame(self, corner_radius=10)
        middle.pack(fill="both", expand=True, padx=20, pady=10)

        self.tabview = ctk.CTkTabview(middle)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_resolved = self.tabview.add("Direct Download URLs (0)")
        self.tab_log = self.tabview.add("Activity Log")

        self.resolved_textbox = ctk.CTkTextbox(
            self.tab_resolved,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none"
        )
        self.resolved_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_textbox = ctk.CTkTextbox(
            self.tab_log,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        # ── Bottom Actions ──
        bottom = ctk.CTkFrame(self, corner_radius=10)
        bottom.pack(fill="x", padx=20, pady=(10, 20))

        self.copy_btn = ctk.CTkButton(
            bottom,
            text="📋 Copy All Direct URLs to Clipboard",
            command=self._copy_to_clipboard,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            fg_color="#2e7d32", hover_color="#1b5e20",
            state="disabled"
        )
        self.copy_btn.pack(side="right", padx=15, pady=15)

        self.count_label = ctk.CTkLabel(
            bottom,
            text="",
            font=ctk.CTkFont(size=13),
            text_color="gray70"
        )
        self.count_label.pack(side="left", padx=15, pady=15)

    # ── Logging ──
    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log_textbox.insert("end", f"[{ts}] {msg}\n")
        self.log_textbox.see("end")

    def set_progress(self, text, fraction=None, color="white"):
        self.progress_label.configure(text=text, text_color=color)
        if fraction is not None:
            self.progress_bar.set(fraction)

    # ── Start / Cancel ──
    def _on_start(self):
        url = self.url_entry.get().strip()
        if not url:
            self.set_progress("Enter a pastebin URL first", color="#FF5252")
            return

        self.is_running = True
        self.cancel_requested = False
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.copy_btn.configure(state="disabled")
        self.resolved_textbox.delete("1.0", "end")
        self.resolved_links = []
        self.pastebin_links = []

        threading.Thread(target=self._run_full_pipeline, args=(url,), daemon=True).start()

    def _on_cancel(self):
        self.cancel_requested = True
        self.log("Cancellation requested by user.")

    # ── Full Pipeline ──
    def _run_full_pipeline(self, pastebin_url):
        try:
            # ── Phase 1: Extract links from pastebin ──
            self.after(0, lambda: self.set_progress("Phase 1: Fetching pastebin page...", 0.05, "#FFC107"))
            self.log(f"Phase 1: Fetching pastebin: {pastebin_url}")

            with sync_playwright() as p:
                browser = self._launch_browser(p, headless=True)
                page = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ).new_page()

                page.goto(pastebin_url, wait_until="networkidle")
                time.sleep(2)

                for a in page.query_selector_all("a"):
                    href = a.get_attribute("href")
                    if href and "fuckingfast.co" in href:
                        if href not in self.pastebin_links:
                            self.pastebin_links.append(href)

                browser.close()

            count = len(self.pastebin_links)
            self.log(f"Phase 1 complete: found {count} links")
            if count == 0:
                self.after(0, lambda: self.set_progress("No fuckingfast links found on page", color="#FF5252"))
                self._finish()
                return

            # ── Phase 2: Instant JS resolution via real browser ──
            self.after(0, lambda: self.set_progress(
                f"Phase 2: Resolving 0/{count} links...", 0.1, "#2196F3"
            ))
            self.log(f"Phase 2: Resolving {count} links to direct dl.fuckingfast.co URLs")

            channel = detect_browser_channel()
            if not channel:
                self.log("ERROR: No Chrome or Edge browser found.")
                self.after(0, lambda: self.set_progress("No Chrome/Edge browser found!", color="#FF5252"))
                self._finish()
                return

            self.log(f"Using system browser: {channel}")

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=False,
                    channel=channel,
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = browser.new_context(viewport={"width": 1280, "height": 720})
                context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")

                # Auto-close ad popups & cancel any file download if triggered
                context.on("page", lambda pop: pop.close() if pop != context.pages[0] else None)

                page = context.new_page()
                page.on("download", lambda dl: self._cancel_download(dl))

                for idx, ff_link in enumerate(self.pastebin_links):
                    if self.cancel_requested:
                        break

                    part_name = ff_link.split("#")[-1] if "#" in ff_link else ff_link.split("/")[-1]
                    frac = 0.1 + (0.85 * (idx + 1) / count)
                    self.after(0, lambda i=idx, n=part_name, f=frac: self.set_progress(
                        f"Phase 2: Resolving {i+1}/{count} - {n}", f, "#2196F3"
                    ))
                    self.log(f"[{idx+1}/{count}] Resolving {part_name}...")

                    direct_url = self._resolve_single_link_pure_js(page, ff_link)

                    if direct_url:
                        self.resolved_links.append(direct_url)
                        self.log(f"  ✅ GOT DIRECT URL: {direct_url[:80]}...")
                        self.after(0, lambda u=direct_url: self._append_resolved(u))
                    else:
                        self.log(f"  ⚠️ Resolution timed out for {part_name}, skipping")

                browser.close()

            # ── Complete ──
            resolved_count = len(self.resolved_links)
            self.after(0, lambda: self._on_pipeline_complete(resolved_count, count))

        except Exception as e:
            self.log(f"Pipeline error: {e}")
            self.after(0, lambda: self.set_progress(f"Error: {e}", color="#FF5252"))
            self._finish()

    def _cancel_download(self, download):
        """Immediately cancel any browser download to avoid filling disk."""
        try:
            download.cancel()
            self.log("  [Browser file download cancelled]")
        except:
            pass

    def _launch_browser(self, p, headless=True):
        if headless:
            try:
                return p.chromium.launch(headless=True)
            except Exception:
                driver_exe, driver_env = compute_driver_executable()
                env = {**os.environ, **driver_env}
                subprocess.run(
                    [str(driver_exe), "install", "chromium"],
                    env=env, capture_output=True,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                )
                return p.chromium.launch(headless=True)
        else:
            channel = detect_browser_channel()
            return p.chromium.launch(
                headless=False,
                channel=channel,
                args=['--disable-blink-features=AutomationControlled']
            )

    def _resolve_single_link_pure_js(self, page, ff_url):
        """Navigate to fuckingfast link, wait for Turnstile token, and perform JS fetch (no file download!)."""
        direct_url = None

        def on_response(response):
            nonlocal direct_url
            if "/go" in response.url or "dl.fuckingfast.co" in response.url:
                headers = dict(response.headers)
                if "hx-redirect" in headers:
                    direct_url = headers["hx-redirect"]
                elif "location" in headers:
                    direct_url = headers["location"]

        page.on("response", on_response)

        try:
            page.goto(ff_url, wait_until="domcontentloaded")
            time.sleep(2)

            # 1. Wait for Turnstile token
            token = ""
            for i in range(12):
                if self.cancel_requested:
                    break
                try:
                    token = page.evaluate("() => window.turnstileToken || ''")
                    cleared = page.evaluate("() => window.dlCleared || false")
                    if token or cleared:
                        break
                except:
                    pass
                time.sleep(1)

            if not token:
                for frame in page.frames:
                    if "turnstile" in frame.url or "cloudflare" in frame.url:
                        try:
                            frame.click("body", timeout=1500)
                        except:
                            pass
                for i in range(8):
                    try:
                        token = page.evaluate("() => window.turnstileToken || ''")
                        if token:
                            break
                    except:
                        pass
                    time.sleep(1)

            # 2. Pure JS fetch for /go endpoint — NO page.click() so NO file download starts in browser!
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
            res = page.evaluate(js_script)
            if res:
                direct_url = res

        except Exception as e:
            self.log(f"  Error resolving: {e}")
        finally:
            page.remove_listener("response", on_response)

        return direct_url

    def _append_resolved(self, url):
        self.resolved_textbox.insert("end", f"{url}\n")
        self.resolved_textbox.see("end")

    def _on_pipeline_complete(self, resolved_count, total_count):
        self.set_progress(
            f"Successfully resolved {resolved_count}/{total_count} TRUE direct URLs!",
            1.0, "#4CAF50"
        )
        self.log(f"Pipeline complete! {resolved_count}/{total_count} direct dl.fuckingfast.co URLs generated.")

        if resolved_count > 0:
            self.copy_btn.configure(state="normal")
            text = "\n".join(self.resolved_links)
            pyperclip.copy(text)
            self.log("Direct URLs auto-copied to clipboard! Paste into JDownloader 2.")
            self.count_label.configure(
                text=f"✨ {resolved_count} direct URLs copied to clipboard!",
                text_color="#4CAF50"
            )

        self._finish()

    def _finish(self):
        self.is_running = False
        self.after(0, lambda: self.start_btn.configure(state="normal"))
        self.after(0, lambda: self.cancel_btn.configure(state="disabled"))

    def _copy_to_clipboard(self):
        if self.resolved_links:
            text = "\n".join(self.resolved_links)
            pyperclip.copy(text)
            self.count_label.configure(
                text=f"✨ {len(self.resolved_links)} direct URLs copied!",
                text_color="#4CAF50"
            )
            self.log("Copied all direct download URLs to clipboard.")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = LinkExtractorApp()
    app.mainloop()
