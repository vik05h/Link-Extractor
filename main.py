import os
import sys
import re
import json
import time
import asyncio
import threading
import pyperclip
import flet as ft

# Ensure Playwright browser cache location
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "ms-playwright"
)

import scraper
from engine import ResolutionEngine, ResolvedLink, detect_browser_channel
import validator
from history import HistoryManager
import integrations
import updater

THEME_PRESETS = {
    "Deep Violet": "#6750A4",
    "Emerald": "#10B981",
    "Sapphire": "#0284C7",
    "Amber": "#F59E0B",
    "Rose": "#F43F5E"
}

LOGO_PRESETS = {
    "Minimalist Cyber Link": "assets/logo_minimal.png",
    "Retro Arcade Cartridge": "assets/logo_arcade.png"
}

ANIMATION_PRESETS = {
    "Fast Subtle Fade": {
        "transition": ft.AnimatedSwitcherTransition.FADE,
        "duration": 300,
        "reverse_duration": 220,
        "curve_in": ft.AnimationCurve.EASE_IN_OUT,
        "curve_out": ft.AnimationCurve.EASE_IN_OUT
    },
    "Instant (Snappy)": {
        "transition": ft.AnimatedSwitcherTransition.FADE,
        "duration": 0,
        "reverse_duration": 0,
        "curve_in": ft.AnimationCurve.LINEAR,
        "curve_out": ft.AnimationCurve.LINEAR
    }
}


