import os
import sys
import time
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
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
    last_val_summary: Optional[Any] = None
    active_screen: int = 0


class UIContext:
    def __init__(self, page: ft.Page, settings: Dict[str, Any], history_mgr: HistoryManager):
        self.page = page
        self.settings = settings
        self.history_mgr = history_mgr

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
        self.seg_urls_label: Optional[ft.Text] = None
        self.seg_val_label: Optional[ft.Text] = None
        self.start_btn: Optional[ft.FilledButton] = None
        self.cancel_btn: Optional[ft.OutlinedButton] = None
        self.count_label: Optional[ft.Text] = None
        self.url_input: Optional[ft.TextField] = None
        self.rail_logo: Optional[ft.Image] = None
        self.banner_logo: Optional[ft.Image] = None

    def show_snack(self, text: str, success: bool = True):
        snack = ft.SnackBar(
            content=ft.Text(text, weight=ft.FontWeight.W_500),
            bgcolor=ft.Colors.GREEN_800 if success else ft.Colors.RED_800,
            duration=3500,
            open=True
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

    def show_update_dialog(self, e=None, silent_if_up_to_date: bool = False):
        def _check_and_render():
            has_update, release_info, msg = updater.check_for_updates()
            if has_update and release_info:
                self._render_update_available_dialog(release_info)
            elif not silent_if_up_to_date:
                self._render_up_to_date_dialog()

        threading.Thread(target=_check_and_render, daemon=True).start()

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
            ft.Text(f"Downloading FitGirl Link Extractor {latest_tag}...", size=13, weight=ft.FontWeight.BOLD),
            ft.Container(height=4),
            progress_bar,
            ft.Row([status_label, size_label], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], visible=False, tight=True)

        details_ui = ft.Column([
            ft.Text(f"Release: {release_name}", weight=ft.FontWeight.W_600),
            ft.Divider(),
            ft.Text("Changelog & Highlights:", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Container(
                content=ft.Text(release_body, size=12, scroll=ft.ScrollMode.ADAPTIVE),
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

        def _worker():
            time.sleep(0.8)
            try:
                has_update, release_info, msg = updater.check_for_updates(timeout=6.0)
                if has_update and release_info:
                    self._render_update_available_dialog(release_info)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def check_whats_new_on_startup(self):
        """Check if application was updated or running for the first time on a new version."""
        last_seen = self.settings.get("last_seen_version")
        if last_seen is None or updater.parse_version(updater.CURRENT_VERSION) > updater.parse_version(str(last_seen)):
            # Defer slightly so page renders
            def _whats_new_worker():
                time.sleep(0.4)
                self.show_whats_new_dialog(updater.CURRENT_VERSION)

            threading.Thread(target=_whats_new_worker, daemon=True).start()

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
        try:
            self.status_chip.update()
        except Exception:
            self.page.update()

    def log(self, msg: str):
        if not self.log_column:
            return
        ts = time.strftime("%H:%M:%S")
        self.log_column.controls.append(
            ft.Text(f"[{ts}] {msg}", size=11, font_family="Consolas", color=ft.Colors.ON_SURFACE_VARIANT)
        )
        try:
            if self.results_view_container and self.results_view_container.content == self.log_column:
                self.log_column.update()
            else:
                self.page.update()
        except Exception:
            try:
                self.page.update()
            except Exception:
                pass

    def update_stats_display(self, is_running: bool = False):
        if not is_running and self.stats_text:
            c = self.settings.get("concurrency", 3)
            v = "Enabled" if self.settings.get("auto_validate", True) else "Disabled"
            self.stats_text.value = f"⚡ Worker Pool: {c} Tabs | 🔁 Auto-Retry: 2 Passes | 🔍 Validation: {v}"
            try:
                self.stats_text.update()
            except Exception:
                pass
