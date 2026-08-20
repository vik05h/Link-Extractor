import time
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
import flet as ft

from history import HistoryManager
import updater


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

    def show_update_dialog(self, e=None):
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
                    ft.TextButton("Later", on_click=lambda _: self.page.pop_dialog()),
                    ft.FilledButton(
                        "Download Update",
                        icon=ft.Icons.DOWNLOAD,
                        on_click=lambda _: (updater.open_release_page(release_info["download_url"]), self.page.pop_dialog())
                    )
                ]
            )
            self.page.show_dialog(dlg)
        else:
            dlg = ft.AlertDialog(
                title=ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400),
                    ft.Text("You're Up to Date!", weight=ft.FontWeight.BOLD)
                ]),
                content=ft.Text(f"You are running the latest version ({updater.CURRENT_VERSION}).\nNo new updates found on GitHub."),
                actions=[ft.FilledButton("OK", on_click=lambda _: self.page.pop_dialog())]
            )
            self.page.show_dialog(dlg)

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
