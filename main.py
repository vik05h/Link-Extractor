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


def load_settings() -> dict:
    default_settings = {
        "concurrency": 3,
        "auto_validate": True,
        "jd_port": 9666,
        "theme_seed": "Deep Violet"
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
    settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


def main(page: ft.Page):
    page.title = f"FitGirl Direct Link Extractor {updater.CURRENT_VERSION} — Flutter High Speed Edition"
    page.window.width = 1180
    page.window.height = 840
    page.window.min_width = 960
    page.window.min_height = 680
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    settings = load_settings()
    history_mgr = HistoryManager()

    seed_name = settings.get("theme_seed", "Deep Violet")
    seed_color = THEME_PRESETS.get(seed_name, "#6750A4")
    page.theme = ft.Theme(color_scheme_seed=seed_color)

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
        page.snack_bar = ft.SnackBar(
            content=ft.Text(text, weight=ft.FontWeight.W_500),
            bgcolor=ft.Colors.GREEN_800 if success else ft.Colors.RED_800,
            duration=3500
        )
        page.snack_bar.open = True
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
                    ft.Text("Changelog & Highlights:", size=12, color=ft.Colors.GREY_400),
                    ft.Container(
                        content=ft.Text(release_info["body"], size=12),
                        padding=10,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        border_radius=8,
                        height=160
                    )
                ], tight=True, width=480),
                actions=[
                    ft.TextButton("Later", on_click=lambda _: page.close(dlg)),
                    ft.FilledButton(
                        "Download Update",
                        icon=ft.Icons.DOWNLOAD,
                        on_click=lambda _: (updater.open_release_page(release_info["download_url"]), page.close(dlg))
                    )
                ]
            )
            page.open(dlg)
        else:
            dlg = ft.AlertDialog(
                title=ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400),
                    ft.Text("You're Up to Date!", weight=ft.FontWeight.BOLD)
                ]),
                content=ft.Text(f"You are running the latest version ({updater.CURRENT_VERSION}).\nNo new updates found on GitHub."),
                actions=[ft.FilledButton("OK", on_click=lambda _: page.close(dlg))]
            )
            page.open(dlg)

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

    url_badge = ft.Chip(
        label=ft.Text("Auto-detecting URL", size=11, weight=ft.FontWeight.BOLD),
        leading=ft.Icon(ft.Icons.AUTORENEW, size=14)
    )

    def on_url_changed(e):
        url_type = scraper.detect_url_type(url_input.value or "")
        if url_type == "fitgirl_game_page":
            url_badge.label.value = "🎮 Game Page Detected"
            url_badge.leading.name = ft.Icons.SPORTS_ESPORTS
        elif url_type == "fitgirl_pastebin":
            url_badge.label.value = "📋 Pastebin Detected"
            url_badge.leading.name = ft.Icons.CONTENT_PASTE
        elif url_type in ("fuckingfast_direct", "raw_links"):
            url_badge.label.value = "⚡ Direct FuckingFast Links"
            url_badge.leading.name = ft.Icons.FLASH_ON
        else:
            url_badge.label.value = "Auto-detecting URL"
            url_badge.leading.name = ft.Icons.AUTORENEW
        url_badge.update()

    url_input.on_change = on_url_changed

    start_btn = ft.FilledButton("Extract & Resolve", icon=ft.Icons.ROCKET_LAUNCH, height=44)
    cancel_btn = ft.OutlinedButton("Cancel", icon=ft.Icons.CANCEL, height=44, disabled=True)

    status_chip = ft.Chip(
        label=ft.Text("Ready", size=12, weight=ft.FontWeight.BOLD),
        leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=14)
    )
    progress_bar = ft.ProgressBar(value=0, expand=True, border_radius=6)
    stats_text = ft.Text(
        f"⚡ Worker Pool: {settings.get('concurrency', 3)} Tabs | 🔁 Auto-Retry: 2 Passes | 🔍 Validation: Enabled",
        size=11, color=ft.Colors.GREY_400
    )

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
        controls=[ft.Text("[Ready] Waiting for extraction input...", size=11, font_family="Consolas", color=ft.Colors.GREY_400)],
        expand=True,
        auto_scroll=True,
        padding=10
    )

    def log(msg: str):
        ts = time.strftime("%H:%M:%S")
        log_column.controls.append(ft.Text(f"[{ts}] {msg}", size=11, font_family="Consolas"))
        log_column.update()

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
    count_label = ft.Text("Paste a link above and click 'Extract & Resolve'", size=12, color=ft.Colors.GREY_400)

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
        out_dir = os.path.dirname(os.path.abspath(__file__))

        if format_type == "txt":
            fp = os.path.join(out_dir, f"{safe_title}_direct_urls.txt")
            integrations.export_text(fp, state["resolved_links"], state["last_game_title"])
            show_snack(f"Exported text file: {os.path.basename(fp)}")
        elif format_type == "json":
            fp = os.path.join(out_dir, f"{safe_title}.json")
            size_str = state["last_val_summary"].total_size_str if state["last_val_summary"] else ""
            integrations.export_json(fp, state["last_game_title"], url_input.value.strip(), state["resolved_links"], size_str)
            show_snack(f"Exported JSON file: {os.path.basename(fp)}")
        elif format_type == "crawljob":
            fp = os.path.join(out_dir, f"{safe_title}.crawljob")
            integrations.export_crawljob(fp, state["resolved_links"], state["last_game_title"])
            show_snack(f"Exported CrawlJob: {os.path.basename(fp)}")

    export_menu = ft.PopupMenuButton(
        icon=ft.Icons.SAVE_ALT,
        tooltip="Export URLs",
        items=[
            ft.PopupMenuItem(content="Export as .txt", on_click=lambda _: on_export("txt")),
            ft.PopupMenuItem(content="Export as .json", on_click=lambda _: on_export("json")),
            ft.PopupMenuItem(content="Export as .crawljob", on_click=lambda _: on_export("crawljob")),
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
                status_chip.label.value = "No Browser Found"
                status_chip.leading.name = ft.Icons.ERROR
                finish_pipeline()
                return

            log(f"Using system browser engine: {channel}")

            if url_type in ("fuckingfast_direct", "raw_links"):
                raw_urls = re.findall(r'https?://[^\s,]+', target_url)
                state["pastebin_links"] = [u for u in raw_urls if "fuckingfast.co" in u] or [target_url]
                state["last_game_title"] = "FuckingFast Direct Parts"
                log(f"Phase 1: Parsed {len(state['pastebin_links'])} direct fuckingfast link(s)")
            elif url_type == "fitgirl_game_page":
                status_chip.label.value = "Scraping Game Page..."
                status_chip.update()
                log(f"Phase 1: Fetching FitGirl game page: {target_url}")
                pastebins, game_title = scraper.extract_game_page_pastebins(target_url)
                state["last_game_title"] = game_title or "FitGirl Repack"
                log(f"Game Repack: {state['last_game_title']}")

                ff_pastebins = [p for p in pastebins if p["hoster"] == "FuckingFast"] or (pastebins[:1] if pastebins else [])
                if not ff_pastebins:
                    log("ERROR: No pastebin mirrors found.")
                    status_chip.label.value = "No Mirrors Found"
                    finish_pipeline()
                    return

                target_pastebin = ff_pastebins[0]["url"]
                status_chip.label.value = "Decrypting Pastebin..."
                status_chip.update()
                state["pastebin_links"] = asyncio.run(engine.fetch_pastebin_links(target_pastebin, log_cb=log))
            else:
                status_chip.label.value = "Decrypting Pastebin..."
                status_chip.update()
                state["pastebin_links"] = asyncio.run(engine.fetch_pastebin_links(target_url, log_cb=log))
                state["last_game_title"] = "FitGirl Pastebin Download"

            total_count = len(state["pastebin_links"])
            log(f"Phase 1 complete: extracted {total_count} game parts")

            if total_count == 0:
                status_chip.label.value = "No Links Found"
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
                            ft.DataCell(ft.Text("--", size=12, color=ft.Colors.GREY_400)),
                            ft.DataCell(ft.Chip(label=ft.Text("Pending", size=10), leading=ft.Icon(ft.Icons.HOURGLASS_EMPTY, size=12))),
                            ft.DataCell(ft.IconButton(icon=ft.Icons.COPY, icon_size=16, tooltip="Copy Link", disabled=True))
                        ]
                    )
                )
            data_table.update()

            def on_progress(done_count, total, avg_speed, eta, active_tabs, part_name, direct_url, status):
                frac = done_count / max(1, total)
                progress_bar.value = frac
                status_chip.label.value = f"Resolving {done_count}/{total}"
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
                status_chip.label.value = f"Retrying {failed_cnt} links (Pass {cur_att}/{max_att})"
                status_chip.update()

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
                status_chip.label.value = "Validating Links & Size..."
                status_chip.update()
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

            # Save to SQLite History
            if resolved_urls:
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
            status_chip.label.value = f"Complete ({avg_s:.1f}s/part)"
            status_chip.leading.name = ft.Icons.CHECK_CIRCLE
            stats_text.value = f"🚀 Completed in {total_elapsed:.1f}s | Avg Speed: {avg_s:.1f}s/part | Total Size: {total_size_str} | Success: {len(resolved_urls)}/{total_count}"
            count_label.value = f"✨ {len(resolved_urls)} direct URLs ready ({total_size_str})"
            show_snack(f"All {len(resolved_urls)} direct URLs resolved successfully!")

        except Exception as ex:
            log(f"Pipeline error: {ex}")
            status_chip.label.value = "Error Occurred"
            status_chip.leading.name = ft.Icons.ERROR
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
        status_chip.label.value = "Starting Engine..."
        page.update()

        threading.Thread(target=run_pipeline_thread, args=(target,), daemon=True).start()

    def cancel_pipeline(e):
        if state["cancel_event"]:
            state["cancel_event"].set()
        log("🛑 Cancellation requested by user.")
        status_chip.label.value = "Cancelling..."
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
        content=ft.Column([
            # Top Banner Card
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("FitGirl Direct Link Extractor", size=20, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=ft.Text("⚡ TURBO SPEED ENGINE", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                bgcolor=seed_color,
                                border_radius=12,
                                padding=ft.Padding.symmetric(horizontal=10, vertical=4)
                            ),
                        ]),
                        ft.Text(
                            "Directly paste FitGirl Game Pages, Pastebin URLs, or FuckingFast links. Converts all parts to direct dl.fuckingfast.co URLs via concurrent tabs with auto-retry and JDownloader 2 push.",
                            size=12, color=ft.Colors.GREY_300
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
                        ft.Icon(ft.Icons.HISTORY, size=48, color=ft.Colors.GREY_600),
                        ft.Text("No extraction records found.", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_400),
                        ft.Text("Resolved game links will automatically appear here.", size=12, color=ft.Colors.GREY_500)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
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
        history_list.update()

    search_input.on_change = lambda e: refresh_history(search_input.value)

    history_screen = ft.Container(
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

    concur_slider.on_change = on_concur_changed

    val_switch = ft.Switch(
        value=settings.get("auto_validate", True),
        on_change=lambda e: (settings.update({"auto_validate": e.control.value}), save_settings(settings))
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
        content=ft.Column([
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Engine & Customization Preferences", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("Configure Material 3 color themes, worker tab concurrency, validation, and JDownloader 2 integration.", size=12, color=ft.Colors.GREY_400)
                    ]),
                    padding=16
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        # 1. Theme Color
                        ft.Row([
                            ft.Column([
                                ft.Text("Material 3 Theme Palette Preset:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Choose dynamic seed color (Deep Violet, Emerald, Sapphire, Amber, Rose).", size=11, color=ft.Colors.GREY_400)
                            ]),
                            theme_dropdown
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 2. Concurrency
                        ft.Row([
                            ft.Column([
                                ft.Text("Worker Tab Concurrency (Parallel Resolution):", size=13, weight=ft.FontWeight.BOLD),
                                concur_label
                            ]),
                            ft.Container(content=concur_slider, width=220)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 3. Auto-Validation
                        ft.Row([
                            ft.Column([
                                ft.Text("Auto-Validate Links & Calculate Repack Size:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Runs rapid 1-byte Range checks to compute total download size and verify live filenames.", size=11, color=ft.Colors.GREY_400)
                            ]),
                            val_switch
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 4. JD2 Port
                        ft.Row([
                            ft.Column([
                                ft.Text("JDownloader 2 Local CNL Port:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Default port for JDownloader 2 Click'n'Load / FlashGot web API is 9666.", size=11, color=ft.Colors.GREY_400)
                            ]),
                            ft.Row([
                                jd_port_field,
                                ft.FilledTonalButton("Test", on_click=test_jd_connection)
                            ])
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 5. Check for Updates
                        ft.Row([
                            ft.Column([
                                ft.Text(f"Application Version & Updates ({updater.CURRENT_VERSION}):", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Check GitHub Releases for the latest patches, features, and binary builds.", size=11, color=ft.Colors.GREY_400)
                            ]),
                            ft.FilledButton("Check for Updates", icon=ft.Icons.SYSTEM_UPDATE, on_click=show_update_dialog)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ], spacing=12),
                    padding=20
                )
            )
        ], spacing=10, expand=True),
        padding=16,
        expand=True
    )

    # ── Main Layout with NavigationRail ──
    screen_container = ft.AnimatedSwitcher(
        content=extractor_screen,
        transition=ft.AnimatedSwitcherTransition.FADE,
        duration=250,
        expand=True
    )

    def on_nav_change(e):
        idx = e.control.selected_index
        state["active_screen"] = idx
        if idx == 0:
            screen_container.content = extractor_screen
        elif idx == 1:
            refresh_history(search_input.value)
            screen_container.content = history_screen
        elif idx == 2:
            screen_container.content = settings_screen
        page.update()

    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=80,
        min_extended_width=180,
        leading=ft.Container(
            content=ft.Icon(ft.Icons.FLASH_ON, size=32, color=seed_color),
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
            screen_container
        ], expand=True, spacing=0)
    )


if __name__ == "__main__":
    ft.run(main)