def get_app_data_dir() -> str:
    """Get persistent user data directory for settings and history database."""
    if getattr(sys, 'frozen', False):
        app_data = os.environ.get('APPDATA')
        if app_data:
            dir_path = os.path.join(app_data, 'FitGirlLinkExtractor')
            os.makedirs(dir_path, exist_ok=True)
            return dir_path
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path: str) -> str:
    """Get absolute path to bundled resource (works in dev and PyInstaller single-file)."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path.replace("/", os.sep))


def get_export_dir() -> str:
    """Get user-friendly export directory (Downloads folder or app folder) dynamically across all OSes and drives."""
    # 1. Cross-platform home directory detection via os.path.expanduser('~')
    home_dir = os.path.expanduser("~")
    downloads = os.path.join(home_dir, "Downloads")
    if os.path.exists(downloads):
        return downloads

    # 2. Check Windows USERPROFILE environment variable if custom drive
    user_profile = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    if user_profile:
        dl = os.path.join(user_profile, "Downloads")
        if os.path.exists(dl):
            return dl
        return user_profile

    # 3. Fallback to application directory
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def open_folder_cross_platform(folder_path: str):
    """Open folder in native file manager on Windows (Explorer), macOS (Finder), or Linux."""
    try:
        if sys.platform == "win32":
            os.startfile(folder_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder_path], check=False)
        else:
            subprocess.run(["xdg-open", folder_path], check=False)
    except Exception:
        pass


def load_settings() -> dict:
    default_settings = {
        "concurrency": 3,
        "auto_validate": True,
        "jd_port": 9666,
        "theme_seed": "Deep Violet",
        "theme_mode": "Dark",
        "logo_style": "Minimalist Cyber Link",
        "animation_style": "Fast Subtle Fade",
        "headless": False
    }
    settings_file = os.path.join(get_app_data_dir(), "settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_settings.update(data)
        except Exception:
            pass
    return default_settings


def save_settings(settings: dict):
    settings_file = os.path.join(get_app_data_dir(), "settings.json")
    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


def apply_windows_native_icon(ico_path="app_icon.ico"):
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    abs_ico = os.path.join(base_dir, ico_path)
    if not os.path.exists(abs_ico):
        abs_ico = os.path.abspath(ico_path)
    if not os.path.exists(abs_ico):
        return

    WM_SETICON = 0x0080
    ICON_SMALL = 0
    ICON_BIG = 1
    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x00000010
    LR_DEFAULTSIZE = 0x00000040
    GCLP_HICON = -14
    GCLP_HICONSM = -34

    try:
        user32 = ctypes.windll.user32
        h_icon = user32.LoadImageW(None, abs_ico, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
        if not h_icon:
            return

        def _apply_loop():
            for _ in range(12):
                time.sleep(0.3)
                found = []

                @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                def enum_cb(hwnd, lparam):
                    if user32.IsWindowVisible(hwnd):
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buf = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buf, length + 1)
                            if "fitgirl direct link extractor" in buf.value.lower():
                                found.append(hwnd)
                    return True

                user32.EnumWindows(enum_cb, 0)
                for hwnd in found:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon)
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon)
                    try:
                        if hasattr(user32, 'SetClassLongPtrW'):
                            user32.SetClassLongPtrW(hwnd, GCLP_HICON, h_icon)
                            user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, h_icon)
                        else:
                            user32.SetClassLongW(hwnd, GCLP_HICON, h_icon)
                            user32.SetClassLongW(hwnd, GCLP_HICONSM, h_icon)
                    except Exception:
                        pass
                if found:
                    break

        threading.Thread(target=_apply_loop, daemon=True).start()
    except Exception:
        pass


def main(page: ft.Page):
    apply_windows_native_icon("app_icon.ico")

    page.title = f"FitGirl Direct Link Extractor {updater.CURRENT_VERSION} — Flutter High Speed Edition"
    page.window.width = 1180
    page.window.height = 840
    page.window.min_width = 960
    page.window.min_height = 680
    page.padding = 0

    settings = load_settings()
    history_mgr = HistoryManager()

    mode_val = settings.get("theme_mode", "Dark")
    if mode_val == "Light":
        page.theme_mode = ft.ThemeMode.LIGHT
    elif mode_val == "System":
        page.theme_mode = ft.ThemeMode.SYSTEM
    else:
        page.theme_mode = ft.ThemeMode.DARK

    seed_name = settings.get("theme_seed", "Deep Violet")
    seed_color = THEME_PRESETS.get(seed_name, "#6750A4")
    page.theme = ft.Theme(color_scheme_seed=seed_color)

    active_logo_name = settings.get("logo_style", "Minimalist Cyber Link")
    active_logo_rel = LOGO_PRESETS.get(active_logo_name, "assets/logo_minimal.png")
    abs_logo_path = get_resource_path(active_logo_rel)
    page.window.icon = abs_logo_path

    rail_logo = ft.Image(src=abs_logo_path, width=38, height=38, border_radius=8, fit=ft.BoxFit.CONTAIN)
    banner_logo = ft.Image(src=abs_logo_path, width=30, height=30, border_radius=6, fit=ft.BoxFit.CONTAIN)

    # Runtime state
    state = {
        "is_running": False,
        "cancel_event": None,
        "pastebin_links": [],
        "resolved_links": [],
        "last_game_title": "FitGirl Repack",
        "last_val_summary": None,
        "active_screen": 0
    }

    # ── SnackBar Helper ──
    def show_snack(text: str, success: bool = True):
        snack = ft.SnackBar(
            content=ft.Text(text, weight=ft.FontWeight.W_500),
            bgcolor=ft.Colors.GREEN_800 if success else ft.Colors.RED_800,
            duration=3500,
            open=True
        )
        page.overlay.append(snack)
        page.update()

    # ── Update Checker Dialog ──
    def show_update_dialog(e=None):
        has_update, release_info, msg = updater.check_for_updates()
        if has_update and release_info:
            dlg = ft.AlertDialog(
                title=ft.Row([
                    ft.Icon(ft.Icons.SYSTEM_UPDATE, color=ft.Colors.AMBER_400),
                    ft.Text(f"Update Available: {release_info['latest_version']}", weight=ft.FontWeight.BOLD)
                ]),
                content=ft.Column([
                    ft.Text(f"Release: {release_info['name']}", weight=ft.FontWeight.W_600),
                    ft.Divider(),
                    ft.Text("Changelog & Highlights:", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Container(
                        content=ft.Text(release_info["body"], size=12),
                        padding=10,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        border_radius=8,
                        height=160
                    )
                ], tight=True, width=480),
                actions=[
                    ft.TextButton("Later", on_click=lambda _: page.pop_dialog()),
                    ft.FilledButton(
                        "Download Update",
                        icon=ft.Icons.DOWNLOAD,
                        on_click=lambda _: (updater.open_release_page(release_info["download_url"]), page.pop_dialog())
                    )
                ]
            )
            page.show_dialog(dlg)
        else:
            dlg = ft.AlertDialog(
                title=ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400),
                    ft.Text("You're Up to Date!", weight=ft.FontWeight.BOLD)
                ]),
                content=ft.Text(f"You are running the latest version ({updater.CURRENT_VERSION}).\nNo new updates found on GitHub."),
                actions=[ft.FilledButton("OK", on_click=lambda _: page.pop_dialog())]
            )
            page.show_dialog(dlg)

    # ═══════════════════════════════════════════════════════════════════
    # ── SCREEN 1: EXTRACTOR SCREEN ──
    # ═══════════════════════════════════════════════════════════════════
    url_input = ft.TextField(
        hint_text="e.g. https://fitgirl-repacks.site/black-myth-wukong/ OR pastebin / fuckingfast URL",
        prefix_icon=ft.Icons.LINK,
        expand=True,
        dense=True,
        border_radius=10,
        content_padding=12
    )

    url_badge_text = ft.Text("Auto-detecting URL", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT)
    url_badge_icon = ft.Icon(ft.Icons.AUTORENEW, size=14, color=ft.Colors.ON_SURFACE_VARIANT)
    url_badge = ft.Container(
        content=ft.Row([
            url_badge_icon,
            url_badge_text
        ], spacing=6, tight=True),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6)
    )

    def on_url_changed(e):
        raw_val = (url_input.value or "").strip()
        url_type = scraper.detect_url_type(raw_val)
        if url_type == "fitgirl_game_page":
            url_badge_text.value = "🎮 Game Page Detected"
            url_badge_text.color = ft.Colors.GREEN_400
            url_badge_icon.name = ft.Icons.SPORTS_ESPORTS
            url_badge_icon.color = ft.Colors.GREEN_400
            url_badge.bgcolor = ft.Colors.with_opacity(0.18, ft.Colors.GREEN_400)
            url_badge.border = ft.Border.all(1, ft.Colors.with_opacity(0.6, ft.Colors.GREEN_400))
        elif url_type == "fitgirl_pastebin":
            url_badge_text.value = "📋 Pastebin Detected"
            url_badge_text.color = ft.Colors.AMBER_400
            url_badge_icon.name = ft.Icons.CONTENT_PASTE
            url_badge_icon.color = ft.Colors.AMBER_400
            url_badge.bgcolor = ft.Colors.with_opacity(0.18, ft.Colors.AMBER_400)
            url_badge.border = ft.Border.all(1, ft.Colors.with_opacity(0.6, ft.Colors.AMBER_400))
        elif url_type in ("fuckingfast_direct", "raw_links"):
            url_badge_text.value = "⚡ Direct FuckingFast Links"
            url_badge_text.color = ft.Colors.CYAN_400
            url_badge_icon.name = ft.Icons.FLASH_ON
            url_badge_icon.color = ft.Colors.CYAN_400
            url_badge.bgcolor = ft.Colors.with_opacity(0.18, ft.Colors.CYAN_400)
            url_badge.border = ft.Border.all(1, ft.Colors.with_opacity(0.6, ft.Colors.CYAN_400))
        else:
            url_badge_text.value = "Auto-detecting URL"
            url_badge_text.color = ft.Colors.ON_SURFACE_VARIANT
            url_badge_icon.name = ft.Icons.AUTORENEW
            url_badge_icon.color = ft.Colors.ON_SURFACE_VARIANT
            url_badge.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGH
            url_badge.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        try:
            url_badge.update()
        except Exception:
            page.update()

    url_input.on_change = on_url_changed

    start_btn = ft.FilledButton("Extract & Resolve", icon=ft.Icons.ROCKET_LAUNCH, height=44)
    cancel_btn = ft.OutlinedButton("Cancel", icon=ft.Icons.CANCEL, height=44, disabled=True)

    status_chip_text = ft.Text("Ready", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT)
    status_chip_icon = ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=14, color=ft.Colors.ON_SURFACE_VARIANT)
    status_chip = ft.Container(
        content=ft.Row([
            status_chip_icon,
            status_chip_text
        ], spacing=6, tight=True),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6)
    )

    def set_status(text: str, icon=ft.Icons.CHECK_CIRCLE_OUTLINE, color=None):
        status_chip_text.value = text
        if icon:
            status_chip_icon.name = icon
        if color:
            status_chip_text.color = color
            status_chip_icon.color = color
            status_chip.bgcolor = ft.Colors.with_opacity(0.18, color)
            status_chip.border = ft.Border.all(1, ft.Colors.with_opacity(0.6, color))
        else:
            status_chip_text.color = ft.Colors.ON_SURFACE_VARIANT
            status_chip_icon.color = ft.Colors.ON_SURFACE_VARIANT
            status_chip.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGH
            status_chip.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        try:
            status_chip.update()
        except Exception:
            page.update()

    progress_bar = ft.ProgressBar(value=0, expand=True, border_radius=6)
    stats_text = ft.Text(
        f"⚡ Worker Pool: {settings.get('concurrency', 3)} Tabs | 🔁 Auto-Retry: 2 Passes | 🔍 Validation: {'Enabled' if settings.get('auto_validate', True) else 'Disabled'}",
        size=11, color=ft.Colors.ON_SURFACE_VARIANT
    )

    def update_stats_display():
        if not state["is_running"]:
            c = settings.get("concurrency", 3)
            v = "Enabled" if settings.get("auto_validate", True) else "Disabled"
            stats_text.value = f"⚡ Worker Pool: {c} Tabs | 🔁 Auto-Retry: 2 Passes | 🔍 Validation: {v}"
            try:
                stats_text.update()
            except Exception:
                pass

    # ── Interactive DataTable for Resolved Links ──
    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("#", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Part Filename", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Size", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Action", weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
        heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGH,
        border_radius=8,
        column_spacing=24
    )

    table_scroll = ft.ListView(
        controls=[data_table],
        expand=True,
        spacing=0,
        padding=0
    )

    # Validation breakdown text
    val_text = ft.Text("No validation data yet. Run an extraction with auto-validate enabled.", size=12, font_family="Consolas")
    val_container = ft.ListView(controls=[val_text], expand=True, padding=12)

    # Log text
    log_column = ft.ListView(
        controls=[ft.Text("[Ready] Waiting for extraction input...", size=11, font_family="Consolas", color=ft.Colors.ON_SURFACE_VARIANT)],
        expand=True,
        auto_scroll=True,
        padding=10
    )

    def log(msg: str):
        ts = time.strftime("%H:%M:%S")
        log_column.controls.append(ft.Text(f"[{ts}] {msg}", size=11, font_family="Consolas", color=ft.Colors.ON_SURFACE_VARIANT))
        try:
            if results_view_container.content == log_column:
                log_column.update()
            else:
                page.update()
        except Exception:
            try:
                page.update()
            except Exception:
                pass

    # Material 3 Segmented Button for View Switching
    seg_urls_label = ft.Text("Direct URLs (0)")
    seg_val_label = ft.Text("Validation & Size (0 B)")

    results_view_container = ft.Container(content=table_scroll, expand=True)

    def on_view_segment_changed(e):
        selected = list(e.control.selected)[0] if e.control.selected else "urls"
        if selected == "urls":
            results_view_container.content = table_scroll
        elif selected == "val":
            results_view_container.content = val_container
        else:
            results_view_container.content = log_column
        results_view_container.update()

    view_segments = ft.SegmentedButton(
        selected=["urls"],
        allow_multiple_selection=False,
        on_change=on_view_segment_changed,
        segments=[
            ft.Segment(value="urls", label=seg_urls_label, icon=ft.Icon(ft.Icons.LINK)),
            ft.Segment(value="val", label=seg_val_label, icon=ft.Icon(ft.Icons.CHECKLIST)),
            ft.Segment(value="log", label=ft.Text("Activity Log"), icon=ft.Icon(ft.Icons.TERMINAL)),
        ]
    )

    # Bottom Actions
    push_jd_btn = ft.FilledButton("Push to JD2", icon=ft.Icons.FAST_FORWARD, height=38)
    copy_all_btn = ft.FilledTonalButton("Copy All", icon=ft.Icons.COPY_ALL, height=38)
    count_label = ft.Text("Paste a link above and click 'Extract & Resolve'", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

    def on_copy_all(e):
        if state["resolved_links"]:
            pyperclip.copy("\n".join(state["resolved_links"]))
            show_snack(f"Copied all {len(state['resolved_links'])} direct URLs to clipboard!")

    def on_push_jd(e):
        if not state["resolved_links"]:
            show_snack("No resolved links to push.", success=False)
            return
        port = settings.get("jd_port", 9666)
        success, msg = integrations.push_to_jdownloader(
            state["resolved_links"],
            package_name=state["last_game_title"],
            source_url=url_input.value.strip(),
            port=port
        )
        show_snack(msg, success=success)

    def on_export(format_type: str):
        if not state["resolved_links"]:
            show_snack("No resolved links to export.", success=False)
            return
        safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', state["last_game_title"]).strip('_')
        out_dir = get_export_dir()
        os.makedirs(out_dir, exist_ok=True)

        if format_type == "txt":
            fp = os.path.join(out_dir, f"{safe_title}_direct_urls.txt")
            integrations.export_text(fp, state["resolved_links"], state["last_game_title"])
            show_snack(f"📁 Saved to Downloads: {os.path.basename(fp)}")
        elif format_type == "json":
            fp = os.path.join(out_dir, f"{safe_title}.json")
            size_str = state["last_val_summary"].total_size_str if state["last_val_summary"] else ""
            integrations.export_json(fp, state["last_game_title"], url_input.value.strip(), state["resolved_links"], size_str)
            show_snack(f"📁 Saved to Downloads: {os.path.basename(fp)}")
        elif format_type == "crawljob":
            fp = os.path.join(out_dir, f"{safe_title}.crawljob")
            integrations.export_crawljob(fp, state["resolved_links"], state["last_game_title"])
            show_snack(f"📁 Saved to Downloads: {os.path.basename(fp)}")

        open_folder_cross_platform(out_dir)

    export_menu = ft.PopupMenuButton(
        icon=ft.Icons.SAVE_ALT,
        tooltip="Export URLs",
        items=[
            ft.PopupMenuItem(content=ft.Text("Export as .txt"), on_click=lambda _: on_export("txt")),
            ft.PopupMenuItem(content=ft.Text("Export as .json"), on_click=lambda _: on_export("json")),
            ft.PopupMenuItem(content=ft.Text("Export as .crawljob"), on_click=lambda _: on_export("crawljob")),
        ]
    )

    copy_all_btn.on_click = on_copy_all
    push_jd_btn.on_click = on_push_jd

    # ── Pipeline Execution ──
    def run_pipeline_thread(target_url: str):
        t_start = time.time()
        try:
            url_type = scraper.detect_url_type(target_url)
            log(f"Detected input type: {url_type}")

            concur = settings.get("concurrency", 3)
            engine = ResolutionEngine(concurrency=concur, max_retries=2, headless=False)

            channel = detect_browser_channel()
            if not channel:
                log("ERROR: No Chrome or Edge browser detected on system.")
                set_status("No Browser Found", icon=ft.Icons.ERROR, color=ft.Colors.RED_400)
                finish_pipeline()
                return

            log(f"Using system browser engine: {channel}")

            if url_type in ("fuckingfast_direct", "raw_links"):
                raw_urls = re.findall(r'https?://[^\s,]+', target_url)
                state["pastebin_links"] = [u for u in raw_urls if "fuckingfast.co" in u] or [target_url]
                state["last_game_title"] = "FuckingFast Direct Parts"
                log(f"Phase 1: Parsed {len(state['pastebin_links'])} direct fuckingfast link(s)")
            elif url_type == "fitgirl_game_page":
                set_status("Scraping Game Page...", icon=ft.Icons.SEARCH, color=ft.Colors.AMBER_400)
                log(f"Phase 1: Fetching FitGirl game page: {target_url}")
                pastebins, game_title = scraper.extract_game_page_pastebins(target_url)
                state["last_game_title"] = game_title or "FitGirl Repack"
                log(f"Game Repack: {state['last_game_title']}")

                ff_pastebins = [p for p in pastebins if p["hoster"] == "FuckingFast"] or (pastebins[:1] if pastebins else [])
                if not ff_pastebins:
                    log("ERROR: No pastebin mirrors found.")
                    set_status("No Mirrors Found", icon=ft.Icons.ERROR, color=ft.Colors.RED_400)
                    finish_pipeline()
                    return

                target_pastebin = ff_pastebins[0]["url"]
                set_status("Decrypting Pastebin...", icon=ft.Icons.LOCK_OPEN, color=ft.Colors.AMBER_400)
                state["pastebin_links"] = asyncio.run(engine.fetch_pastebin_links(target_pastebin, log_cb=log))
            else:
                set_status("Decrypting Pastebin...", icon=ft.Icons.LOCK_OPEN, color=ft.Colors.AMBER_400)
                state["pastebin_links"] = asyncio.run(engine.fetch_pastebin_links(target_url, log_cb=log))
                state["last_game_title"] = "FitGirl Pastebin Download"

            total_count = len(state["pastebin_links"])
            log(f"Phase 1 complete: extracted {total_count} game parts")

            if total_count == 0:
                set_status("No Links Found", icon=ft.Icons.ERROR, color=ft.Colors.RED_400)
                finish_pipeline()
                return

            # Initialize Table Rows
            data_table.rows.clear()
            for i, u in enumerate(state["pastebin_links"]):
                p_name = u.split("#")[-1] if "#" in u else f"part_{i+1:02d}"
                data_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(i + 1))),
                            ft.DataCell(ft.Text(p_name, size=12)),
                            ft.DataCell(ft.Text("--", size=12, color=ft.Colors.ON_SURFACE_VARIANT)),
                            ft.DataCell(ft.Chip(label=ft.Text("Pending", size=10), leading=ft.Icon(ft.Icons.HOURGLASS_EMPTY, size=12))),
                            ft.DataCell(ft.IconButton(icon=ft.Icons.COPY, icon_size=16, tooltip="Copy Link", disabled=True))
                        ]
                    )
                )
            page.update()

            def on_progress(done_count, total, avg_speed, eta, active_tabs, part_name, direct_url, status):
                frac = done_count / max(1, total)
                progress_bar.value = frac
                set_status(f"Resolving {done_count}/{total}", icon=ft.Icons.AUTORENEW, color=ft.Colors.BLUE_400)
                eta_str = f"{int(eta)}s" if eta < 60 else f"{int(eta // 60)}m {int(eta % 60)}s"
                stats_text.value = f"⚡ Speed: {avg_speed:.1f}s/part | ⏱️ ETA: ~{eta_str} | 🌐 {active_tabs} tabs active"

                # Update row
                for idx, row in enumerate(data_table.rows):
                    if row.cells[1].content.value == part_name:
                        if status == "resolved" and direct_url:
                            row.cells[3].content = ft.Chip(label=ft.Text("Resolved", size=10, color=ft.Colors.GREEN_400), leading=ft.Icon(ft.Icons.CHECK_CIRCLE, size=12, color=ft.Colors.GREEN_400))
                            row.cells[4].content = ft.IconButton(icon=ft.Icons.COPY, icon_size=16, tooltip="Copy Link", on_click=lambda _, u=direct_url: (pyperclip.copy(u), show_snack("Copied direct link!")))
                        else:
                            row.cells[3].content = ft.Chip(label=ft.Text("Failed", size=10, color=ft.Colors.RED_400), leading=ft.Icon(ft.Icons.ERROR, size=12, color=ft.Colors.RED_400))
                        break

                seg_urls_label.value = f"Direct URLs ({done_count}/{total})"
                page.update()

            def on_retry_pass(failed_cnt, cur_att, max_att):
                set_status(f"Retrying {failed_cnt} links (Pass {cur_att}/{max_att})", icon=ft.Icons.REFRESH, color=ft.Colors.AMBER_400)

            results = asyncio.run(
                engine.resolve_all_async(
                    urls=state["pastebin_links"],
                    on_progress=on_progress,
                    on_log=log,
                    on_retry_pass=on_retry_pass,
                    cancel_event=state["cancel_event"]
                )
            )

            resolved_urls = [r.direct_url for r in results if r.direct_url]
            state["resolved_links"] = resolved_urls

            # Phase 3: Link Validation
            total_size_str = "0 B"
            total_size_bytes = 0

            if settings.get("auto_validate", True) and resolved_urls and not (state["cancel_event"] and state["cancel_event"].is_set()):
                set_status("Validating Links & Size...", icon=ft.Icons.CHECKLIST, color=ft.Colors.CYAN_400)
                log(f"Phase 3: Validating {len(resolved_urls)} direct URLs & computing exact download sizes...")

                val_summary = validator.validate_links(resolved_urls, max_workers=15, cancel_event=state["cancel_event"])
                state["last_val_summary"] = val_summary
                total_size_str = val_summary.total_size_str
                total_size_bytes = val_summary.total_bytes

                # Update row sizes in table
                for vl in val_summary.links:
                    for row in data_table.rows:
                        if vl.filename in row.cells[1].content.value or row.cells[1].content.value in vl.filename:
                            row.cells[2].content = ft.Text(vl.content_length_str, size=12, weight=ft.FontWeight.W_500)

                val_text.value = (
                    f"=== REPACK DOWNLOAD VALIDATION SUMMARY ===\n"
                    f"Game: {state['last_game_title']}\n"
                    f"Total Repack Size: {total_size_str}\n"
                    f"Active Verified Links: {val_summary.valid_count}/{val_summary.total_links}\n"
                    f"{'='*50}\n\n"
                    + "\n".join(f"{'✅' if l.is_valid else '❌'} [{l.content_length_str:>10}]  {l.filename}" for l in val_summary.links)
                )
                seg_val_label.value = f"Validation & Size ({total_size_str})"
                log(f"Validation Complete: {val_summary.valid_count}/{val_summary.total_links} verified | Total Size: {total_size_str}")

            is_cancelled = bool(state["cancel_event"] and state["cancel_event"].is_set())

            # Save to SQLite History ONLY if not cancelled and URLs were resolved
            if resolved_urls and not is_cancelled:
                history_mgr.add_record(
                    title=state["last_game_title"],
                    source_url=target_url,
                    total_parts=total_count,
                    resolved_count=len(resolved_urls),
                    total_size_bytes=total_size_bytes,
                    total_size_str=total_size_str,
                    urls=resolved_urls
                )

            total_elapsed = time.time() - t_start
            avg_s = total_elapsed / len(resolved_urls) if resolved_urls else 0

            if is_cancelled:
                set_status("Cancelled", icon=ft.Icons.CANCEL, color=ft.Colors.RED_400)
                stats_text.value = f"🛑 Extraction cancelled by user ({len(resolved_urls)}/{total_count} resolved)."
                count_label.value = f"⚠️ Cancelled: {len(resolved_urls)}/{total_count} parts resolved"
                show_snack("Extraction cancelled by user.", success=False)
            else:
                set_status(f"Complete ({avg_s:.1f}s/part)", icon=ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400)
                stats_text.value = f"🚀 Completed in {total_elapsed:.1f}s | Avg Speed: {avg_s:.1f}s/part | Total Size: {total_size_str} | Success: {len(resolved_urls)}/{total_count}"
                count_label.value = f"✨ {len(resolved_urls)} direct URLs ready ({total_size_str})"
                show_snack(f"All {len(resolved_urls)} direct URLs resolved successfully!")

        except Exception as ex:
            log(f"Pipeline error: {ex}")
            set_status("Error Occurred", icon=ft.Icons.ERROR, color=ft.Colors.RED_400)
        finally:
            finish_pipeline()

    def start_pipeline(e):
        target = url_input.value.strip()
        if not target:
            show_snack("Please enter a valid FitGirl game page or pastebin URL.", success=False)
            return

        state["is_running"] = True
        state["cancel_event"] = threading.Event()
        start_btn.disabled = True
        cancel_btn.disabled = False
        progress_bar.value = None
        set_status("Starting Engine...", icon=ft.Icons.AUTORENEW, color=ft.Colors.BLUE_400)
        page.update()

        threading.Thread(target=run_pipeline_thread, args=(target,), daemon=True).start()

    def cancel_pipeline(e):
        if state["cancel_event"]:
            state["cancel_event"].set()
        log("🛑 Cancellation requested by user.")
        set_status("Cancelling...", icon=ft.Icons.CANCEL, color=ft.Colors.AMBER_400)
        cancel_btn.disabled = True
        page.update()

    def finish_pipeline():
        state["is_running"] = False
        start_btn.disabled = False
        cancel_btn.disabled = True
        if progress_bar.value is None:
            progress_bar.value = 1.0
        page.update()

    start_btn.on_click = start_pipeline
    cancel_btn.on_click = cancel_pipeline

    extractor_screen = ft.Container(
        key="screen_extractor",
        content=ft.Column([
            # Top Banner Card
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            banner_logo,
                            ft.Text("FitGirl Direct Link Extractor", size=20, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=ft.Text("⚡ TURBO SPEED ENGINE", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                bgcolor=seed_color,
                                border_radius=12,
                                padding=ft.Padding.symmetric(horizontal=10, vertical=4)
                            ),
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Text(
                            "Directly paste FitGirl Game Pages, Pastebin URLs, or FuckingFast links. Converts all parts to direct dl.fuckingfast.co URLs via concurrent tabs with auto-retry and JDownloader 2 push.",
                            size=12, color=ft.Colors.ON_SURFACE_VARIANT
                        )
                    ], spacing=6),
                    padding=16
                )
            ),
            # URL Input Card
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("FitGirl Game Page, Pastebin, or FuckingFast URL:", size=13, weight=ft.FontWeight.BOLD),
                            url_badge
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([
                            url_input,
                            start_btn,
                            cancel_btn
                        ]),
                        ft.Row([
                            status_chip,
                            progress_bar
                        ]),
                        stats_text
                    ], spacing=10),
                    padding=16
                )
            ),
            # Results Card with Segmented Controls
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([view_segments], alignment=ft.MainAxisAlignment.START),
                        ft.Divider(height=1),
                        results_view_container
                    ], expand=True, spacing=8),
                    padding=12,
                    expand=True
                ),
                expand=True
            ),
            # Bottom Action Bar
            ft.Card(
                content=ft.Container(
                    content=ft.Row([
                        count_label,
                        ft.Row([
                            push_jd_btn,
                            export_menu,
                            copy_all_btn
                        ])
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=12
                )
            )
        ], spacing=10, expand=True),
        padding=16,
        expand=True
    )

    # ═══════════════════════════════════════════════════════════════════
    # ── SCREEN 2: HISTORY & ARCHIVE SCREEN ──
    # ═══════════════════════════════════════════════════════════════════
    history_list = ft.ListView(expand=True, spacing=8, padding=12)
    search_input = ft.TextField(
        hint_text="🔍 Search past games...",
        prefix_icon=ft.Icons.SEARCH,
        dense=True,
        width=300,
        border_radius=8
    )

    def refresh_history(query: str = ""):
        history_list.controls.clear()
        records = history_mgr.get_records(query)
        if not records:
            history_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.HISTORY, size=48, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text("No extraction records found.", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text("Resolved game links will automatically appear here.", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.Alignment.CENTER,
                    padding=40
                )
            )
        else:
            for rec in records:
                urls = rec.get("urls", [])
                history_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row([
                                ft.Column([
                                    ft.Text(rec["title"], size=14, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"📅 {rec['timestamp']}  •  📦 {rec['resolved_count']}/{rec['total_parts']} Parts  •  💾 {rec['total_size_str']}", size=11, color=seed_color),
                                ], expand=True, spacing=4),
                                ft.Row([
                                    ft.FilledTonalButton("📋 Copy", on_click=lambda _, u=urls: (pyperclip.copy("\n".join(u)), show_snack(f"Copied {len(u)} URLs!"))),
                                    ft.FilledButton("🚀 Push JD2", on_click=lambda _, u=urls, t=rec["title"]: (
                                        show_snack(integrations.push_to_jdownloader(u, t, port=settings.get("jd_port", 9666))[1])
                                    )),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=ft.Colors.RED_400,
                                        tooltip="Delete Record",
                                        on_click=lambda _, r_id=rec["id"]: (history_mgr.delete_record(r_id), refresh_history(search_input.value))
                                    )
                                ])
                            ]),
                            padding=12
                        )
                    )
                )
        page.update()

    search_input.on_change = lambda e: refresh_history(search_input.value)

    history_screen = ft.Container(
        key="screen_history",
        content=ft.Column([
            ft.Card(
                content=ft.Container(
                    content=ft.Row([
                        ft.Text("Saved Game Extractions & Archive", size=18, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            search_input,
                            ft.OutlinedButton(
                                "Clear All",
                                icon=ft.Icons.DELETE_FOREVER,
                                on_click=lambda _: (history_mgr.clear_history(), refresh_history())
                            )
                        ])
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=16
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=history_list,
                    expand=True,
                    padding=6
                ),
                expand=True
            )
        ], spacing=10, expand=True),
        padding=16,
        expand=True
    )

    # ═══════════════════════════════════════════════════════════════════
    # ── SCREEN 3: SETTINGS SCREEN ──
    # ═══════════════════════════════════════════════════════════════════
    def on_theme_changed(theme_name: str):
        settings["theme_seed"] = theme_name
        save_settings(settings)
        new_seed = THEME_PRESETS.get(theme_name, "#6750A4")
        page.theme = ft.Theme(color_scheme_seed=new_seed)
        page.update()
        show_snack(f"Theme switched to {theme_name}!")

    theme_dropdown = ft.Dropdown(
        value=settings.get("theme_seed", "Deep Violet"),
        options=[ft.dropdown.Option(text=name, key=name) for name in THEME_PRESETS.keys()],
        width=200,
        dense=True,
        on_select=lambda e: on_theme_changed(e.control.value)
    )

    def on_logo_changed(logo_name: str):
        settings["logo_style"] = logo_name
        save_settings(settings)
        rel_path = LOGO_PRESETS.get(logo_name, "assets/logo_minimal.png")
        abs_path = get_resource_path(rel_path)
        rail_logo.src = abs_path
        banner_logo.src = abs_path
        page.window.icon = abs_path
        apply_windows_native_icon("app_icon.ico")
        page.update()
        show_snack(f"Branding logo switched to {logo_name}!")

    def on_mode_changed(mode_name: str):
        settings["theme_mode"] = mode_name
        save_settings(settings)
        if mode_name == "Light":
            page.theme_mode = ft.ThemeMode.LIGHT
        elif mode_name == "System":
            page.theme_mode = ft.ThemeMode.SYSTEM
        else:
            page.theme_mode = ft.ThemeMode.DARK
        page.update()
        show_snack(f"Switched to {mode_name} Mode!")

    theme_mode_btn = ft.SegmentedButton(
        selected=[settings.get("theme_mode", "Dark")],
        allow_multiple_selection=False,
        on_change=lambda e: on_mode_changed(list(e.control.selected)[0]),
        segments=[
            ft.Segment(value="Dark", label=ft.Text("Dark"), icon=ft.Icon(ft.Icons.DARK_MODE)),
            ft.Segment(value="Light", label=ft.Text("Light"), icon=ft.Icon(ft.Icons.LIGHT_MODE)),
            ft.Segment(value="System", label=ft.Text("System"), icon=ft.Icon(ft.Icons.SETTINGS_SYSTEM_DAYDREAM)),
        ]
    )

    logo_dropdown = ft.Dropdown(
        value=settings.get("logo_style", "Minimalist Cyber Link"),
        options=[ft.dropdown.Option(text=name, key=name) for name in LOGO_PRESETS.keys()],
        width=220,
        dense=True,
        on_select=lambda e: on_logo_changed(e.control.value)
    )

    def on_animation_changed(anim_name: str):
        settings["animation_style"] = anim_name
        save_settings(settings)
        cfg = ANIMATION_PRESETS.get(anim_name, ANIMATION_PRESETS["Fast Subtle Fade"])
        cur_screen = screens[state["active_screen"]]
        screen_holder.content = create_screen_switcher(cfg, cur_screen)
        screen_holder.update()
        show_snack(f"Tab transition set to {anim_name} (Live Applied)!")

    anim_dropdown = ft.Dropdown(
        value=settings.get("animation_style", "Fast Subtle Fade"),
        options=[ft.dropdown.Option(text=name, key=name) for name in ANIMATION_PRESETS.keys()],
        width=220,
        dense=True,
        on_select=lambda e: on_animation_changed(e.control.value)
    )

    concur_slider = ft.Slider(
        min=1, max=6, divisions=5,
        value=settings.get("concurrency", 3),
        label="{value} tabs"
    )
    concur_label = ft.Text(f"{settings.get('concurrency', 3)} Parallel Tabs (Recommended: 3–4)", size=12, color=seed_color)

    def on_concur_changed(e):
        val = int(round(concur_slider.value))
        concur_label.value = f"{val} Parallel Tabs (Recommended: 3–4)"
        settings["concurrency"] = val
        save_settings(settings)
        concur_label.update()
        update_stats_display()

    concur_slider.on_change = on_concur_changed

    def on_val_switch_changed(e):
        settings["auto_validate"] = e.control.value
        save_settings(settings)
        update_stats_display()

    val_switch = ft.Switch(
        value=settings.get("auto_validate", True),
        on_change=on_val_switch_changed
    )

    jd_port_field = ft.TextField(
        value=str(settings.get("jd_port", 9666)),
        width=100,
        dense=True,
        on_change=lambda e: (settings.update({"jd_port": int(e.control.value or 9666)}), save_settings(settings))
    )

    def test_jd_connection(e):
        port = int(jd_port_field.value or 9666)
        if integrations.is_jdownloader_running(port):
            show_snack(f"✅ JDownloader 2 is running and reachable on port {port}!")
        else:
            show_snack(f"⚠️ Could not connect to JDownloader 2 on port {port}.", success=False)

    settings_screen = ft.Container(
        key="screen_settings",
        content=ft.Column([
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Engine & Customization Preferences", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("Configure Material 3 color themes, worker tab concurrency, validation, and JDownloader 2 integration.", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
                    ]),
                    padding=16
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        # 1. Theme Brightness Mode (Dark / Light / System)
                        ft.Row([
                            ft.Column([
                                ft.Text("Appearance & Theme Mode:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Toggle between Dark Mode, Light Mode, or follow Windows System setting.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            theme_mode_btn
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 2. Theme Palette Color
                        ft.Row([
                            ft.Column([
                                ft.Text("Material 3 Theme Palette Preset:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Choose dynamic seed color (Deep Violet, Emerald, Sapphire, Amber, Rose).", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            theme_dropdown
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 3. App Logo & Branding
                        ft.Row([
                            ft.Column([
                                ft.Text("Application Logo & Branding Theme:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Switch between Minimalist Cyber Link and Retro Arcade Cartridge.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            logo_dropdown
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 4. Tab Transition Animation
                        ft.Row([
                            ft.Column([
                                ft.Text("Tab Switch Animation Effect:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Choose between Instant (Snappy 0ms) and Fast Subtle Fade (180ms).", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            anim_dropdown
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 5. Concurrency
                        ft.Row([
                            ft.Column([
                                ft.Text("Worker Tab Concurrency (Parallel Resolution):", size=13, weight=ft.FontWeight.BOLD),
                                concur_label
                            ]),
                            ft.Container(content=concur_slider, width=220)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 6. Auto-Validation
                        ft.Row([
                            ft.Column([
                                ft.Text("Auto-Validate Links & Calculate Repack Size:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Runs rapid 1-byte Range checks to compute total download size and verify live filenames.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            val_switch
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 7. JD2 Port
                        ft.Row([
                            ft.Column([
                                ft.Text("JDownloader 2 Local CNL Port:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Default port for JDownloader 2 Click'n'Load / FlashGot web API is 9666.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            ft.Row([
                                jd_port_field,
                                ft.FilledTonalButton("Test", on_click=test_jd_connection)
                            ])
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 8. Check for Updates
                        ft.Row([
                            ft.Column([
                                ft.Text(f"Application Version & Updates ({updater.CURRENT_VERSION}):", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Check GitHub Releases for the latest patches, features, and binary builds.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            ft.FilledButton("Check for Updates", icon=ft.Icons.SYSTEM_UPDATE, on_click=show_update_dialog)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 9. About & Author Credits
                        ft.Row([
                            ft.Column([
                                ft.Text("Original Author & Open Source License:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Developed by Vikash (@vik05h) • Licensed under PolyForm Noncommercial 1.0.0 (Free for personal use; no commercial use).", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            ft.TextButton("GitHub Repo", icon=ft.Icons.OPEN_IN_NEW, on_click=lambda _: updater.open_release_page("https://github.com/vik05h/Link-Extractor"))
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ], spacing=12),
                    padding=20
                )
            )
        ], spacing=10, expand=True, scroll=ft.ScrollMode.ADAPTIVE),
        padding=16,
        expand=True
    )

    # ── Main Layout with NavigationRail ──
    active_anim_name = settings.get("animation_style", "Fast Subtle Fade")
    anim_cfg = ANIMATION_PRESETS.get(active_anim_name, ANIMATION_PRESETS["Fast Subtle Fade"])

    screens = [extractor_screen, history_screen, settings_screen]

    screen_container = None

    def create_screen_switcher(cfg, cur_screen):
        nonlocal screen_container
        screen_container = ft.AnimatedSwitcher(
            content=cur_screen,
            transition=cfg["transition"],
            duration=cfg["duration"],
            reverse_duration=cfg["reverse_duration"],
            switch_in_curve=cfg.get("curve_in", ft.AnimationCurve.EASE_IN_OUT),
            switch_out_curve=cfg.get("curve_out", ft.AnimationCurve.EASE_IN_OUT),
            expand=True
        )
        return screen_container

    screen_holder = ft.Container(
        content=create_screen_switcher(anim_cfg, extractor_screen),
        expand=True
    )

    def on_nav_change(e):
        idx = e.control.selected_index
        state["active_screen"] = idx
        if idx == 0:
            update_stats_display()
        elif idx == 1:
            refresh_history(search_input.value)

        screen_container.content = screens[idx]
        screen_container.update()

    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=80,
        min_extended_width=180,
        leading=ft.Container(
            content=rail_logo,
            padding=ft.Padding.only(top=16, bottom=16)
        ),
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.BOLT_OUTLINED, selected_icon=ft.Icons.BOLT, label="Extractor"),
            ft.NavigationRailDestination(icon=ft.Icons.HISTORY_OUTLINED, selected_icon=ft.Icons.HISTORY, label="History"),
            ft.NavigationRailDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label="Settings"),
        ],
        on_change=on_nav_change,
        trailing=ft.Container(
            content=ft.IconButton(
                icon=ft.Icons.SYSTEM_UPDATE_ALT,
                tooltip="Check for Updates",
                on_click=show_update_dialog
            ),
            padding=ft.Padding.only(bottom=16)
        )
    )

    page.add(
        ft.Row([
            nav_rail,
            ft.VerticalDivider(width=1),
            screen_holder
        ], expand=True, spacing=0)
    )


if __name__ == "__main__":
    ft.run(main, assets_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"))
