import os
import sys
import io
import re
import time
import subprocess
import threading
import multiprocessing
import pyperclip
import customtkinter as ctk
from PIL import Image

# Force Playwright to use the user's global browser cache
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "ms-playwright"
)

from playwright.sync_api import sync_playwright
from playwright._impl._driver import compute_driver_executable

# Appearance setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def get_asset_path(filename):
    """Helper to locate assets whether running from script or PyInstaller frozen bundle."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)


def detect_browser_channel():
    """Detect installed browser (Edge or Chrome)."""
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

        self.title("FitGirl Link Extractor - High Speed Direct Link Grabber")
        self.geometry("1050x750")
        self.minsize(850, 600)

        # Set App Window Icon if exists
        icon_path = get_asset_path("app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.pastebin_links = []
        self.resolved_links = []
        self.is_running = False
        self.cancel_requested = False

        self._load_icons()
        self._create_ui()

    def _load_icons(self):
        """Load PIL images for CTkImage widgets."""
        try:
            p_app = get_asset_path("app_icon.png")
            p_ext = get_asset_path("icon_extract.png")
            p_copy = get_asset_path("icon_copy.png")
            p_can = get_asset_path("icon_cancel.png")

            self.img_brand = ctk.CTkImage(Image.open(p_app), size=(42, 42)) if os.path.exists(p_app) else None
            self.img_extract = ctk.CTkImage(Image.open(p_ext), size=(18, 18)) if os.path.exists(p_ext) else None
            self.img_copy = ctk.CTkImage(Image.open(p_copy), size=(18, 18)) if os.path.exists(p_copy) else None
            self.img_cancel = ctk.CTkImage(Image.open(p_can), size=(16, 16)) if os.path.exists(p_can) else None
        except Exception as e:
            self.img_brand = None
            self.img_extract = None
            self.img_copy = None
            self.img_cancel = None

    def _create_ui(self):
        # Main Outer Container Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── 1. Top Header Banner ──
        header_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#1E293B", border_width=1, border_color="#334155")
        header_card.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

        header_layout = ctk.CTkFrame(header_card, fg_color="transparent")
        header_layout.pack(fill="x", padx=20, pady=15)

        if self.img_brand:
            brand_icon_label = ctk.CTkLabel(header_layout, image=self.img_brand, text="")
            brand_icon_label.pack(side="left", padx=(0, 15))

        title_box = ctk.CTkFrame(header_layout, fg_color="transparent")
        title_box.pack(side="left", fill="both", expand=True)

        title_row = ctk.CTkFrame(title_box, fg_color="transparent")
        title_row.pack(anchor="w")

        ctk.CTkLabel(
            title_row,
            text="FitGirl Direct Link Extractor",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left", padx=(0, 10))

        badge = ctk.CTkLabel(
            title_row,
            text="v2.5.1 HOTFIX",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#0284C7",
            text_color="#FFFFFF",
            corner_radius=6,
            padx=8, pady=2
        )
        badge.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="Paste a FitGirl pastebin or fuckingfast URL. Converts all parts to TRUE direct download links (dl.fuckingfast.co) at max speed.\nPatch: Fixed Playwright driver initialization crash & added direct host link parsing support.",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8",
            wraplength=750,
            justify="left"
        ).pack(anchor="w", pady=(4, 0))

        # ── 2. URL Input Card ──
        input_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#1E293B", border_width=1, border_color="#334155")
        input_card.grid(row=1, column=0, sticky="ew", padx=20, pady=10)

        input_layout = ctk.CTkFrame(input_card, fg_color="transparent")
        input_layout.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            input_layout,
            text="Pastebin or FuckingFast URL:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#E2E8F0"
        ).pack(anchor="w", pady=(0, 8))

        entry_row = ctk.CTkFrame(input_layout, fg_color="transparent")
        entry_row.pack(fill="x")

        self.url_entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="e.g. https://paste.fitgirl-repacks.site/?b9f42622ad62a88b#GvhWmbUo...",
            font=ctk.CTkFont(size=13),
            height=42,
            border_color="#475569",
            fg_color="#0F172A"
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.start_btn = ctk.CTkButton(
            entry_row,
            text=" Extract & Resolve All",
            image=self.img_extract,
            compound="left",
            command=self._on_start,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=42, width=190,
            fg_color="#0284C7", hover_color="#0369A1",
            corner_radius=8
        )
        self.start_btn.pack(side="right")

        # Progress Row inside input card
        self.progress_row = ctk.CTkFrame(input_layout, fg_color="transparent")
        self.progress_row.pack(fill="x", pady=(12, 0))

        self.status_badge = ctk.CTkLabel(
            self.progress_row,
            text="Ready",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#10B981",
            text_color="#FFFFFF",
            corner_radius=6,
            padx=10, pady=3
        )
        self.status_badge.pack(side="left", padx=(0, 12))

        self.progress_bar = ctk.CTkProgressBar(self.progress_row, height=10, border_width=0, progress_color="#0284C7")
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.progress_bar.set(0)

        self.cancel_btn = ctk.CTkButton(
            self.progress_row,
            text=" Cancel",
            image=self.img_cancel,
            compound="left",
            command=self._on_cancel,
            font=ctk.CTkFont(size=12),
            height=30, width=90,
            fg_color="#475569", hover_color="#334155",
            corner_radius=6,
            state="disabled"
        )
        self.cancel_btn.pack(side="right")

        # ── 3. Main Results Display Tabs ──
        middle_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#1E293B", border_width=1, border_color="#334155")
        middle_card.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)

        self.tabview = ctk.CTkTabview(middle_card, fg_color="transparent")
        self.tabview.pack(fill="both", expand=True, padx=12, pady=8)

        self.tab_resolved = self.tabview.add("Direct Download URLs (0)")
        self.tab_log = self.tabview.add("Activity Log")

        self.resolved_textbox = ctk.CTkTextbox(
            self.tab_resolved,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none",
            fg_color="#0F172A",
            text_color="#38BDF8",
            border_width=1,
            border_color="#334155"
        )
        self.resolved_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_textbox = ctk.CTkTextbox(
            self.tab_log,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
            fg_color="#0F172A",
            text_color="#CBD5E1",
            border_width=1,
            border_color="#334155"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        # ── 4. Bottom Action Footer Bar ──
        bottom_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#1E293B", border_width=1, border_color="#334155")
        bottom_card.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 20))

        bottom_layout = ctk.CTkFrame(bottom_card, fg_color="transparent")
        bottom_layout.pack(fill="x", padx=20, pady=12)

        self.count_label = ctk.CTkLabel(
            bottom_layout,
            text="Paste a link above and click 'Extract & Resolve All'",
            font=ctk.CTkFont(size=13),
            text_color="#94A3B8"
        )
        self.count_label.pack(side="left")

        self.open_file_btn = ctk.CTkButton(
            bottom_layout,
            text="📁 Open Saved File",
            command=self._open_saved_file,
            font=ctk.CTkFont(size=12),
            height=36, width=140,
            fg_color="#334155", hover_color="#475569"
        )
        self.open_file_btn.pack(side="right", padx=(10, 0))

        self.copy_btn = ctk.CTkButton(
            bottom_layout,
            text=" Copy Resolved URLs to Clipboard",
            image=self.img_copy,
            compound="left",
            command=self._copy_to_clipboard,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36, width=240,
            fg_color="#059669", hover_color="#047857",
            corner_radius=8
        )
        self.copy_btn.pack(side="right")

    # ── Logging & Status UI Updates ──
    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log_textbox.insert("end", f"[{ts}] {msg}\n")
        self.log_textbox.see("end")

    def set_status(self, text, fraction=None, badge_color="#10B981"):
        self.status_badge.configure(text=text, fg_color=badge_color)
        if fraction is not None:
            self.progress_bar.set(fraction)

    # ── Start / Cancel Control ──
    def _on_start(self):
        url = self.url_entry.get().strip()
        if not url:
            self.set_status("Enter a valid URL", badge_color="#EF4444")
            return

        self.is_running = True
        self.cancel_requested = False
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.resolved_textbox.delete("1.0", "end")
        self.resolved_links = []
        self.pastebin_links = []

        threading.Thread(target=self._run_full_pipeline, args=(url,), daemon=True).start()

    def _on_cancel(self):
        self.cancel_requested = True
        self.log("Cancellation requested by user.")

    # ── Pipeline Engine ──
    def _run_full_pipeline(self, pastebin_url):
        t_pipeline_start = time.time()
        try:
            # Check if user passed direct fuckingfast link(s) directly
            if "fuckingfast.co" in pastebin_url:
                self.log(f"Phase 1: Detected direct fuckingfast URL input")
                raw_urls = re.findall(r'https?://[^\s,]+', pastebin_url)
                self.pastebin_links = [u for u in raw_urls if "fuckingfast.co" in u]
                if not self.pastebin_links:
                    self.pastebin_links = [pastebin_url]
            else:
                # Phase 1: Extract links from pastebin page
                self.after(0, lambda: self.set_status("Phase 1: Fetching Pastebin", 0.05, badge_color="#F59E0B"))
                self.log(f"Phase 1: Fetching pastebin: {pastebin_url}")

                with sync_playwright() as p:
                    browser = self._launch_browser(p, headless=True)
                    page = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                    ).new_page()

                    page.goto(pastebin_url, wait_until="networkidle")
                    time.sleep(1.5)

                    for a in page.query_selector_all("a"):
                        href = a.get_attribute("href")
                        if href and "fuckingfast.co" in href:
                            if href not in self.pastebin_links:
                                self.pastebin_links.append(href)

                    browser.close()

            count = len(self.pastebin_links)
            self.log(f"Phase 1 complete: found {count} links")
            if count == 0:
                self.after(0, lambda: self.set_status("No links found", badge_color="#EF4444"))
                self._finish()
                return

            # Phase 2: Ultra Fast JS resolution via real browser
            self.after(0, lambda: self.set_status(f"Resolving 0/{count}", 0.1, badge_color="#0284C7"))
            self.log(f"Phase 2: Resolving {count} links (high speed 100ms polling mode)")

            channel = detect_browser_channel()
            if not channel:
                self.log("ERROR: No Chrome or Edge browser found.")
                self.after(0, lambda: self.set_status("No Browser Found", badge_color="#EF4444"))
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
                context.on("page", lambda pop: pop.close() if pop != context.pages[0] else None)

                page = context.new_page()
                page.on("download", lambda dl: self._cancel_download(dl))

                for idx, ff_link in enumerate(self.pastebin_links):
                    if self.cancel_requested:
                        break

                    part_name = ff_link.split("#")[-1] if "#" in ff_link else ff_link.split("/")[-1]
                    frac = 0.1 + (0.85 * (idx + 1) / count)
                    self.after(0, lambda i=idx, f=frac: self.set_status(f"Resolving {i+1}/{count}", f, badge_color="#0284C7"))

                    t0 = time.time()
                    direct_url = self._resolve_single_link_ultra_fast(page, ff_link)
                    elapsed = time.time() - t0

                    if direct_url:
                        self.resolved_links.append(direct_url)
                        self.log(f"[{idx+1}/{count}] ⚡ Resolved {part_name} in {elapsed:.1f}s -> {direct_url[:65]}...")
                        self.after(0, lambda u=direct_url: self._append_resolved(u))
                    else:
                        self.log(f"[{idx+1}/{count}] ⚠️ Could not resolve {part_name}, skipping")

                browser.close()

            # Complete
            total_elapsed = time.time() - t_pipeline_start
            resolved_count = len(self.resolved_links)
            self.after(0, lambda: self._on_pipeline_complete(resolved_count, count, total_elapsed))

        except Exception as e:
            self.log(f"Pipeline error: {e}")
            self.after(0, lambda: self.set_status("Error Occurred", badge_color="#EF4444"))
            self._finish()

    def _cancel_download(self, download):
        try:
            download.cancel()
        except:
            pass

    def _launch_browser(self, p, headless=True):
        if headless:
            try:
                return p.chromium.launch(headless=True)
            except Exception:
                try:
                    res = compute_driver_executable()
                    if isinstance(res, tuple) and len(res) == 2:
                        driver_exe, driver_cli = res
                        subprocess.run(
                            [str(driver_exe), str(driver_cli), "install", "chromium"],
                            capture_output=True,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                        )
                except Exception as ex:
                    self.log(f"Driver check warning: {ex}")
                # Fallback to system chrome or edge if headless chromium launch fails
                channel = detect_browser_channel()
                return p.chromium.launch(headless=True, channel=channel)
        else:
            channel = detect_browser_channel()
            return p.chromium.launch(
                headless=False,
                channel=channel,
                args=['--disable-blink-features=AutomationControlled']
            )

    def _resolve_single_link_ultra_fast(self, page, ff_url):
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

            token = ""
            for _ in range(60):
                if self.cancel_requested:
                    break
                try:
                    token = page.evaluate("() => window.turnstileToken || ''")
                    cleared = page.evaluate("() => window.dlCleared || false")
                    if token or cleared:
                        break
                except:
                    pass
                time.sleep(0.1)

            if not token:
                for frame in page.frames:
                    if "turnstile" in frame.url or "cloudflare" in frame.url:
                        try:
                            frame.click("body", timeout=1000)
                        except:
                            pass
                for _ in range(30):
                    try:
                        token = page.evaluate("() => window.turnstileToken || ''")
                        if token:
                            break
                    except:
                        pass
                    time.sleep(0.1)

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
            self.log(f"  Resolution error: {e}")
        finally:
            page.remove_listener("response", on_response)

        return direct_url

    def _append_resolved(self, url):
        self.resolved_textbox.insert("end", f"{url}\n")
        self.resolved_textbox.see("end")
        count = len(self.resolved_links)
        total = len(self.pastebin_links)
        self.count_label.configure(
            text=f"✨ {count}/{total} direct URLs resolved",
            text_color="#38BDF8"
        )
        try:
            with open("resolved_direct_urls.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(self.resolved_links))
        except:
            pass

    def _on_pipeline_complete(self, resolved_count, total_count, total_elapsed):
        avg_s = total_elapsed / resolved_count if resolved_count > 0 else 0
        self.set_status(f"Complete ({avg_s:.1f}s/link)", 1.0, badge_color="#10B981")
        self.log(f"🚀 Speed Pipeline Complete! {resolved_count}/{total_count} direct URLs in {total_elapsed:.1f}s ({avg_s:.1f}s per link).")

        if resolved_count > 0:
            text = "\n".join(self.resolved_links)
            pyperclip.copy(text)
            self.log("All direct URLs auto-copied to clipboard! Saved to resolved_direct_urls.txt")
            self.count_label.configure(
                text=f"✨ All {resolved_count} direct URLs copied to clipboard & saved!",
                text_color="#10B981"
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
                text=f"✨ {len(self.resolved_links)} direct URLs copied to clipboard!",
                text_color="#10B981"
            )
            self.log(f"Copied {len(self.resolved_links)} direct download URLs to clipboard.")

    def _open_saved_file(self):
        filename = "resolved_direct_urls.txt"
        if os.path.exists(filename):
            os.startfile(filename)
        else:
            self.log("No saved file exists yet.")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = LinkExtractorApp()
    app.mainloop()
