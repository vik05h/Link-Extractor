import os
import sys
import io
import re
import time
import asyncio
import threading
import multiprocessing
import pyperclip
import customtkinter as ctk
from PIL import Image

# Ensure Playwright browser cache location
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "ms-playwright"
)

import scraper
from engine import ResolutionEngine, ResolvedLink, detect_browser_channel

# Appearance setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def get_asset_path(filename: str) -> str:
    """Helper to locate assets whether running from script or PyInstaller frozen bundle."""
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)


class LinkExtractorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FitGirl Direct Link Extractor v3.0 — High Speed Multi-Tab Grabber")
        self.geometry("1080x780")
        self.minsize(880, 620)

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
        self.cancel_event = None

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
        except Exception:
            self.img_brand = None
            self.img_extract = None
            self.img_copy = None
            self.img_cancel = None

    def _create_ui(self):
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
            text="v3.0 SPEED BOOST",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#0284C7",
            text_color="#FFFFFF",
            corner_radius=6,
            padx=8, pady=2
        )
        badge.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="Directly paste FitGirl Game Pages, Pastebin URLs, or FuckingFast links.\nConverts all game parts to TRUE direct download links (dl.fuckingfast.co) via 3x concurrent browser tabs with auto-retry.",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8",
            wraplength=780,
            justify="left"
        ).pack(anchor="w", pady=(4, 0))

        # ── 2. URL Input Card ──
        input_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#1E293B", border_width=1, border_color="#334155")
        input_card.grid(row=1, column=0, sticky="ew", padx=20, pady=10)

        input_layout = ctk.CTkFrame(input_card, fg_color="transparent")
        input_layout.pack(fill="x", padx=20, pady=15)

        # Label Row with detected type badge
        label_row = ctk.CTkFrame(input_layout, fg_color="transparent")
        label_row.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            label_row,
            text="FitGirl Game URL, Pastebin, or FuckingFast URL:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#E2E8F0"
        ).pack(side="left")

        self.type_badge = ctk.CTkLabel(
            label_row,
            text="Auto-detecting URL",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#334155",
            text_color="#94A3B8",
            corner_radius=6,
            padx=8, pady=1
        )
        self.type_badge.pack(side="right")

        # Entry Row
        entry_row = ctk.CTkFrame(input_layout, fg_color="transparent")
        entry_row.pack(fill="x")

        self.url_entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="e.g. https://fitgirl-repacks.site/black-myth-wukong/ OR pastebin / fuckingfast URL",
            font=ctk.CTkFont(size=13),
            height=42,
            border_color="#475569",
            fg_color="#0F172A"
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.url_entry.bind("<KeyRelease>", self._on_url_changed)

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

        # Progress & Live Stats Row
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

        # Live speed & ETA sub-bar
        self.stats_row = ctk.CTkFrame(input_layout, fg_color="transparent")
        self.stats_row.pack(fill="x", pady=(6, 0))

        self.stats_label = ctk.CTkLabel(
            self.stats_row,
            text="⚡ Concurrency: 3 Parallel Tabs | 🔁 Auto-Retry: Enabled (2 Passes)",
            font=ctk.CTkFont(size=11),
            text_color="#64748B"
        )
        self.stats_label.pack(side="left")

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
            height=36, width=250,
            fg_color="#059669", hover_color="#047857",
            corner_radius=8
        )
        self.copy_btn.pack(side="right")

    # ── Real-time URL Detection ──
    def _on_url_changed(self, event=None):
        raw = self.url_entry.get().strip()
        url_type = scraper.detect_url_type(raw)
        if url_type == "fitgirl_game_page":
            self.type_badge.configure(text="🎮 Game Page Detected", fg_color="#6366F1", text_color="#FFFFFF")
        elif url_type == "fitgirl_pastebin":
            self.type_badge.configure(text="📋 Pastebin Detected", fg_color="#0284C7", text_color="#FFFFFF")
        elif url_type in ("fuckingfast_direct", "raw_links"):
            self.type_badge.configure(text="⚡ Direct FuckingFast Links", fg_color="#10B981", text_color="#FFFFFF")
        else:
            self.type_badge.configure(text="Auto-detecting URL", fg_color="#334155", text_color="#94A3B8")

    # ── Logging & Status UI Updates ──
    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log_textbox.insert("end", f"[{ts}] {msg}\n")
        self.log_textbox.see("end")

    def set_status(self, text: str, fraction: float = None, badge_color: str = "#10B981"):
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
        self.cancel_event = threading.Event()
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.resolved_textbox.delete("1.0", "end")
        self.resolved_links = []
        self.pastebin_links = []

        threading.Thread(target=self._run_pipeline, args=(url,), daemon=True).start()

    def _on_cancel(self):
        if self.cancel_event:
            self.cancel_event.set()
        self.log("🛑 Cancellation requested by user.")

    # ── Execution Pipeline ──
    def _run_pipeline(self, input_url: str):
        t_pipeline_start = time.time()
        try:
            url_type = scraper.detect_url_type(input_url)
            self.log(f"Detected input type: {url_type}")

            engine = ResolutionEngine(concurrency=3, max_retries=2)
            channel = detect_browser_channel()
            if not channel:
                self.log("ERROR: No Chrome or Edge browser detected on system.")
                self.after(0, lambda: self.set_status("No Browser Found", badge_color="#EF4444"))
                self._finish()
                return

            self.log(f"Using system browser engine: {channel}")

            # Phase 1: URL & Pastebin Resolution
            if url_type in ("fuckingfast_direct", "raw_links"):
                raw_urls = re.findall(r'https?://[^\s,]+', input_url)
                self.pastebin_links = [u for u in raw_urls if "fuckingfast.co" in u]
                if not self.pastebin_links:
                    self.pastebin_links = [input_url]
                self.log(f"Phase 1: Parsed {len(self.pastebin_links)} direct fuckingfast link(s)")

            elif url_type == "fitgirl_game_page":
                self.after(0, lambda: self.set_status("Scraping Game Page", 0.05, badge_color="#6366F1"))
                self.log(f"Phase 1: Fetching FitGirl game page: {input_url}")

                pastebins = scraper.extract_game_page_pastebins(input_url)
                ff_pastebins = [p for p in pastebins if p["hoster"] == "FuckingFast"]

                if not ff_pastebins:
                    self.log(f"Warning: No explicit 'FuckingFast' mirror found. Found: {[p['hoster'] for p in pastebins]}")
                    if pastebins:
                        ff_pastebins = [pastebins[0]]

                if not ff_pastebins:
                    self.log("ERROR: No pastebin mirrors found on game page.")
                    self.after(0, lambda: self.set_status("No Mirrors Found", badge_color="#EF4444"))
                    self._finish()
                    return

                target_pastebin = ff_pastebins[0]["url"]
                self.log(f"Found FuckingFast pastebin: {target_pastebin}")
                self.after(0, lambda: self.set_status("Decrypting Pastebin", 0.1, badge_color="#F59E0B"))

                self.pastebin_links = asyncio.run(
                    engine.fetch_pastebin_links(target_pastebin, log_cb=self.log)
                )

            else:  # fitgirl_pastebin or other pastebin
                self.after(0, lambda: self.set_status("Decrypting Pastebin", 0.08, badge_color="#F59E0B"))
                self.pastebin_links = asyncio.run(
                    engine.fetch_pastebin_links(input_url, log_cb=self.log)
                )

            total_links = len(self.pastebin_links)
            self.log(f"Phase 1 complete: extracted {total_links} game parts")

            if total_links == 0:
                self.after(0, lambda: self.set_status("No Links Found", badge_color="#EF4444"))
                self._finish()
                return

            # Phase 2: High-Speed Multi-Tab Resolution
            self.after(0, lambda: self.set_status(f"Resolving 0/{total_links}", 0.15, badge_color="#0284C7"))

            def on_progress(done_count, total_count, avg_speed, eta, active_tabs, part_name, direct_url, status):
                frac = 0.15 + (0.80 * done_count / max(1, total_count))
                eta_str = f"{int(eta)}s" if eta < 60 else f"{int(eta // 60)}m {int(eta % 60)}s"
                status_text = f"Resolving {done_count}/{total_count}"
                stats_text = f"⚡ Speed: {avg_speed:.1f}s/part | ⏱️ ETA: ~{eta_str} | 🌐 {active_tabs} tabs active"

                self.after(0, lambda: self.set_status(status_text, frac, badge_color="#0284C7"))
                self.after(0, lambda: self.stats_label.configure(text=stats_text))

                if direct_url and status == "resolved":
                    self.after(0, lambda: self._append_resolved(direct_url, done_count, total_count))

            def on_retry_pass(failed_count, current_attempt, max_attempts):
                self.after(0, lambda: self.set_status(
                    f"Retrying {failed_count} links (Pass {current_attempt}/{max_attempts})",
                    badge_color="#F59E0B"
                ))

            # Run engine
            results: list[ResolvedLink] = asyncio.run(
                engine.resolve_all_async(
                    urls=self.pastebin_links,
                    on_progress=on_progress,
                    on_log=self.log,
                    on_retry_pass=on_retry_pass,
                    cancel_event=self.cancel_event
                )
            )

            # Process completion
            total_elapsed = time.time() - t_pipeline_start
            resolved_urls = [r.direct_url for r in results if r.direct_url]
            self.resolved_links = resolved_urls

            self.after(0, lambda: self._on_pipeline_complete(len(resolved_urls), total_links, total_elapsed))

        except Exception as e:
            self.log(f"Pipeline error: {e}")
            self.after(0, lambda: self.set_status("Error Occurred", badge_color="#EF4444"))
            self._finish()

    def _append_resolved(self, direct_url: str, done_count: int, total_count: int):
        self.resolved_textbox.insert("end", f"{direct_url}\n")
        self.resolved_textbox.see("end")

        # Update tab label
        self.tabview.set("Direct Download URLs (0)")  # preserve focus
        # Find tab button and update text if possible or update count label
        self.count_label.configure(
            text=f"✨ {done_count}/{total_count} direct URLs resolved",
            text_color="#38BDF8"
        )
        try:
            with open("resolved_direct_urls.txt", "a", encoding="utf-8") as f:
                f.write(f"{direct_url}\n")
        except Exception:
            pass

    def _on_pipeline_complete(self, resolved_count: int, total_count: int, total_elapsed: float):
        avg_s = total_elapsed / resolved_count if resolved_count > 0 else 0
        self.set_status(f"Complete ({avg_s:.1f}s/part)", 1.0, badge_color="#10B981")
        self.stats_label.configure(
            text=f"🚀 Completed in {total_elapsed:.1f}s | Avg Speed: {avg_s:.1f}s/part | Success: {resolved_count}/{total_count}"
        )

        if resolved_count > 0:
            text = "\n".join(self.resolved_links)
            pyperclip.copy(text)
            self.log(f"All {resolved_count} direct URLs saved to resolved_direct_urls.txt & copied to clipboard!")
            self.count_label.configure(
                text=f"✨ All {resolved_count} direct URLs copied to clipboard & saved!",
                text_color="#10B981"
            )
            # Rewrite clean file
            try:
                with open("resolved_direct_urls.txt", "w", encoding="utf-8") as f:
                    f.write(text + "\n")
            except Exception:
                pass

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
