import os
import re
import pyperclip
import flet as ft

import scraper
import integrations
import utils
from ui.state import UIContext, AppState
from ui.screens.pipeline import start_pipeline, cancel_pipeline


def build_extractor_screen(ctx: UIContext, state: AppState, seed_color: str) -> ft.Container:
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
            ctx.page.update()

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

    progress_bar = ft.ProgressBar(value=0, expand=True, border_radius=6)
    stats_text = ft.Text(
        f"⚡ Worker Pool: {ctx.settings.get('concurrency', 3)} Tabs | 🔁 Auto-Retry: 2 Passes | 🔍 Validation: {'Enabled' if ctx.settings.get('auto_validate', True) else 'Disabled'}",
        size=11, color=ft.Colors.ON_SURFACE_VARIANT
    )

    # Interactive DataTable for Resolved Links
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

    # Material 3 Segmented Button for View Switching
    seg_urls_label = ft.Text("Direct URLs (0)")
    seg_val_label = ft.Text("Validation & Size (0 B)")

    results_view_container = ft.Container(content=table_scroll, expand=True)

    def on_view_segment_changed(e):
        if not e.control.selected:
            view_segments.selected = [ctx.current_tab]
            view_segments.update()
            return
        selected_val = list(e.control.selected)[0]
        ctx.current_tab = selected_val
        view_segments.selected = [selected_val]
        if selected_val == "urls":
            results_view_container.content = table_scroll
        elif selected_val == "val":
            results_view_container.content = val_container
        else:
            results_view_container.content = log_column
        results_view_container.update()
        view_segments.update()

    view_segments = ft.SegmentedButton(
        selected=["urls"],
        allow_multiple_selection=False,
        allow_empty_selection=False,
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
        if state.resolved_links:
            pyperclip.copy("\n".join(state.resolved_links))
            ctx.show_snack(f"Copied all {len(state.resolved_links)} direct URLs to clipboard!")

    def on_push_jd(e):
        if not state.resolved_links:
            ctx.show_snack("No resolved links to push.", success=False)
            return
        port = ctx.settings.get("jd_port", 9666)
        success, msg = integrations.push_to_jdownloader(
            state.resolved_links,
            package_name=state.last_game_title,
            source_url=url_input.value.strip(),
            port=port
        )
        ctx.show_snack(msg, success=success)

    def on_export(format_type: str):
        if not state.resolved_links:
            ctx.show_snack("No resolved links to export.", success=False)
            return
        safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', state.last_game_title).strip('_')
        out_dir = utils.get_export_dir()
        os.makedirs(out_dir, exist_ok=True)

        if format_type == "txt":
            fp = os.path.join(out_dir, f"{safe_title}_direct_urls.txt")
            integrations.export_text(fp, state.resolved_links, state.last_game_title)
            ctx.show_snack(f"📁 Saved to Downloads: {os.path.basename(fp)}")
        elif format_type == "json":
            fp = os.path.join(out_dir, f"{safe_title}.json")
            size_str = state.last_val_summary.total_size_str if state.last_val_summary else ""
            integrations.export_json(fp, state.last_game_title, url_input.value.strip(), state.resolved_links, size_str)
            ctx.show_snack(f"📁 Saved to Downloads: {os.path.basename(fp)}")
        elif format_type == "crawljob":
            fp = os.path.join(out_dir, f"{safe_title}.crawljob")
            integrations.export_crawljob(fp, state.resolved_links, state.last_game_title)
            ctx.show_snack(f"📁 Saved to Downloads: {os.path.basename(fp)}")

        utils.open_folder_cross_platform(out_dir)

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
    start_btn.on_click = lambda e: start_pipeline(ctx, state, e)
    cancel_btn.on_click = lambda e: cancel_pipeline(ctx, state, e)

    # Bind control references into ctx
    ctx.url_input = url_input
    ctx.start_btn = start_btn
    ctx.cancel_btn = cancel_btn
    ctx.status_chip = status_chip
    ctx.status_chip_text = status_chip_text
    ctx.status_chip_icon = status_chip_icon
    ctx.progress_bar = progress_bar
    ctx.stats_text = stats_text
    ctx.data_table = data_table
    ctx.val_text = val_text
    ctx.val_container = val_container
    ctx.log_column = log_column
    ctx.results_view_container = results_view_container
    ctx.view_segments = view_segments
    ctx.seg_urls_label = seg_urls_label
    ctx.seg_val_label = seg_val_label
    ctx.count_label = count_label

    extractor_screen = ft.Container(
        key="screen_extractor",
        content=ft.Column([
            # Top Banner Card
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ctx.banner_logo,
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

    return extractor_screen
