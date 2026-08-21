import os
import sys
import time
import asyncio
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict, Callable, Tuple
import flet as ft

from history import HistoryManager
import updater
import utils


@dataclass
class AppState:
    is_running: bool = False
    cancel_event: Optional[threading.Event] = None
    pastebin_links: List[str] = field(default_factory=list)
    resolved_links: List[str] = field(default_factory=list)
    last_game_title: str = "FitGirl Repack"
    last_cover_image: str = ""
    last_val_summary: Optional[Any] = None
    active_screen: int = 0
    community_games: List[Dict[str, Any]] = field(default_factory=list)
    community_loading: bool = False


class UIContext:
    def __init__(self, page: ft.Page, settings: Dict[str, Any], history_mgr: HistoryManager):
        self.page = page
        self.settings = settings
        self.history_mgr = history_mgr
        self.state: Optional[AppState] = None
        self.current_tab: str = "urls"

        # Control references bound by screen builders
        self.status_chip_text: Optional[ft.Text] = None
        self.status_chip_icon: Optional[ft.Icon] = None
        self.status_chip: Optional[ft.Container] = None
        self.progress_bar: Optional[ft.ProgressBar] = None
        self.stats_text: Optional[ft.Text] = None
        self.data_table: Optional[ft.DataTable] = None
        self.val_text: Optional[ft.Text] = None
        self.val_container: Optional[ft.ListView] = None
        self.log_column: Optional[ft.ListView] = None
        self.results_view_container: Optional[ft.Container] = None
        self.view_segments: Optional[ft.SegmentedButton] = None
        self.seg_urls_label: Optional[ft.Text] = None
        self.seg_val_label: Optional[ft.Text] = None
        self.start_btn: Optional[ft.FilledButton] = None
        self.cancel_btn: Optional[ft.OutlinedButton] = None
        self.count_label: Optional[ft.Text] = None
        self.url_input: Optional[ft.TextField] = None
        self.rail_logo: Optional[ft.Image] = None
        self.banner_logo: Optional[ft.Image] = None

        # Navigation and Screen Switching Handlers
        self.nav_rail: Optional[ft.NavigationRail] = None
        self.screen_container: Optional[ft.AnimatedSwitcher] = None
        self.screens: List[ft.Control] = []
        self.refresh_community_cb: Optional[Any] = None
        self.refresh_history_cb: Optional[Any] = None
        self.theme_change_listeners: List[Callable[[str], None]] = []
        self.tour_targets: Dict[str, ft.Container] = {}
        self._active_highlight_target: Optional[str] = None

    def register_theme_listener(self, callback: Callable[[str], None]):
        """Register a listener called when theme seed changes."""
        if callback not in self.theme_change_listeners:
            self.theme_change_listeners.append(callback)

    def notify_theme_changed(self, new_seed: str):
        """Notify all registered listeners of theme change."""
        for cb in self.theme_change_listeners:
            try:
                cb(new_seed)
            except Exception:
                pass

    def navigate_to_screen(self, index: int):
        """Programmatically switch active screen and update NavigationRail."""
        if self.state:
            self.state.active_screen = index
        if self.nav_rail:
            self.nav_rail.selected_index = index
            try:
                self.nav_rail.update()
            except Exception:
                pass
        if self.screen_container and self.screens and 0 <= index < len(self.screens):
            self.screen_container.content = self.screens[index]
            try:
                self.screen_container.update()
            except Exception:
                pass
        if index == 0:
            self.update_stats_display(self.state.is_running if self.state else False)
            self.refresh_extractor_ui()
        elif index == 1 and self.refresh_community_cb:
            self.refresh_community_cb()
        elif index == 2 and self.refresh_history_cb:
            self.refresh_history_cb()
        try:
            self.page.update()
        except Exception:
            pass

    def show_snack(self, text: str, success: bool = True):
        snack = ft.SnackBar(
            content=ft.Row([
                ft.Icon(
                    ft.Icons.CHECK_CIRCLE_ROUNDED if success else ft.Icons.ERROR_OUTLINE_ROUNDED,
                    color=ft.Colors.WHITE,
                    size=18
                ),
                ft.Text(text, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE, expand=True, size=13)
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.GREEN_700 if success else ft.Colors.RED_700,
            duration=3500,
            open=True,
            behavior=ft.SnackBarBehavior.FLOATING,
            margin=ft.Padding.only(left=20, right=20, bottom=20)
        )
        self.page.overlay.append(snack)
        self.page.update()

    def show_whats_new_dialog(self, version: Optional[str] = None):
        target_version = version or updater.CURRENT_VERSION
        changelog = updater.get_version_changelog(target_version)

        highlights = changelog.get("highlights", [])
        bug_fixes = changelog.get("bug_fixes", [])

        highlight_items = [
            ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, size=16, color=ft.Colors.GREEN_400),
                ft.Text(item, size=12, expand=True)
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
            for item in highlights
        ]

        bug_fix_items = [
            ft.Row([
                ft.Icon(ft.Icons.BUILD_ROUNDED, size=16, color=ft.Colors.AMBER_400),
                ft.Text(item, size=12, expand=True)
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
            for item in bug_fixes
        ]

        def on_dismiss(e):
            self.settings["last_seen_version"] = target_version
            utils.save_settings(self.settings)
            self.page.pop_dialog()

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER_400, size=24),
                ft.Text(f"What's New in {target_version}", weight=ft.FontWeight.BOLD)
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(changelog.get("title", "Latest Release Notes & Improvements"), size=13, weight=ft.FontWeight.W_600, color=ft.Colors.PRIMARY),
                    ft.Divider(height=12),
                    ft.Text("Highlights & New Features", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE),
                    ft.Container(
                        content=ft.Column(highlight_items, spacing=8, scroll=ft.ScrollMode.ADAPTIVE),
                        padding=10,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                        border_radius=8,
                        height=140
                    ),
                    ft.Container(height=6),
                    ft.Text("Bug Fixes & Stability", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE),
                    ft.Container(
                        content=ft.Column(bug_fix_items, spacing=8, scroll=ft.ScrollMode.ADAPTIVE),
                        padding=10,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                        border_radius=8,
                        height=120
                    )
                ], tight=True, spacing=6, scroll=ft.ScrollMode.ADAPTIVE),
                width=520,
                height=380
            ),
            actions=[
                ft.FilledButton(
                    "Got It!",
                    icon=ft.Icons.CHECK,
                    on_click=on_dismiss
                )
            ]
        )
        self.page.show_dialog(dlg)

    def highlight_tour_target(self, target_key: Optional[str], color: Optional[str] = None):
        """Highlight the active UI container with glowing border and shadow during guided tour."""
        # Reset previous target highlight
        if self._active_highlight_target and self._active_highlight_target in self.tour_targets:
            prev_ctrl = self.tour_targets[self._active_highlight_target]
            prev_ctrl.border = None
            prev_ctrl.shadow = None
            try:
                prev_ctrl.update()
            except Exception:
                pass
        self._active_highlight_target = target_key

        # Apply glowing highlight border to new target
        if target_key and target_key in self.tour_targets:
            new_ctrl = self.tour_targets[target_key]
            active_color = color or ft.Colors.CYAN_400
            new_ctrl.border = ft.Border.all(2.5, active_color)
            new_ctrl.shadow = ft.BoxShadow(
                spread_radius=3,
                blur_radius=14,
                color=ft.Colors.with_opacity(0.45, active_color),
                offset=ft.Offset(0, 2)
            )
            new_ctrl.animate = ft.Animation(300, ft.AnimationCurve.EASE_OUT)
            try:
                new_ctrl.update()
            except Exception:
                pass

    def start_live_tour(self):
        """
        Interactive In-App Live Auto-Guide Spotlight Tour.
        Directly navigates between app screens and presents a floating glassmorphic spotlight controller.
        """
        tour_steps = [
            {
                "screen_idx": 0,
                "target_key": "extractor_input",
                "step_num": "1 of 5",
                "badge": "EXTRACTOR INPUT",
                "color": ft.Colors.CYAN_400,
                "icon": ft.Icons.LINK_ROUNDED,
                "title": "Step 1: Input & Smart Auto-Detection",
                "desc": "Paste any FitGirl Game Page, Pastebin URL, or direct FuckingFast link here. The engine auto-detects the format and checks if community pre-fetched links already exist."
            },
            {
                "screen_idx": 0,
                "target_key": "extractor_banner",
                "step_num": "2 of 5",
                "badge": "TURBO ENGINE",
                "color": ft.Colors.AMBER_400,
                "icon": ft.Icons.BOLT_ROUNDED,
                "title": "Step 2: Turbo Multi-Tab Engine",
                "desc": "When resolving fresh, the Playwright browser pool automatically solves Cloudflare Turnstile in parallel across concurrent tabs (~1.8s/part) with a 120 FPS live progress HUD."
            },
            {
                "screen_idx": 1,
                "target_key": "community_banner",
                "step_num": "3 of 5",
                "badge": "COMMUNITY CLOUD",
                "color": ft.Colors.GREEN_400,
                "icon": ft.Icons.ALL_INCLUSIVE,
                "title": "Step 3: FitGirl Community Cloud Cache",
                "desc": "Browse pre-fetched game extractions shared anonymously by the community. Click 'Use Instant' to download in 0 seconds, or click the Health Check icon to verify live server status."
            },
            {
                "screen_idx": 2,
                "target_key": "history_card",
                "step_num": "4 of 5",
                "badge": "HISTORY ARCHIVE",
                "color": ft.Colors.PURPLE_400,
                "icon": ft.Icons.HISTORY_ROUNDED,
                "title": "Step 4: SQLite Extraction Archive",
                "desc": "All successfully resolved games are saved to your local database. Search past repacks, re-copy direct links, or push straight to JDownloader 2 anytime."
            },
            {
                "screen_idx": 3,
                "target_key": "settings_card",
                "step_num": "5 of 5",
                "badge": "CUSTOMIZATION",
                "color": ft.Colors.PINK_400,
                "icon": ft.Icons.PALETTE_ROUNDED,
                "title": "Step 5: Dynamic Themes & 120 FPS Mode",
                "desc": "Personalize your experience with 8 dynamic Material 3 color themes, toggle between 60 FPS and 120 FPS high-refresh rate modes, and tune parallel worker tabs."
            }
        ]

        cur_step = [0]
        active_overlay = [None]

        def update_tour_view():
            idx = cur_step[0]
            data = tour_steps[idx]
            self.navigate_to_screen(data["screen_idx"])
            self.highlight_tour_target(data.get("target_key"), data["color"])

            title_text.value = data["title"]
            desc_text.value = data["desc"]
            badge_text.value = data["badge"]
            badge_container.bgcolor = data["color"]
            step_pill.value = f"STEP {data['step_num'].upper()}"
            step_icon.name = data["icon"]
            step_icon.color = data["color"]
            card_container.border = ft.Border.all(1.5, data["color"])

            prev_btn.disabled = (idx == 0)
            if idx == len(tour_steps) - 1:
                next_btn.text = "Complete Tour 🎉"
                next_btn.icon = ft.Icons.CHECK_CIRCLE_ROUNDED
            else:
                next_btn.text = "Next Step ▶"
                next_btn.icon = ft.Icons.ARROW_FORWARD_ROUNDED

            try:
                self.page.update()
            except Exception:
                pass

        def on_prev(e):
            if cur_step[0] > 0:
                cur_step[0] -= 1
                update_tour_view()

        def on_next(e):
            if cur_step[0] < len(tour_steps) - 1:
                cur_step[0] += 1
                update_tour_view()
            else:
                end_tour()

        def end_tour(e=None):
            self.highlight_tour_target(None)
            self.settings["has_seen_tutorial"] = True
            utils.save_settings(self.settings)
            if active_overlay[0] in self.page.overlay:
                self.page.overlay.remove(active_overlay[0])
            self.navigate_to_screen(0)
            self.show_snack("Tour completed! Welcome to Link Extractor.")
            try:
                self.page.update()
            except Exception:
                pass

        title_text = ft.Text(size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)
        desc_text = ft.Text(size=11, color=ft.Colors.ON_SURFACE_VARIANT)
        badge_text = ft.Text(size=9, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        badge_container = ft.Container(
            content=badge_text,
            border_radius=6,
            padding=ft.Padding.symmetric(horizontal=6, vertical=2)
        )
        step_pill = ft.Text("STEP 1 OF 5", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
        step_icon = ft.Icon(ft.Icons.HELP_OUTLINE, size=22)

        prev_btn = ft.TextButton("◀ Previous", on_click=on_prev)
        next_btn = ft.FilledButton("Next Step ▶", on_click=on_next)

        card_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    step_icon,
                    title_text,
                    badge_container,
                    ft.Container(expand=True),
                    step_pill,
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=16,
                        tooltip="Exit Tour",
                        on_click=end_tour
                    )
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                desc_text,
                ft.Row([
                    prev_btn,
                    ft.Row([
                        ft.TextButton("Exit Tour", on_click=end_tour),
                        next_btn
                    ], spacing=6)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], spacing=6, tight=True),
            padding=14,
            width=580,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=12,
            shadow=ft.BoxShadow(
                spread_radius=2,
                blur_radius=16,
                color=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
                offset=ft.Offset(0, 4)
            )
        )

        tour_card = ft.Card(
            content=card_container,
            elevation=10
        )

        tour_overlay = ft.Container(
            content=tour_card,
            alignment=ft.Alignment.BOTTOM_CENTER,
            padding=ft.Padding.only(bottom=20)
        )

        active_overlay[0] = tour_overlay
        self.page.overlay.append(tour_overlay)
        update_tour_view()

    def show_tutorial_dialog(self):
        """Alias for starting the interactive live tour."""
        self.start_live_tour()

    def show_update_dialog(self, e=None, silent_if_up_to_date: bool = False):
        async def _check_and_render():
            has_update, release_info, msg = await asyncio.to_thread(updater.check_for_updates)
            if has_update and release_info:
                self._render_update_available_dialog(release_info)
            elif not silent_if_up_to_date:
                self._render_up_to_date_dialog()

        self.page.run_task(_check_and_render)

    def _render_up_to_date_dialog(self):
        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400),
                ft.Text("You're Up to Date!", weight=ft.FontWeight.BOLD)
            ]),
            content=ft.Text(f"You are running the latest version ({updater.CURRENT_VERSION}).\nNo new updates found on GitHub."),
            actions=[
                ft.TextButton("View What's New", icon=ft.Icons.INFO_OUTLINE, on_click=lambda _: (self.page.pop_dialog(), self.show_whats_new_dialog())),
                ft.FilledButton("OK", on_click=lambda _: self.page.pop_dialog())
            ]
        )
        self.page.show_dialog(dlg)

    def _render_update_available_dialog(self, release_info: Dict[str, Any]):
        download_url = release_info.get("download_url", "")
        latest_tag = release_info.get("latest_version", "")
        release_name = release_info.get("name", latest_tag)
        release_body = release_info.get("body", "No changelog provided.")

        cancel_dl = threading.Event()
        progress_bar = ft.ProgressBar(value=0, expand=True)
        status_label = ft.Text("Ready to download update...", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        size_label = ft.Text("", size=11, color=ft.Colors.PRIMARY)

        dl_ui = ft.Column([
            ft.Text(f"Downloading Link Extractor {latest_tag}...", size=13, weight=ft.FontWeight.BOLD),
            ft.Container(height=4),
            progress_bar,
            ft.Row([status_label, size_label], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], visible=False, tight=True)

        details_ui = ft.Column([
            ft.Text(f"Release: {release_name}", weight=ft.FontWeight.W_600),
            ft.Divider(),
            ft.Text("Changelog & Highlights:", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Container(
                content=ft.Column([
                    ft.Text(release_body, size=12, selectable=True)
                ], scroll=ft.ScrollMode.ADAPTIVE),
                padding=10,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=8,
                height=150
            ),
            ft.Container(height=4),
            dl_ui
        ], tight=True, width=500)

        later_btn = ft.TextButton("Later", on_click=lambda _: (cancel_dl.set(), self.page.pop_dialog()))
        browser_btn = ft.TextButton("View on GitHub", icon=ft.Icons.OPEN_IN_NEW, on_click=lambda _: updater.open_release_page(release_info.get("html_url")))

        def start_in_app_update(ev):
            update_btn.disabled = True
            later_btn.text = "Cancel Download"
            dl_ui.visible = True
            self.page.update()

            def _download_worker():
                try:
                    def _on_progress(downloaded: int, total: int, pct: float):
                        progress_bar.value = pct / 100.0
                        mb_down = downloaded / (1024 * 1024)
                        mb_tot = total / (1024 * 1024)
                        status_label.value = f"Downloading: {pct:.1f}%"
                        size_label.value = f"{mb_down:.1f} MB / {mb_tot:.1f} MB"
                        try:
                            self.page.update()
                        except Exception:
                            pass

                    target_file = updater.download_update(download_url, _on_progress, cancel_dl)
                    status_label.value = "Download completed! Preparing update..."
                    progress_bar.value = 1.0
                    self.page.update()
                    time.sleep(0.5)

                    # Save version so next launch shows What's New
                    self.settings["last_seen_version"] = updater.CURRENT_VERSION
                    utils.save_settings(self.settings)

                    restarted = updater.apply_update_and_restart(target_file)
                    if restarted:
                        try:
                            self.page.window.close()
                        except Exception:
                            pass
                        os._exit(0)
                    else:
                        status_label.value = f"Update downloaded to {target_file}.\nRestart application to apply."
                        size_label.value = ""
                        later_btn.text = "Close"
                        self.page.update()

                except Exception as ex:
                    if cancel_dl.is_set():
                        status_label.value = "Update download cancelled."
                    else:
                        status_label.value = f"Update failed: {ex}"
                    status_label.color = ft.Colors.RED_400
                    later_btn.text = "Close"
                    try:
                        self.page.update()
                    except Exception:
                        pass

            threading.Thread(target=_download_worker, daemon=True).start()

        update_btn = ft.FilledButton(
            "Update Now",
            icon=ft.Icons.DOWNLOAD,
            on_click=start_in_app_update
        )

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE, color=ft.Colors.AMBER_400),
                ft.Text(f"Update Available: {latest_tag}", weight=ft.FontWeight.BOLD)
            ]),
            content=details_ui,
            actions=[
                later_btn,
                browser_btn,
                update_btn
            ]
        )
        self.page.show_dialog(dlg)

    def check_startup_updates(self):
        """Asynchronously check for updates at startup if enabled."""
        if not self.settings.get("check_updates_on_startup", True):
            return

        async def _worker():
            await asyncio.sleep(0.8)
            try:
                has_update, release_info, msg = await asyncio.to_thread(updater.check_for_updates, 6.0)
                if has_update and release_info:
                    self._render_update_available_dialog(release_info)
            except Exception:
                pass

        self.page.run_task(_worker)

    def check_whats_new_on_startup(self):
        """Check if application was updated or running for the first time on a new version."""
        last_seen = self.settings.get("last_seen_version")
        if last_seen is None or updater.parse_version(updater.CURRENT_VERSION) > updater.parse_version(str(last_seen)):
            # Defer slightly so page renders
            async def _whats_new_worker():
                await asyncio.sleep(0.4)
                self.show_whats_new_dialog(updater.CURRENT_VERSION)

            self.page.run_task(_whats_new_worker)

    def refresh_extractor_ui(self):
        """Safely update dynamic Extractor UI controls from any thread."""
        if self.state and self.state.active_screen != 0:
            return

        controls_to_update = [
            self.data_table,
            self.view_segments,
            self.results_view_container,
            self.progress_bar,
            self.stats_text,
            self.status_chip,
            self.count_label,
        ]
        for ctrl in controls_to_update:
            if ctrl:
                try:
                    ctrl.update()
                except Exception:
                    pass
        try:
            self.page.update()
        except Exception:
            pass

    def set_status(self, text: str, icon=ft.Icons.CHECK_CIRCLE_OUTLINE, color=None):
        if not self.status_chip_text or not self.status_chip_icon or not self.status_chip:
            return
        self.status_chip_text.value = text
        if icon:
            self.status_chip_icon.name = icon
        if color:
            self.status_chip_text.color = color
            self.status_chip_icon.color = color
            self.status_chip.bgcolor = ft.Colors.with_opacity(0.18, color)
            self.status_chip.border = ft.Border.all(1, ft.Colors.with_opacity(0.6, color))
        else:
            self.status_chip_text.color = ft.Colors.ON_SURFACE_VARIANT
            self.status_chip_icon.color = ft.Colors.ON_SURFACE_VARIANT
            self.status_chip.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGH
            self.status_chip.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        self.refresh_extractor_ui()

    def log(self, msg: str):
        if not self.log_column:
            return
        ts = time.strftime("%H:%M:%S")
        self.log_column.controls.append(
            ft.Text(f"[{ts}] {msg}", size=11, font_family="Consolas", color=ft.Colors.ON_SURFACE_VARIANT)
        )
        self.refresh_extractor_ui()

    def update_stats_display(self, is_running: bool = False):
        if not is_running and self.stats_text:
            c = self.settings.get("concurrency", 3)
            v = "Enabled" if self.settings.get("auto_validate", True) else "Disabled"
            self.stats_text.value = f"⚡ Worker Pool: {c} Tabs | 🔁 Auto-Retry: 2 Passes | 🔍 Validation: {v}"
            try:
                self.stats_text.update()
            except Exception:
                pass
