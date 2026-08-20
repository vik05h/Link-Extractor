import os
import sys
import io
import re
import json
import time
import asyncio
import threading
import multiprocessing
import tkinter as tk
from tkinter import filedialog, messagebox
import pyperclip
import customtkinter as ctk
from PIL import Image

# Ensure Playwright browser cache location
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "ms-playwright"
)

import theme_m3 as m3
import scraper
from engine import ResolutionEngine, ResolvedLink, detect_browser_channel
import validator
from history import HistoryManager
import integrations
import updater

# Global CustomTkinter appearance setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def get_asset_path(filename: str) -> str:
    """Helper to locate assets whether running from script or PyInstaller frozen bundle."""
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)


def load_settings() -> dict:
    """Load settings from local settings.json or return defaults."""
    default_settings = {
        "concurrency": 3,
        "auto_validate": True,
        "jd_port": 9666,
        "auto_push_jd": False
    }
    settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_settings.update(data)
        except Exception:
            pass
    return default_settings


def save_settings(settings: dict):
    """Save settings to local settings.json."""
    settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


class LinkExtractorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FitGirl Direct Link Extractor v3.1 — High Speed Multi-Tab Grabber")
        self.geometry("1140x800")
        self.minsize(940, 640)
        self.configure(fg_color=m3.BG_SURFACE)

        # Set App Window Icon if exists
        icon_path = get_asset_path("app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.settings = load_settings()
        self.history_mgr = HistoryManager()

        self.pastebin_links = []
        self.resolved_links = []
        self.last_game_title = "FitGirl Repack"
        self.last_validation_summary = None
        self.is_running = False
        self.cancel_event = None

        # Animation states
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_idx = 0
        self.is_animating = False

        self._load_icons()
        self._create_layout()
        self._show_screen("extractor")

    def _load_icons(self):
        """Load PIL images for CTkImage widgets."""
        try:
            p_app = get_asset_path("app_icon.png")
            p_ext = get_asset_path("icon_extract.png")
            p_copy = get_asset_path("icon_copy.png")
            p_can = get_asset_path("icon_cancel.png")

            self.img_brand = ctk.CTkImage(Image.open(p_app), size=(36, 36)) if os.path.exists(p_app) else None
            self.img_extract = ctk.CTkImage(Image.open(p_ext), size=(18, 18)) if os.path.exists(p_ext) else None
            self.img_copy = ctk.CTkImage(Image.open(p_copy), size=(18, 18)) if os.path.exists(p_copy) else None
            self.img_cancel = ctk.CTkImage(Image.open(p_can), size=(16, 16)) if os.path.exists(p_can) else None
        except Exception:
            self.img_brand = None
            self.img_extract = None
            self.img_copy = None
            self.img_cancel = None

    def _create_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── 1. Navigation Rail (Sidebar) ──
        self.nav_rail = ctk.CTkFrame(
            self,
            width=210,
            corner_radius=0,
            fg_color=m3.SURFACE_CONTAINER_LOW,
            border_width=1,
            border_color=m3.OUTLINE_VARIANT
        )
        self.nav_rail.grid(row=0, column=0, sticky="nsew")
        self.nav_rail.grid_propagate(False)

        # Brand header in nav rail
        brand_frame = ctk.CTkFrame(self.nav_rail, fg_color="transparent")
        brand_frame.pack(fill="x", padx=16, pady=(20, 24))

        if self.img_brand:
            ctk.CTkLabel(brand_frame, image=self.img_brand, text="").pack(side="left", padx=(0, 10))

        brand_text_box = ctk.CTkFrame(brand_frame, fg_color="transparent")
        brand_text_box.pack(side="left", fill="both")

        ctk.CTkLabel(
            brand_text_box,
            text="FitGirl Extractor",
            font=ctk.CTkFont(family=m3.FONT_DISPLAY, size=15, weight="bold"),
            text_color=m3.TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            brand_text_box,
            text="High Speed Edition",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=11),
            text_color=m3.PRIMARY
        ).pack(anchor="w")

        # Nav Items
        self.nav_buttons = {}
        nav_items = [
            ("extractor", "⚡  Extractor"),
            ("history", "📚  History & Archive"),
            ("settings", "⚙️  Settings & Tweaks")
        ]

        for screen_key, label in nav_items:
            btn = ctk.CTkButton(
                self.nav_rail,
                text=label,
                anchor="w",
                font=ctk.CTkFont(family=m3.FONT_TEXT, size=13, weight="bold"),
                height=42,
                corner_radius=m3.RADIUS_PILL,
                fg_color="transparent",
                text_color=m3.TEXT_SECONDARY,
                hover_color=m3.SURFACE_CONTAINER_HIGH,
                command=lambda k=screen_key: self._show_screen(k)
            )
            btn.pack(fill="x", padx=12, pady=4)
            self.nav_buttons[screen_key] = btn

        # Bottom info in rail
        rail_footer = ctk.CTkFrame(self.nav_rail, fg_color="transparent")
        rail_footer.pack(side="bottom", fill="x", padx=16, pady=20)

        ctk.CTkLabel(
            rail_footer,
            text="v3.1.0 • Pro Edition",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=11),
            text_color=m3.TEXT_MUTED
        ).pack(anchor="w")

        # ── 2. Screen Container ──
        self.screen_container = ctk.CTkFrame(self, fg_color=m3.BG_SURFACE)
        self.screen_container.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.screen_container.grid_columnconfigure(0, weight=1)
        self.screen_container.grid_rowconfigure(0, weight=1)

        # Build individual screens
        self.screens = {
            "extractor": self._build_extractor_screen(),
            "history": self._build_history_screen(),
            "settings": self._build_settings_screen()
        }

    def _show_screen(self, screen_name: str):
        """Switch active screen with smooth transition."""
        for name, frame in self.screens.items():
            if name == screen_name:
                frame.grid(row=0, column=0, sticky="nsew")
                self.nav_buttons[name].configure(
                    fg_color=m3.PRIMARY_CONTAINER,
                    text_color=m3.ON_PRIMARY_CONTAINER
                )
            else:
                frame.grid_forget()
                self.nav_buttons[name].configure(
                    fg_color="transparent",
                    text_color=m3.TEXT_SECONDARY
                )

        if screen_name == "history":
            self._refresh_history_list()

    # ── Smooth Animation Engine ──
    def animate_progress_to(self, target_frac: float, steps: int = 8, interval_ms: int = 15):
        """Smoothly interpolate progress bar to target fraction."""
        try:
            current = self.progress_bar.get()
            diff = target_frac - current
            if abs(diff) < 0.005:
                self.progress_bar.set(target_frac)
                return
            step_size = diff / steps
            for i in range(1, steps + 1):
                self.after(i * interval_ms, lambda v=current + step_size * i: self.progress_bar.set(min(1.0, max(0.0, v))))
        except Exception:
            self.progress_bar.set(target_frac)

    def _start_spinner(self):
        self.is_animating = True
        self._spin_loop()

    def _stop_spinner(self):
        self.is_animating = False

    def _spin_loop(self):
        if not self.is_animating:
            return
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_frames)
        self.after(120, self._spin_loop)

    # ═══════════════════════════════════════════════════════════════════
    # ── SCREEN 1: EXTRACTOR SCREEN ──
    # ═══════════════════════════════════════════════════════════════════
    def _build_extractor_screen(self) -> ctk.CTkFrame:
        screen = ctk.CTkFrame(self.screen_container, fg_color="transparent")
        screen.grid_columnconfigure(0, weight=1)
        screen.grid_rowconfigure(2, weight=1)

        # ── Header Banner Card ──
        header_card = ctk.CTkFrame(
            screen,
            corner_radius=m3.RADIUS_CARD,
            fg_color=m3.SURFACE_CONTAINER,
            border_width=1,
            border_color=m3.OUTLINE_VARIANT
        )
        header_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        header_layout = ctk.CTkFrame(header_card, fg_color="transparent")
        header_layout.pack(fill="x", padx=20, pady=14)

        title_row = ctk.CTkFrame(header_layout, fg_color="transparent")
        title_row.pack(fill="x")

        ctk.CTkLabel(
            title_row,
            text="FitGirl Direct Link Extractor",
            font=ctk.CTkFont(family=m3.FONT_DISPLAY, size=20, weight="bold"),
            text_color=m3.TEXT_PRIMARY
        ).pack(side="left", padx=(0, 10))

        self.chip_badge = ctk.CTkLabel(
            title_row,
            text="⚡ TURBO SPEED ENGINE",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=11, weight="bold"),
            fg_color=m3.PRIMARY_CONTAINER,
            text_color=m3.ON_PRIMARY_CONTAINER,
            corner_radius=m3.RADIUS_PILL,
            padx=10, pady=3
        )
        self.chip_badge.pack(side="left")

        ctk.CTkLabel(
            header_layout,
            text="Directly paste FitGirl Game Pages, Pastebin URLs, or FuckingFast links. Converts all parts to direct dl.fuckingfast.co URLs via concurrent tabs with auto-retry and JDownloader 2 push.",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=12),
            text_color=m3.TEXT_SECONDARY,
            wraplength=760,
            justify="left"
        ).pack(anchor="w", pady=(4, 0))

        # ── URL Input Card ──
        input_card = ctk.CTkFrame(
            screen,
            corner_radius=m3.RADIUS_CARD,
            fg_color=m3.SURFACE_CONTAINER,
            border_width=1,
            border_color=m3.OUTLINE_VARIANT
        )
        input_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        input_layout = ctk.CTkFrame(input_card, fg_color="transparent")
        input_layout.pack(fill="x", padx=20, pady=14)

        label_row = ctk.CTkFrame(input_layout, fg_color="transparent")
        label_row.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            label_row,
            text="FitGirl Game Page, Pastebin, or FuckingFast URL:",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=13, weight="bold"),
            text_color=m3.TEXT_PRIMARY
        ).pack(side="left")

        self.type_badge = ctk.CTkLabel(
            label_row,
            text="Auto-detecting URL",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=11, weight="bold"),
            fg_color=m3.SURFACE_CONTAINER_HIGHEST,
            text_color=m3.TEXT_TERTIARY,
            corner_radius=m3.RADIUS_PILL,
            padx=10, pady=2
        )
        self.type_badge.pack(side="right")

        # Entry Row
        entry_row = ctk.CTkFrame(input_layout, fg_color="transparent")
        entry_row.pack(fill="x")

        self.url_entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="e.g. https://fitgirl-repacks.site/black-myth-wukong/ OR pastebin / fuckingfast URL",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=13),
            height=44,
            border_color=m3.OUTLINE,
            fg_color=m3.SURFACE_CONTAINER_LOWEST,
            text_color=m3.TEXT_PRIMARY,
            corner_radius=m3.RADIUS_INPUT
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<KeyRelease>", self._on_url_changed)

        self.start_btn = ctk.CTkButton(
            entry_row,
            text=" Extract & Resolve",
            image=self.img_extract,
            compound="left",
            command=self._on_start,
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=13, weight="bold"),
            height=44, width=180,
            fg_color=m3.PRIMARY,
            text_color=m3.ON_PRIMARY,
            hover_color=m3.PRIMARY_HOVER,
            corner_radius=m3.RADIUS_BUTTON
        )
        self.start_btn.pack(side="right")

        # Progress Row
        self.progress_row = ctk.CTkFrame(input_layout, fg_color="transparent")
        self.progress_row.pack(fill="x", pady=(12, 0))

        self.status_badge = ctk.CTkLabel(
            self.progress_row,
            text="Ready",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=12, weight="bold"),
            fg_color=m3.TERTIARY_CONTAINER,
            text_color=m3.ON_TERTIARY_CONTAINER,
            corner_radius=m3.RADIUS_PILL,
            padx=12, pady=3
        )
        self.status_badge.pack(side="left", padx=(0, 12))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_row,
            height=10,
            border_width=0,
            progress_color=m3.PRIMARY,
            fg_color=m3.SURFACE_CONTAINER_HIGHEST,
            corner_radius=m3.RADIUS_PILL
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.progress_bar.set(0)

        self.cancel_btn = ctk.CTkButton(
            self.progress_row,
            text=" Cancel",
            image=self.img_cancel,
            compound="left",
            command=self._on_cancel,
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=12),
            height=32, width=90,
            fg_color=m3.SURFACE_CONTAINER_HIGHEST,
            text_color=m3.TEXT_SECONDARY,
            hover_color=m3.OUTLINE,
            corner_radius=m3.RADIUS_BUTTON,
            state="disabled"
        )
        self.cancel_btn.pack(side="right")

        # Live speed & ETA sub-bar
        self.stats_row = ctk.CTkFrame(input_layout, fg_color="transparent")
        self.stats_row.pack(fill="x", pady=(6, 0))

        self.stats_label = ctk.CTkLabel(
            self.stats_row,
            text=f"⚡ Worker Pool: {self.settings.get('concurrency', 3)} Tabs | 🔁 Auto-Retry: 2 Passes | 🔍 Validation: Enabled",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=11),
            text_color=m3.TEXT_TERTIARY
        )
        self.stats_label.pack(side="left")

        # ── Results & Segmented Tabs Card ──
        middle_card = ctk.CTkFrame(
            screen,
            corner_radius=m3.RADIUS_CARD,
            fg_color=m3.SURFACE_CONTAINER,
            border_width=1,
            border_color=m3.OUTLINE_VARIANT
        )
        middle_card.grid(row=2, column=0, sticky="nsew", pady=(0, 12))
        middle_card.grid_columnconfigure(0, weight=1)
        middle_card.grid_rowconfigure(1, weight=1)

        tabs_header = ctk.CTkFrame(middle_card, fg_color="transparent")
        tabs_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))

        self.view_selector = ctk.CTkSegmentedButton(
            tabs_header,
            values=["Direct URLs (0)", "Validation & Size (0 B)", "Activity Log"],
            command=self._on_view_changed,
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=12, weight="bold"),
            height=34,
            corner_radius=m3.RADIUS_PILL,
            fg_color=m3.SURFACE_CONTAINER_LOWEST,
            selected_color=m3.PRIMARY_CONTAINER,
            selected_hover_color=m3.PRIMARY_CONTAINER,
            unselected_color=m3.SURFACE_CONTAINER_LOWEST,
            unselected_hover_color=m3.SURFACE_CONTAINER_HIGH,
            text_color=m3.TEXT_PRIMARY
        )
        self.view_selector.set("Direct URLs (0)")
        self.view_selector.pack(side="left")

        # Views Container
        self.views_container = ctk.CTkFrame(middle_card, fg_color="transparent")
        self.views_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.views_container.grid_columnconfigure(0, weight=1)
        self.views_container.grid_rowconfigure(0, weight=1)

        # View 1: Direct URLs Textbox
        self.resolved_textbox = ctk.CTkTextbox(
            self.views_container,
            font=ctk.CTkFont(family=m3.FONT_MONO, size=12),
            wrap="none",
            fg_color=m3.SURFACE_CONTAINER_LOWEST,
            text_color=m3.ACCENT_BLUE,
            border_width=1,
            border_color=m3.OUTLINE_VARIANT,
            corner_radius=m3.RADIUS_INPUT
        )

        # View 2: Validation Details Textbox
        self.validation_textbox = ctk.CTkTextbox(
            self.views_container,
            font=ctk.CTkFont(family=m3.FONT_MONO, size=11),
            wrap="none",
            fg_color=m3.SURFACE_CONTAINER_LOWEST,
            text_color=m3.TEXT_SECONDARY,
            border_width=1,
            border_color=m3.OUTLINE_VARIANT,
            corner_radius=m3.RADIUS_INPUT
        )

        # View 3: Activity Log Textbox
        self.log_textbox = ctk.CTkTextbox(
            self.views_container,
            font=ctk.CTkFont(family=m3.FONT_MONO, size=11),
            wrap="word",
            fg_color=m3.SURFACE_CONTAINER_LOWEST,
            text_color=m3.TEXT_SECONDARY,
            border_width=1,
            border_color=m3.OUTLINE_VARIANT,
            corner_radius=m3.RADIUS_INPUT
        )

        self._on_view_changed("Direct URLs (0)")

        # ── Bottom Action Footer Bar ──
        bottom_card = ctk.CTkFrame(
            screen,
            corner_radius=m3.RADIUS_CARD,
            fg_color=m3.SURFACE_CONTAINER,
            border_width=1,
            border_color=m3.OUTLINE_VARIANT
        )
        bottom_card.grid(row=3, column=0, sticky="ew")

        bottom_layout = ctk.CTkFrame(bottom_card, fg_color="transparent")
        bottom_layout.pack(fill="x", padx=16, pady=10)

        self.count_label = ctk.CTkLabel(
            bottom_layout,
            text="Paste a link above and click 'Extract & Resolve'",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=13),
            text_color=m3.TEXT_TERTIARY
        )
        self.count_label.pack(side="left")

        actions_box = ctk.CTkFrame(bottom_layout, fg_color="transparent")
        actions_box.pack(side="right")

        self.push_jd_btn = ctk.CTkButton(
            actions_box,
            text="🚀 Push to JD2",
            command=self._push_to_jdownloader,
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=12, weight="bold"),
            height=36, width=130,
            fg_color=m3.TERTIARY,
            text_color=m3.ON_TERTIARY,
            hover_color=m3.TERTIARY_HOVER,
            corner_radius=m3.RADIUS_BUTTON
        )
        self.push_jd_btn.pack(side="left", padx=(0, 8))

        self.export_menu = ctk.CTkOptionMenu(
            actions_box,
            values=["📁 Export .txt", "📁 Export .json", "📁 Export .crawljob"],
            command=self._on_export_selected,
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=12),
            height=36, width=140,
            fg_color=m3.SURFACE_CONTAINER_HIGHEST,
            text_color=m3.TEXT_PRIMARY,
            button_color=m3.SURFACE_CONTAINER_HIGH,
            button_hover_color=m3.OUTLINE,
            corner_radius=m3.RADIUS_BUTTON
        )
        self.export_menu.set("📁 Export...")
        self.export_menu.pack(side="left", padx=(0, 8))

        self.copy_btn = ctk.CTkButton(
            actions_box,
            text=" Copy All",
            image=self.img_copy,
            compound="left",
            command=self._copy_to_clipboard,
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=12, weight="bold"),
            height=36, width=120,
            fg_color=m3.PRIMARY_CONTAINER,
            text_color=m3.ON_PRIMARY_CONTAINER,
            hover_color=m3.SECONDARY_CONTAINER,
            corner_radius=m3.RADIUS_BUTTON
        )
        self.copy_btn.pack(side="left")

        return screen

    def _on_view_changed(self, selected_val: str):
        """Switch between Direct URLs, Validation Breakdown, and Log."""
        self.resolved_textbox.grid_forget()
        self.validation_textbox.grid_forget()
        self.log_textbox.grid_forget()

        if "Direct URLs" in selected_val:
            self.resolved_textbox.grid(row=0, column=0, sticky="nsew")
        elif "Validation" in selected_val:
            self.validation_textbox.grid(row=0, column=0, sticky="nsew")
        else:
            self.log_textbox.grid(row=0, column=0, sticky="nsew")

    # ═══════════════════════════════════════════════════════════════════
    # ── SCREEN 2: HISTORY & ARCHIVE SCREEN ──
    # ═══════════════════════════════════════════════════════════════════
    def _build_history_screen(self) -> ctk.CTkFrame:
        screen = ctk.CTkFrame(self.screen_container, fg_color="transparent")
        screen.grid_columnconfigure(0, weight=1)
        screen.grid_rowconfigure(1, weight=1)

        # Header Bar with Search & Clear All
        header_card = ctk.CTkFrame(
            screen,
            corner_radius=m3.RADIUS_CARD,
            fg_color=m3.SURFACE_CONTAINER,
            border_width=1,
            border_color=m3.OUTLINE_VARIANT
        )
        header_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        header_layout = ctk.CTkFrame(header_card, fg_color="transparent")
        header_layout.pack(fill="x", padx=20, pady=14)

        ctk.CTkLabel(
            header_layout,
            text="Saved Game Extractions & Archive",
            font=ctk.CTkFont(family=m3.FONT_DISPLAY, size=18, weight="bold"),
            text_color=m3.TEXT_PRIMARY
        ).pack(side="left", padx=(0, 16))

        self.search_entry = ctk.CTkEntry(
            header_layout,
            placeholder_text="🔍 Search past games...",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=12),
            height=36, width=260,
            border_color=m3.OUTLINE,
            fg_color=m3.SURFACE_CONTAINER_LOWEST,
            text_color=m3.TEXT_PRIMARY,
            corner_radius=m3.RADIUS_INPUT
        )
        self.search_entry.pack(side="left", padx=(0, 12))
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_history_list())

        ctk.CTkButton(
            header_layout,
            text="🗑️ Clear All",
            command=self._clear_all_history,
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=12),
            height=36, width=100,
            fg_color=m3.ERROR_CONTAINER,
            text_color=m3.ERROR,
            hover_color=m3.ON_ERROR,
            corner_radius=m3.RADIUS_BUTTON
        ).pack(side="right")

        # Scrollable History List
        self.history_scroll = ctk.CTkScrollableFrame(
            screen,
            corner_radius=m3.RADIUS_CARD,
            fg_color=m3.SURFACE_CONTAINER_LOW,
            border_width=1,
            border_color=m3.OUTLINE_VARIANT
        )
        self.history_scroll.grid(row=1, column=0, sticky="nsew")
        self.history_scroll.grid_columnconfigure(0, weight=1)

        return screen

    def _refresh_history_list(self):
        """Fetch and render history cards from SQLite database."""
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        query = self.search_entry.get().strip() if hasattr(self, "search_entry") else ""
        records = self.history_mgr.get_records(query)

        if not records:
            empty_box = ctk.CTkFrame(self.history_scroll, fg_color="transparent")
            empty_box.pack(expand=True, pady=60)
            ctk.CTkLabel(
                empty_box,
                text="📚 No extraction records found.",
                font=ctk.CTkFont(family=m3.FONT_DISPLAY, size=15, weight="bold"),
                text_color=m3.TEXT_TERTIARY
            ).pack()
            ctk.CTkLabel(
                empty_box,
                text="Resolved game links will automatically appear here.",
                font=ctk.CTkFont(family=m3.FONT_TEXT, size=12),
                text_color=m3.TEXT_MUTED
            ).pack(pady=(4, 0))
            return

        for rec in records:
            card = ctk.CTkFrame(
                self.history_scroll,
                corner_radius=m3.RADIUS_CARD,
                fg_color=m3.SURFACE_CONTAINER,
                border_width=1,
                border_color=m3.OUTLINE_VARIANT
            )
            card.pack(fill="x", padx=12, pady=6)

            card_layout = ctk.CTkFrame(card, fg_color="transparent")
            card_layout.pack(fill="x", padx=16, pady=12)

            info_box = ctk.CTkFrame(card_layout, fg_color="transparent")
            info_box.pack(side="left", fill="both", expand=True)

            ctk.CTkLabel(
                info_box,
                text=rec["title"],
                font=ctk.CTkFont(family=m3.FONT_DISPLAY, size=14, weight="bold"),
                text_color=m3.TEXT_PRIMARY
            ).pack(anchor="w")

            meta_text = f"📅 {rec['timestamp']}  •  📦 {rec['resolved_count']}/{rec['total_parts']} Parts  •  💾 {rec['total_size_str']}"
            ctk.CTkLabel(
                info_box,
                text=meta_text,
                font=ctk.CTkFont(family=m3.FONT_TEXT, size=11),
                text_color=m3.PRIMARY
            ).pack(anchor="w", pady=(2, 0))

            btn_box = ctk.CTkFrame(card_layout, fg_color="transparent")
            btn_box.pack(side="right")

            urls = rec.get("urls", [])

            ctk.CTkButton(
                btn_box,
                text="📋 Copy",
                width=70, height=32,
                font=ctk.CTkFont(family=m3.FONT_TEXT, size=11, weight="bold"),
                fg_color=m3.PRIMARY_CONTAINER,
                text_color=m3.ON_PRIMARY_CONTAINER,
                hover_color=m3.SECONDARY_CONTAINER,
                corner_radius=m3.RADIUS_BUTTON,
                command=lambda u=urls: self._copy_specific_urls(u)
            ).pack(side="left", padx=4)

            ctk.CTkButton(
                btn_box,
                text="🚀 Push JD2",
                width=85, height=32,
                font=ctk.CTkFont(family=m3.FONT_TEXT, size=11, weight="bold"),
                fg_color=m3.TERTIARY,
                text_color=m3.ON_TERTIARY,
                hover_color=m3.TERTIARY_HOVER,
                corner_radius=m3.RADIUS_BUTTON,
                command=lambda u=urls, t=rec["title"]: self._push_specific_urls(u, t)
            ).pack(side="left", padx=4)

            ctk.CTkButton(
                btn_box,
                text="🗑️",
                width=36, height=32,
                font=ctk.CTkFont(family=m3.FONT_TEXT, size=12),
                fg_color=m3.SURFACE_CONTAINER_HIGHEST,
                text_color=m3.ERROR,
                hover_color=m3.ERROR_CONTAINER,
                corner_radius=m3.RADIUS_BUTTON,
                command=lambda r_id=rec["id"]: self._delete_history_record(r_id)
            ).pack(side="left", padx=4)

    def _copy_specific_urls(self, urls: list):
        if urls:
            pyperclip.copy("\n".join(urls))
            messagebox.showinfo("Copied", f"Copied {len(urls)} direct URLs to clipboard!")

    def _push_specific_urls(self, urls: list, title: str):
        if urls:
            port = self.settings.get("jd_port", 9666)
            success, msg = integrations.push_to_jdownloader(urls, package_name=title, port=port)
            if success:
                messagebox.showinfo("JDownloader 2", msg)
            else:
                messagebox.showwarning("JDownloader 2", msg)

    def _delete_history_record(self, record_id: int):
        self.history_mgr.delete_record(record_id)
        self._refresh_history_list()

    def _clear_all_history(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to delete all saved extractions?"):
            self.history_mgr.clear_history()
            self._refresh_history_list()

    # ═══════════════════════════════════════════════════════════════════
    # ── SCREEN 3: SETTINGS & TWEAKS SCREEN ──
    # ═══════════════════════════════════════════════════════════════════
    def _build_settings_screen(self) -> ctk.CTkFrame:
        screen = ctk.CTkFrame(self.screen_container, fg_color="transparent")
        screen.grid_columnconfigure(0, weight=1)

        header_card = ctk.CTkFrame(
            screen,
            corner_radius=m3.RADIUS_CARD,
            fg_color=m3.SURFACE_CONTAINER,
            border_width=1,
            border_color=m3.OUTLINE_VARIANT
        )
        header_card.pack(fill="x", pady=(0, 16))

        header_layout = ctk.CTkFrame(header_card, fg_color="transparent")
        header_layout.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(
            header_layout,
            text="Engine & Integration Preferences",
            font=ctk.CTkFont(family=m3.FONT_DISPLAY, size=18, weight="bold"),
            text_color=m3.TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_layout,
            text="Configure browser worker pool parallelism, link validation, and JDownloader 2 port settings.",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=12),
            text_color=m3.TEXT_SECONDARY
        ).pack(anchor="w", pady=(2, 0))

        # Settings Options Card
        card = ctk.CTkFrame(
            screen,
            corner_radius=m3.RADIUS_CARD,
            fg_color=m3.SURFACE_CONTAINER,
            border_width=1,
            border_color=m3.OUTLINE_VARIANT
        )
        card.pack(fill="x", pady=(0, 16))

        card_layout = ctk.CTkFrame(card, fg_color="transparent")
        card_layout.pack(fill="x", padx=24, pady=20)

        # 1. Concurrency Slider
        concur_row = ctk.CTkFrame(card_layout, fg_color="transparent")
        concur_row.pack(fill="x", pady=10)

        concur_info = ctk.CTkFrame(concur_row, fg_color="transparent")
        concur_info.pack(side="left", fill="both")

        ctk.CTkLabel(
            concur_info,
            text="Worker Tab Concurrency (Parallel Resolution):",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=13, weight="bold"),
            text_color=m3.TEXT_PRIMARY
        ).pack(anchor="w")

        self.concur_val_label = ctk.CTkLabel(
            concur_info,
            text=f"{self.settings.get('concurrency', 3)} Parallel Tabs (Recommended: 3–4)",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=11),
            text_color=m3.PRIMARY
        )
        self.concur_val_label.pack(anchor="w")

        self.concur_slider = ctk.CTkSlider(
            concur_row,
            from_=1, to=6, number_of_steps=5,
            command=self._on_concurrency_changed,
            width=180,
            progress_color=m3.PRIMARY,
            button_color=m3.PRIMARY,
            button_hover_color=m3.PRIMARY_HOVER
        )
        self.concur_slider.set(self.settings.get("concurrency", 3))
        self.concur_slider.pack(side="right")

        # 2. Auto-Validate Links Switch
        val_row = ctk.CTkFrame(card_layout, fg_color="transparent")
        val_row.pack(fill="x", pady=12)

        val_info = ctk.CTkFrame(val_row, fg_color="transparent")
        val_info.pack(side="left", fill="both")

        ctk.CTkLabel(
            val_info,
            text="Auto-Validate Links & Calculate Repack Size:",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=13, weight="bold"),
            text_color=m3.TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            val_info,
            text="Runs rapid 1-byte Range checks to compute total download size and verify live filenames.",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=11),
            text_color=m3.TEXT_TERTIARY
        ).pack(anchor="w")

        self.val_switch = ctk.CTkSwitch(
            val_row,
            text="",
            command=self._save_current_settings,
            progress_color=m3.PRIMARY,
            button_color=m3.ON_PRIMARY,
            button_hover_color=m3.PRIMARY_HOVER
        )
        if self.settings.get("auto_validate", True):
            self.val_switch.select()
        self.val_switch.pack(side="right")

        # 3. JDownloader 2 Port Entry
        jd_row = ctk.CTkFrame(card_layout, fg_color="transparent")
        jd_row.pack(fill="x", pady=12)

        jd_info = ctk.CTkFrame(jd_row, fg_color="transparent")
        jd_info.pack(side="left", fill="both")

        ctk.CTkLabel(
            jd_info,
            text="JDownloader 2 Local CNL Port:",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=13, weight="bold"),
            text_color=m3.TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            jd_info,
            text="Default port for JDownloader 2 Click'n'Load / FlashGot web API is 9666.",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=11),
            text_color=m3.TEXT_TERTIARY
        ).pack(anchor="w")

        # 4. Check for Updates
        update_row = ctk.CTkFrame(card_layout, fg_color="transparent")
        update_row.pack(fill="x", pady=12)

        update_info = ctk.CTkFrame(update_row, fg_color="transparent")
        update_info.pack(side="left", fill="both")

        ctk.CTkLabel(
            update_info,
            text=f"Application Version & Updates ({updater.CURRENT_VERSION}):",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=13, weight="bold"),
            text_color=m3.TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            update_info,
            text="Check GitHub Releases for the latest patches and binaries.",
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=11),
            text_color=m3.TEXT_TERTIARY
        ).pack(anchor="w")

        ctk.CTkButton(
            update_row,
            text="🔄 Check Updates",
            command=self._check_for_updates,
            width=130, height=36,
            font=ctk.CTkFont(family=m3.FONT_TEXT, size=12, weight="bold"),
            fg_color=m3.PRIMARY_CONTAINER,
            text_color=m3.ON_PRIMARY_CONTAINER,
            hover_color=m3.SECONDARY_CONTAINER,
            corner_radius=m3.RADIUS_BUTTON
        ).pack(side="right")

        return screen

    def _check_for_updates(self):
        has_update, release_info, msg = updater.check_for_updates()
        if has_update and release_info:
            if messagebox.askyesno(
                "Update Available",
                f"New Version {release_info['latest_version']} is available!\n\n"
                f"Release: {release_info['name']}\n\n"
                f"Would you like to open the download page now?"
            ):
                updater.open_release_page(release_info["download_url"])
        else:
            messagebox.showinfo("Check for Updates", f"You are running the latest version ({updater.CURRENT_VERSION}).\n\nNo updates available.")

    def _on_concurrency_changed(self, value):
        val = int(round(value))
        self.concur_val_label.configure(text=f"{val} Parallel Tabs (Recommended: 3–4)")
        self._save_current_settings()

    def _save_current_settings(self):
        try:
            port = int(self.jd_port_entry.get().strip())
        except Exception:
            port = 9666

        self.settings = {
            "concurrency": int(round(self.concur_slider.get())),
            "auto_validate": bool(self.val_switch.get()),
            "jd_port": port,
            "auto_push_jd": self.settings.get("auto_push_jd", False)
        }
        save_settings(self.settings)

    # ═══════════════════════════════════════════════════════════════════
    # ── LOGIC & PIPELINE ENGINE ──
    # ═══════════════════════════════════════════════════════════════════
    def _on_url_changed(self, event=None):
        raw = self.url_entry.get().strip()
        url_type = scraper.detect_url_type(raw)
        if url_type == "fitgirl_game_page":
            self.type_badge.configure(text="🎮 Game Page Detected", fg_color=m3.PRIMARY_CONTAINER, text_color=m3.ON_PRIMARY_CONTAINER)
        elif url_type == "fitgirl_pastebin":
            self.type_badge.configure(text="📋 Pastebin Detected", fg_color=m3.SECONDARY_CONTAINER, text_color=m3.ON_SECONDARY_CONTAINER)
        elif url_type in ("fuckingfast_direct", "raw_links"):
            self.type_badge.configure(text="⚡ Direct FuckingFast Links", fg_color=m3.TERTIARY_CONTAINER, text_color=m3.ON_TERTIARY_CONTAINER)
        else:
            self.type_badge.configure(text="Auto-detecting URL", fg_color=m3.SURFACE_CONTAINER_HIGHEST, text_color=m3.TEXT_TERTIARY)

    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log_textbox.insert("end", f"[{ts}] {msg}\n")
        self.log_textbox.see("end")

    def set_status(self, text: str, fraction: float = None, badge_color: str = None, text_color: str = None):
        self.status_badge.configure(
            text=text,
            fg_color=badge_color or m3.PRIMARY_CONTAINER,
            text_color=text_color or m3.ON_PRIMARY_CONTAINER
        )
        if fraction is not None:
            self.animate_progress_to(fraction)

    def _on_start(self):
        url = self.url_entry.get().strip()
        if not url:
            self.set_status("Enter a valid URL", badge_color=m3.ERROR_CONTAINER, text_color=m3.ERROR)
            return

        self.is_running = True
        self.cancel_event = threading.Event()
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.resolved_textbox.delete("1.0", "end")
        self.validation_textbox.delete("1.0", "end")
        self.resolved_links = []
        self.pastebin_links = []
        self.last_game_title = "FitGirl Repack"
        self._start_spinner()

        threading.Thread(target=self._run_pipeline, args=(url,), daemon=True).start()

    def _on_cancel(self):
        if self.cancel_event:
            self.cancel_event.set()
        self.log("🛑 Cancellation requested by user.")

    def _run_pipeline(self, input_url: str):
        t_pipeline_start = time.time()
        try:
            url_type = scraper.detect_url_type(input_url)
            self.log(f"Detected input type: {url_type}")

            concurrency = self.settings.get("concurrency", 3)

            # Link resolution must run in visible browser mode to pass Cloudflare Turnstile
            engine = ResolutionEngine(concurrency=concurrency, max_retries=2, headless=False)
            channel = detect_browser_channel()
            if not channel:
                self.log("ERROR: No Chrome or Edge browser detected on system.")
                self.after(0, lambda: self.set_status("No Browser Found", badge_color=m3.ERROR_CONTAINER, text_color=m3.ERROR))
                self._finish()
                return

            self.log(f"Using system browser engine: {channel}")

            # Phase 1: URL & Pastebin Resolution
            if url_type in ("fuckingfast_direct", "raw_links"):
                raw_urls = re.findall(r'https?://[^\s,]+', input_url)
                self.pastebin_links = [u for u in raw_urls if "fuckingfast.co" in u]
                if not self.pastebin_links:
                    self.pastebin_links = [input_url]
                self.last_game_title = "FuckingFast Direct Parts"
                self.log(f"Phase 1: Parsed {len(self.pastebin_links)} direct fuckingfast link(s)")

            elif url_type == "fitgirl_game_page":
                self.after(0, lambda: self.set_status("Scraping Game Page", 0.05, badge_color=m3.PRIMARY_CONTAINER))
                self.log(f"Phase 1: Fetching FitGirl game page: {input_url}")

                pastebins, game_title = scraper.extract_game_page_pastebins(input_url)
                self.last_game_title = game_title or "FitGirl Repack"
                self.log(f"Game Repack: {self.last_game_title}")

                ff_pastebins = [p for p in pastebins if p["hoster"] == "FuckingFast"]
                if not ff_pastebins and pastebins:
                    ff_pastebins = [pastebins[0]]

                if not ff_pastebins:
                    self.log("ERROR: No pastebin mirrors found on game page.")
                    self.after(0, lambda: self.set_status("No Mirrors Found", badge_color=m3.ERROR_CONTAINER, text_color=m3.ERROR))
                    self._finish()
                    return

                target_pastebin = ff_pastebins[0]["url"]
                self.log(f"Found FuckingFast pastebin: {target_pastebin}")
                self.after(0, lambda: self.set_status("Decrypting Pastebin", 0.1, badge_color=m3.SECONDARY_CONTAINER))

                self.pastebin_links = asyncio.run(
                    engine.fetch_pastebin_links(target_pastebin, log_cb=self.log)
                )

            else:  # fitgirl_pastebin
                self.after(0, lambda: self.set_status("Decrypting Pastebin", 0.08, badge_color=m3.SECONDARY_CONTAINER))
                self.pastebin_links = asyncio.run(
                    engine.fetch_pastebin_links(input_url, log_cb=self.log)
                )
                self.last_game_title = "FitGirl Pastebin Download"

            total_links = len(self.pastebin_links)
            self.log(f"Phase 1 complete: extracted {total_links} game parts")

            if total_links == 0:
                self.after(0, lambda: self.set_status("No Links Found", badge_color=m3.ERROR_CONTAINER, text_color=m3.ERROR))
                self._finish()
                return

            # Phase 2: High-Speed Multi-Tab Resolution
            self.after(0, lambda: self.set_status(f"Resolving 0/{total_links}", 0.15, badge_color=m3.PRIMARY_CONTAINER))

            def on_progress(done_count, total_count, avg_speed, eta, active_tabs, part_name, direct_url, status):
                frac = 0.15 + (0.75 * done_count / max(1, total_count))
                eta_str = f"{int(eta)}s" if eta < 60 else f"{int(eta // 60)}m {int(eta % 60)}s"
                status_text = f"Resolving {done_count}/{total_count}"
                stats_text = f"⚡ Speed: {avg_speed:.1f}s/part | ⏱️ ETA: ~{eta_str} | 🌐 {active_tabs} tabs active"

                self.after(0, lambda: self.set_status(status_text, frac, badge_color=m3.PRIMARY_CONTAINER))
                self.after(0, lambda: self.stats_label.configure(text=stats_text))

                if direct_url and status == "resolved":
                    self.after(0, lambda: self._append_resolved(direct_url, done_count, total_count))

            def on_retry_pass(failed_count, current_attempt, max_attempts):
                self.after(0, lambda: self.set_status(
                    f"Retrying {failed_count} links (Pass {current_attempt}/{max_attempts})",
                    badge_color=m3.WARNING_CONTAINER,
                    text_color=m3.WARNING
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

            total_elapsed = time.time() - t_pipeline_start
            resolved_urls = [r.direct_url for r in results if r.direct_url]
            self.resolved_links = resolved_urls

            # Optional: Link Validation & Exact Size Calculation via 1-byte Range checks
            total_size_str = "0 B"
            total_size_bytes = 0

            if self.settings.get("auto_validate", True) and resolved_urls and not (self.cancel_event and self.cancel_event.is_set()):
                self.after(0, lambda: self.set_status("Validating Links & Size", 0.92, badge_color=m3.TERTIARY_CONTAINER, text_color=m3.ON_TERTIARY_CONTAINER))
                self.log(f"Phase 3: Validating {len(resolved_urls)} direct URLs & computing exact download sizes...")

                val_summary = validator.validate_links(
                    resolved_urls,
                    max_workers=15,
                    cancel_event=self.cancel_event
                )
                self.last_validation_summary = val_summary
                total_size_str = val_summary.total_size_str
                total_size_bytes = val_summary.total_bytes

                self.log(f"Validation Complete: {val_summary.valid_count}/{val_summary.total_links} verified | Total Size: {total_size_str}")
                self.after(0, lambda: self._render_validation_view(val_summary))

            # Save to SQLite History ONLY if not cancelled
            is_cancelled = bool(self.cancel_event and self.cancel_event.is_set())
            if resolved_urls and not is_cancelled:
                self.history_mgr.add_record(
                    title=self.last_game_title,
                    source_url=input_url,
                    total_parts=total_links,
                    resolved_count=len(resolved_urls),
                    total_size_bytes=total_size_bytes,
                    total_size_str=total_size_str,
                    urls=resolved_urls
                )

            self.after(0, lambda: self._on_pipeline_complete(len(resolved_urls), total_links, total_elapsed, total_size_str))

        except Exception as e:
            self.log(f"Pipeline error: {e}")
            self.after(0, lambda: self.set_status("Error Occurred", badge_color=m3.ERROR_CONTAINER, text_color=m3.ERROR))
            self._finish()

    def _append_resolved(self, direct_url: str, done_count: int, total_count: int):
        self.resolved_textbox.insert("end", f"{direct_url}\n")
        self.resolved_textbox.see("end")

        self.view_selector.configure(values=[
            f"Direct URLs ({done_count}/{total_count})",
            "Validation & Size",
            "Activity Log"
        ])
        self.count_label.configure(
            text=f"✨ {done_count}/{total_count} direct URLs resolved",
            text_color=m3.ACCENT_BLUE
        )
        try:
            with open("resolved_direct_urls.txt", "a", encoding="utf-8") as f:
                f.write(f"{direct_url}\n")
        except Exception:
            pass

    def _render_validation_view(self, val_summary: validator.ValidationSummary):
        self.validation_textbox.delete("1.0", "end")
        self.validation_textbox.insert("end", f"=== REPACK DOWNLOAD VALIDATION SUMMARY ===\n")
        self.validation_textbox.insert("end", f"Game: {self.last_game_title}\n")
        self.validation_textbox.insert("end", f"Total Repack Size: {val_summary.total_size_str}\n")
        self.validation_textbox.insert("end", f"Active Verified Links: {val_summary.valid_count}/{val_summary.total_links}\n")
        self.validation_textbox.insert("end", f"{'='*60}\n\n")

        for item in val_summary.links:
            status_symbol = "✅" if item.is_valid else "❌"
            self.validation_textbox.insert("end", f"{status_symbol} [{item.content_length_str:>10}]  {item.filename}\n")

        self.view_selector.configure(values=[
            f"Direct URLs ({len(self.resolved_links)})",
            f"Validation & Size ({val_summary.total_size_str})",
            "Activity Log"
        ])

    def _on_pipeline_complete(self, resolved_count: int, total_count: int, total_elapsed: float, total_size_str: str):
        self._stop_spinner()
        avg_s = total_elapsed / resolved_count if resolved_count > 0 else 0
        self.set_status(f"Complete ({avg_s:.1f}s/part)", 1.0, badge_color=m3.TERTIARY_CONTAINER, text_color=m3.ON_TERTIARY_CONTAINER)
        self.stats_label.configure(
            text=f"🚀 Completed in {total_elapsed:.1f}s | Avg Speed: {avg_s:.1f}s/part | Total Size: {total_size_str} | Success: {resolved_count}/{total_count}"
        )

        if resolved_count > 0:
            text = "\n".join(self.resolved_links)
            pyperclip.copy(text)
            self.log(f"All {resolved_count} direct URLs saved & copied to clipboard!")
            self.count_label.configure(
                text=f"✨ All {resolved_count} direct URLs copied to clipboard & saved! ({total_size_str})",
                text_color=m3.TERTIARY
            )
            try:
                with open("resolved_direct_urls.txt", "w", encoding="utf-8") as f:
                    f.write(text + "\n")
            except Exception:
                pass

        self._finish()

    def _finish(self):
        self._stop_spinner()
        self.is_running = False
        self.after(0, lambda: self.start_btn.configure(state="normal"))
        self.after(0, lambda: self.cancel_btn.configure(state="disabled"))

    def _copy_to_clipboard(self):
        if self.resolved_links:
            text = "\n".join(self.resolved_links)
            pyperclip.copy(text)
            self.count_label.configure(
                text=f"✨ {len(self.resolved_links)} direct URLs copied to clipboard!",
                text_color=m3.TERTIARY
            )
            self.log(f"Copied {len(self.resolved_links)} direct download URLs to clipboard.")

    def _push_to_jdownloader(self):
        if not self.resolved_links:
            messagebox.showinfo("JDownloader 2", "No resolved links to push.")
            return

        port = self.settings.get("jd_port", 9666)
        success, msg = integrations.push_to_jdownloader(
            self.resolved_links,
            package_name=self.last_game_title,
            source_url=self.url_entry.get().strip(),
            port=port
        )
        if success:
            self.log(f"🚀 {msg}")
            messagebox.showinfo("JDownloader 2 Push", msg)
        else:
            self.log(f"⚠️ {msg}")
            messagebox.showwarning("JDownloader 2 Connection", msg)

    def _on_export_selected(self, choice: str):
        if not self.resolved_links:
            messagebox.showinfo("Export", "No resolved links to export.")
            self.export_menu.set("📁 Export...")
            return

        safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', self.last_game_title).strip('_')

        if "crawljob" in choice:
            fp = filedialog.asksaveasfilename(
                defaultextension=".crawljob",
                filetypes=[("JDownloader CrawlJob", "*.crawljob")],
                initialfile=f"{safe_title}.crawljob"
            )
            if fp:
                integrations.export_crawljob(fp, self.resolved_links, package_name=self.last_game_title)
                self.log(f"Exported .crawljob to: {fp}")

        elif "json" in choice:
            fp = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON File", "*.json")],
                initialfile=f"{safe_title}.json"
            )
            if fp:
                size_str = self.last_validation_summary.total_size_str if self.last_validation_summary else ""
                integrations.export_json(fp, self.last_game_title, self.url_entry.get().strip(), self.resolved_links, size_str)
                self.log(f"Exported JSON to: {fp}")

        elif "txt" in choice:
            fp = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text File", "*.txt")],
                initialfile=f"{safe_title}_direct_urls.txt"
            )
            if fp:
                integrations.export_text(fp, self.resolved_links)
                self.log(f"Exported TXT to: {fp}")

        self.export_menu.set("📁 Export...")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = LinkExtractorApp()
    app.mainloop()
