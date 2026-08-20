import re
import time
import asyncio
import threading
import pyperclip
import flet as ft

import scraper
from engine import ResolutionEngine, detect_browser_channel
import validator
from ui.state import UIContext, AppState


def run_pipeline_thread(ctx: UIContext, state: AppState, target_url: str):
    t_start = time.time()
    try:
        url_type = scraper.detect_url_type(target_url)
        ctx.log(f"Detected input type: {url_type}")

        concur = ctx.settings.get("concurrency", 3)
        engine = ResolutionEngine(concurrency=concur, max_retries=2, headless=False)

        channel = detect_browser_channel()
        if not channel:
            ctx.log("ERROR: No Chrome or Edge browser detected on system.")
            ctx.set_status("No Browser Found", icon=ft.Icons.ERROR, color=ft.Colors.RED_400)
            finish_pipeline(ctx, state)
            return

        ctx.log(f"Using system browser engine: {channel}")

        if url_type in ("fuckingfast_direct", "raw_links"):
            raw_urls = re.findall(r'https?://[^\s,]+', target_url)
            state.pastebin_links = [u for u in raw_urls if "fuckingfast.co" in u] or [target_url]
            state.last_game_title = "FuckingFast Direct Parts"
            ctx.log(f"Phase 1: Parsed {len(state.pastebin_links)} direct fuckingfast link(s)")
        elif url_type == "fitgirl_game_page":
            ctx.set_status("Scraping Game Page...", icon=ft.Icons.SEARCH, color=ft.Colors.AMBER_400)
            ctx.log(f"Phase 1: Fetching FitGirl game page: {target_url}")
            pastebins, game_title = scraper.extract_game_page_pastebins(target_url)
            state.last_game_title = game_title or "FitGirl Repack"
            ctx.log(f"Game Repack: {state.last_game_title}")

            ff_pastebins = [p for p in pastebins if p["hoster"] == "FuckingFast"] or (pastebins[:1] if pastebins else [])
            if not ff_pastebins:
                ctx.log("ERROR: No pastebin mirrors found.")
                ctx.set_status("No Mirrors Found", icon=ft.Icons.ERROR, color=ft.Colors.RED_400)
                finish_pipeline(ctx, state)
                return

            target_pastebin = ff_pastebins[0]["url"]
            ctx.set_status("Decrypting Pastebin...", icon=ft.Icons.LOCK_OPEN, color=ft.Colors.AMBER_400)
            state.pastebin_links = asyncio.run(engine.fetch_pastebin_links(target_pastebin, log_cb=ctx.log))
        else:
            ctx.set_status("Decrypting Pastebin...", icon=ft.Icons.LOCK_OPEN, color=ft.Colors.AMBER_400)
            state.pastebin_links = asyncio.run(engine.fetch_pastebin_links(target_url, log_cb=ctx.log))
            state.last_game_title = "FitGirl Pastebin Download"

        total_count = len(state.pastebin_links)
        ctx.log(f"Phase 1 complete: extracted {total_count} game parts")

        if total_count == 0:
            ctx.set_status("No Links Found", icon=ft.Icons.ERROR, color=ft.Colors.RED_400)
            finish_pipeline(ctx, state)
            return

        # Initialize Table Rows
        if ctx.data_table:
            ctx.data_table.rows.clear()
            for i, u in enumerate(state.pastebin_links):
                p_name = u.split("#")[-1] if "#" in u else f"part_{i+1:02d}"
                ctx.data_table.rows.append(
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
            ctx.page.update()

        def on_progress(done_count, total, avg_speed, eta, active_tabs, part_name, direct_url, status):
            frac = done_count / max(1, total)
            if ctx.progress_bar:
                ctx.progress_bar.value = frac
            ctx.set_status(f"Resolving {done_count}/{total}", icon=ft.Icons.AUTORENEW, color=ft.Colors.BLUE_400)
            eta_str = f"{int(eta)}s" if eta < 60 else f"{int(eta // 60)}m {int(eta % 60)}s"
            if ctx.stats_text:
                ctx.stats_text.value = f"⚡ Speed: {avg_speed:.1f}s/part | ⏱️ ETA: ~{eta_str} | 🌐 {active_tabs} tabs active"

            # Update row
            if ctx.data_table:
                for idx, row in enumerate(ctx.data_table.rows):
                    if row.cells[1].content.value == part_name:
                        if status == "resolved" and direct_url:
                            row.cells[3].content = ft.Chip(
                                label=ft.Text("Resolved", size=10, color=ft.Colors.GREEN_400),
                                leading=ft.Icon(ft.Icons.CHECK_CIRCLE, size=12, color=ft.Colors.GREEN_400)
                            )
                            row.cells[4].content = ft.IconButton(
                                icon=ft.Icons.COPY,
                                icon_size=16,
                                tooltip="Copy Link",
                                on_click=lambda _, u=direct_url: (pyperclip.copy(u), ctx.show_snack("Copied direct link!"))
                            )
                        else:
                            row.cells[3].content = ft.Chip(
                                label=ft.Text("Failed", size=10, color=ft.Colors.RED_400),
                                leading=ft.Icon(ft.Icons.ERROR, size=12, color=ft.Colors.RED_400)
                            )
                        break

            if ctx.seg_urls_label:
                ctx.seg_urls_label.value = f"Direct URLs ({done_count}/{total})"
            ctx.page.update()

        def on_retry_pass(failed_cnt, cur_att, max_att):
            ctx.set_status(f"Retrying {failed_cnt} links (Pass {cur_att}/{max_att})", icon=ft.Icons.REFRESH, color=ft.Colors.AMBER_400)

        results = asyncio.run(
            engine.resolve_all_async(
                urls=state.pastebin_links,
                on_progress=on_progress,
                on_log=ctx.log,
                on_retry_pass=on_retry_pass,
                cancel_event=state.cancel_event
            )
        )

        resolved_urls = [r.direct_url for r in results if r.direct_url]
        state.resolved_links = resolved_urls

        # Phase 3: Link Validation
        total_size_str = "0 B"
        total_size_bytes = 0

        if ctx.settings.get("auto_validate", True) and resolved_urls and not (state.cancel_event and state.cancel_event.is_set()):
            ctx.set_status("Validating Links & Size...", icon=ft.Icons.CHECKLIST, color=ft.Colors.CYAN_400)
            ctx.log(f"Phase 3: Validating {len(resolved_urls)} direct URLs & computing exact download sizes...")

            val_summary = validator.validate_links(resolved_urls, max_workers=15, cancel_event=state.cancel_event)
            state.last_val_summary = val_summary
            total_size_str = val_summary.total_size_str
            total_size_bytes = val_summary.total_bytes

            # Update row sizes in table
            if ctx.data_table:
                for vl in val_summary.links:
                    for row in ctx.data_table.rows:
                        if vl.filename in row.cells[1].content.value or row.cells[1].content.value in vl.filename:
                            row.cells[2].content = ft.Text(vl.content_length_str, size=12, weight=ft.FontWeight.W_500)

            if ctx.val_text:
                ctx.val_text.value = (
                    f"=== REPACK DOWNLOAD VALIDATION SUMMARY ===\n"
                    f"Game: {state.last_game_title}\n"
                    f"Total Repack Size: {total_size_str}\n"
                    f"Active Verified Links: {val_summary.valid_count}/{val_summary.total_links}\n"
                    f"{'='*50}\n\n"
                    + "\n".join(f"{'✅' if l.is_valid else '❌'} [{l.content_length_str:>10}]  {l.filename}" for l in val_summary.links)
                )
            if ctx.seg_val_label:
                ctx.seg_val_label.value = f"Validation & Size ({total_size_str})"
            ctx.log(f"Validation Complete: {val_summary.valid_count}/{val_summary.total_links} verified | Total Size: {total_size_str}")

        is_cancelled = bool(state.cancel_event and state.cancel_event.is_set())

        # Save to SQLite History ONLY if not cancelled and URLs were resolved
        if resolved_urls and not is_cancelled:
            ctx.history_mgr.add_record(
                title=state.last_game_title,
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
            ctx.set_status("Cancelled", icon=ft.Icons.CANCEL, color=ft.Colors.RED_400)
            if ctx.stats_text:
                ctx.stats_text.value = f"🛑 Extraction cancelled by user ({len(resolved_urls)}/{total_count} resolved)."
            if ctx.count_label:
                ctx.count_label.value = f"⚠️ Cancelled: {len(resolved_urls)}/{total_count} parts resolved"
            ctx.show_snack("Extraction cancelled by user.", success=False)
        else:
            ctx.set_status(f"Complete ({avg_s:.1f}s/part)", icon=ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400)
            if ctx.stats_text:
                ctx.stats_text.value = f"🚀 Completed in {total_elapsed:.1f}s | Avg Speed: {avg_s:.1f}s/part | Total Size: {total_size_str} | Success: {len(resolved_urls)}/{total_count}"
            if ctx.count_label:
                ctx.count_label.value = f"✨ {len(resolved_urls)} direct URLs ready ({total_size_str})"
            ctx.show_snack(f"All {len(resolved_urls)} direct URLs resolved successfully!")

    except Exception as ex:
        ctx.log(f"Pipeline error: {ex}")
        ctx.set_status("Error Occurred", icon=ft.Icons.ERROR, color=ft.Colors.RED_400)
    finally:
        finish_pipeline(ctx, state)


def start_pipeline(ctx: UIContext, state: AppState, e=None):
    if not ctx.url_input:
        return
    target = ctx.url_input.value.strip()
    if not target:
        ctx.show_snack("Please enter a valid FitGirl game page or pastebin URL.", success=False)
        return

    state.is_running = True
    state.cancel_event = threading.Event()
    if ctx.start_btn:
        ctx.start_btn.disabled = True
    if ctx.cancel_btn:
        ctx.cancel_btn.disabled = False
    if ctx.progress_bar:
        ctx.progress_bar.value = None
    ctx.set_status("Starting Engine...", icon=ft.Icons.AUTORENEW, color=ft.Colors.BLUE_400)
    ctx.page.update()

    threading.Thread(target=run_pipeline_thread, args=(ctx, state, target), daemon=True).start()


def cancel_pipeline(ctx: UIContext, state: AppState, e=None):
    if state.cancel_event:
        state.cancel_event.set()
    ctx.log("🛑 Cancellation requested by user.")
    ctx.set_status("Cancelling...", icon=ft.Icons.CANCEL, color=ft.Colors.AMBER_400)
    if ctx.cancel_btn:
        ctx.cancel_btn.disabled = True
    ctx.page.update()


def finish_pipeline(ctx: UIContext, state: AppState):
    state.is_running = False
    if ctx.start_btn:
        ctx.start_btn.disabled = False
    if ctx.cancel_btn:
        ctx.cancel_btn.disabled = True
    if ctx.progress_bar and ctx.progress_bar.value is None:
        ctx.progress_bar.value = 1.0
    ctx.page.update()
