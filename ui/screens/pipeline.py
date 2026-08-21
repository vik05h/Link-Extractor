import re
import time
import asyncio
import threading
from typing import List, Dict, Any, Optional
import pyperclip
import flet as ft

import scraper
import community
from engine import ResolutionEngine, detect_browser_channel
import validator
from ui.state import UIContext, AppState


# Row state model: list of dicts tracking each part's current display state
_row_states = []


def _build_status_chip(rs):
    """Build a Chip control from a row state dict."""
    return ft.Chip(
        label=ft.Text(rs["status_label"], size=10, color=rs.get("status_color")),
        leading=ft.Icon(rs["status_icon"], size=12, color=rs.get("status_color"))
    )


def _build_action_cell(rs, ctx):
    """Build the action cell (copy button) from row state."""
    if rs["status"] == "resolved" and rs.get("direct_url"):
        url = rs["direct_url"]
        return ft.IconButton(
            icon=ft.Icons.COPY,
            icon_size=16,
            tooltip="Copy Link",
            on_click=lambda _, u=url: (pyperclip.copy(u), ctx.show_snack("Copied direct link!"))
        )
    return ft.IconButton(icon=ft.Icons.COPY, icon_size=16, tooltip="Copy Link", disabled=True)


def rebuild_table(ctx):
    """Clear and rebuild data_table.rows from _row_states, then push update."""
    if not ctx.data_table:
        return
    ctx.data_table.rows.clear()
    for rs in _row_states:
        ctx.data_table.rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(rs["index"] + 1))),
                    ft.DataCell(ft.Text(rs["name"], size=12)),
                    ft.DataCell(ft.Text(rs["size_str"], size=12, color=ft.Colors.ON_SURFACE_VARIANT,
                                        weight=ft.FontWeight.W_500 if rs["size_str"] != "--" else None)),
                    ft.DataCell(_build_status_chip(rs)),
                    ft.DataCell(_build_action_cell(rs, ctx))
                ]
            )
        )
    ctx.refresh_extractor_ui()


def load_community_record_into_extractor(ctx: UIContext, state: AppState, record: Dict[str, Any]):
    """
    Instantly inject community cloud record into Extractor UI without browser automation.
    """
    global _row_states
    slug = record.get("slug", "")
    title = record.get("title", "FitGirl Repack")
    urls = community.get_game_urls(slug, ctx.settings.get("community_firebase_url"))
    if not urls:
        ctx.show_snack(f"Could not load URLs for {title}.", success=False)
        return

    state.resolved_links = urls
    state.last_game_title = title
    state.last_cover_image = record.get("image_url", "")
    total_count = len(urls)
    total_size_str = record.get("total_size_str", "0 B")
    local_time = record.get("local_time", "Recently")

    if ctx.url_input:
        ctx.url_input.value = record.get("source_url", f"https://fitgirl-repacks.site/{slug}/")

    # Rebuild rows as resolved
    _row_states = []
    for i, u in enumerate(urls):
        p_name = u.split("#")[-1] if "#" in u else f"part_{i+1:02d}.rar"
        _row_states.append({
            "index": i,
            "name": p_name,
            "size_str": "--",
            "status": "resolved",
            "status_label": "Cloud Instant",
            "status_color": ft.Colors.GREEN_400,
            "status_icon": ft.Icons.BOLT,
            "direct_url": u
        })

    rebuild_table(ctx)

    if ctx.progress_bar:
        ctx.progress_bar.value = 1.0

    ctx.set_status("Loaded from Community Cloud", icon=ft.Icons.BOLT, color=ft.Colors.GREEN_400)
    if ctx.stats_text:
        ctx.stats_text.value = f"⚡ Instant Community Cache | 📦 {total_count} Parts | 💾 {total_size_str} | 📅 Synced: {local_time}"
    if ctx.count_label:
        ctx.count_label.value = f"✨ {total_count} direct URLs ready from Community Hub ({total_size_str})"
    if ctx.seg_urls_label:
        ctx.seg_urls_label.value = f"Direct URLs ({total_count}/{total_count})"
    if ctx.seg_val_label:
        ctx.seg_val_label.value = f"Validation & Size ({total_size_str})"

    if ctx.val_text:
        ctx.val_text.value = (
            f"=== COMMUNITY CLOUD DOWNLOAD RECORD ===\n"
            f"Game: {title}\n"
            f"Source: {record.get('source_url', 'FitGirl Repacks')}\n"
            f"Total Repack Size: {total_size_str}\n"
            f"Cached Local Time: {local_time}\n"
            f"Community Uploader: {record.get('uploader', 'Community')}\n"
            f"{'='*50}\n\n"
            + "\n".join(f"⚡ [  INSTANT ]  {u.split('#')[-1] if '#' in u else u}" for u in urls)
        )

    # Save to local SQLite History database
    try:
        ctx.history_mgr.add_record(
            title=title,
            source_url=record.get("source_url", ""),
            total_parts=total_count,
            resolved_count=total_count,
            total_size_bytes=record.get("total_size_bytes", 0),
            total_size_str=total_size_str,
            urls=urls
        )
    except Exception:
        pass

    ctx.navigate_to_screen(0)
    ctx.show_snack(f"✨ Loaded {total_count} links for '{title}' instantly from Community Hub!")


async def run_pipeline_async(ctx: UIContext, state: AppState, target_url: str):
    global _row_states
    t_start = time.time()
    cover_image_url = ""
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
            pastebins, game_title, cover_image_url = await asyncio.to_thread(scraper.extract_game_page_pastebins, target_url)
            state.last_game_title = game_title or "FitGirl Repack"
            state.last_cover_image = cover_image_url
            ctx.log(f"Game Repack: {state.last_game_title}")

            ff_pastebins = [p for p in pastebins if p["hoster"] == "FuckingFast"] or (pastebins[:1] if pastebins else [])
            if not ff_pastebins:
                ctx.log("ERROR: No pastebin mirrors found.")
                ctx.set_status("No Mirrors Found", icon=ft.Icons.ERROR, color=ft.Colors.RED_400)
                finish_pipeline(ctx, state)
                return

            target_pastebin = ff_pastebins[0]["url"]
            ctx.set_status("Decrypting Pastebin...", icon=ft.Icons.LOCK_OPEN, color=ft.Colors.AMBER_400)
            state.pastebin_links = await engine.fetch_pastebin_links(target_pastebin, log_cb=ctx.log)
        else:
            ctx.set_status("Decrypting Pastebin...", icon=ft.Icons.LOCK_OPEN, color=ft.Colors.AMBER_400)
            state.pastebin_links = await engine.fetch_pastebin_links(target_url, log_cb=ctx.log)
            state.last_game_title = "FitGirl Pastebin Download"

        total_count = len(state.pastebin_links)
        ctx.log(f"Phase 1 complete: extracted {total_count} game parts")

        if total_count == 0:
            ctx.set_status("No Links Found", icon=ft.Icons.ERROR, color=ft.Colors.RED_400)
            finish_pipeline(ctx, state)
            return

        # Initialize row state model
        _row_states = []
        for i, u in enumerate(state.pastebin_links):
            p_name = u.split("#")[-1] if "#" in u else f"part_{i+1:02d}"
            _row_states.append({
                "index": i,
                "name": p_name,
                "size_str": "--",
                "status": "pending",
                "status_label": "Pending",
                "status_color": None,
                "status_icon": ft.Icons.HOURGLASS_EMPTY,
                "direct_url": None
            })
        rebuild_table(ctx)

        def on_start_part(part_name, worker_id):
            for rs in _row_states:
                if rs["name"] == part_name:
                    rs["status"] = "resolving"
                    rs["status_label"] = f"Resolving (Tab {worker_id})"
                    rs["status_color"] = ft.Colors.BLUE_400
                    rs["status_icon"] = ft.Icons.SYNC
                    break
            rebuild_table(ctx)

        def on_progress(done_count, total, avg_speed, eta, active_tabs, part_name, direct_url, status):
            frac = done_count / max(1, total)
            if ctx.progress_bar:
                ctx.progress_bar.value = frac
            ctx.set_status(f"Resolved {done_count}/{total} ({active_tabs} Active)", icon=ft.Icons.AUTORENEW, color=ft.Colors.BLUE_400)
            eta_str = f"{int(eta)}s" if eta < 60 else f"{int(eta // 60)}m {int(eta % 60)}s"
            if ctx.stats_text:
                ctx.stats_text.value = f"⚡ Speed: {avg_speed:.1f}s/part | ⏱️ ETA: ~{eta_str} | 🌐 {active_tabs} tabs active"

            # Update row state
            for rs in _row_states:
                if rs["name"] == part_name:
                    if status == "resolved" and direct_url:
                        rs["status"] = "resolved"
                        rs["status_label"] = "Resolved"
                        rs["status_color"] = ft.Colors.GREEN_400
                        rs["status_icon"] = ft.Icons.CHECK_CIRCLE
                        rs["direct_url"] = direct_url
                    else:
                        rs["status"] = "failed"
                        rs["status_label"] = "Failed"
                        rs["status_color"] = ft.Colors.RED_400
                        rs["status_icon"] = ft.Icons.ERROR
                    break

            if ctx.seg_urls_label:
                ctx.seg_urls_label.value = f"Direct URLs ({done_count}/{total})"
            rebuild_table(ctx)

        def on_retry_pass(failed_cnt, cur_att, max_att):
            ctx.set_status(f"Retrying {failed_cnt} links (Pass {cur_att}/{max_att})", icon=ft.Icons.REFRESH, color=ft.Colors.AMBER_400)
            for rs in _row_states:
                if rs["status"] == "failed":
                    rs["status"] = "queued"
                    rs["status_label"] = f"Queue (Pass {cur_att})"
                    rs["status_color"] = ft.Colors.AMBER_400
                    rs["status_icon"] = ft.Icons.SCHEDULE
            rebuild_table(ctx)

        results = await engine.resolve_all_async(
            urls=state.pastebin_links,
            on_progress=on_progress,
            on_log=ctx.log,
            on_retry_pass=on_retry_pass,
            on_start_part=on_start_part,
            cancel_event=state.cancel_event
        )

        resolved_urls = [r.direct_url for r in results if r.direct_url]
        state.resolved_links = resolved_urls

        # Phase 3: Link Validation
        total_size_str = "0 B"
        total_size_bytes = 0

        if ctx.settings.get("auto_validate", True) and resolved_urls and not (state.cancel_event and state.cancel_event.is_set()):
            ctx.set_status("Validating Links & Size...", icon=ft.Icons.CHECKLIST, color=ft.Colors.CYAN_400)
            ctx.log(f"Phase 3: Validating {len(resolved_urls)} direct URLs & computing exact download sizes...")

            val_summary = await asyncio.to_thread(validator.validate_links, resolved_urls, 15, None, state.cancel_event)
            state.last_val_summary = val_summary
            total_size_str = val_summary.total_size_str
            total_size_bytes = val_summary.total_bytes

            # Update row sizes in state
            for vl in val_summary.links:
                for rs in _row_states:
                    if vl.filename in rs["name"] or rs["name"] in vl.filename:
                        rs["size_str"] = vl.content_length_str

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
            rebuild_table(ctx)

        is_cancelled = bool(state.cancel_event and state.cancel_event.is_set())

        # Save to SQLite History ONLY if not cancelled and URLs were resolved
        if resolved_urls and not is_cancelled:
            await asyncio.to_thread(
                ctx.history_mgr.add_record,
                title=state.last_game_title,
                source_url=target_url,
                total_parts=total_count,
                resolved_count=len(resolved_urls),
                total_size_bytes=total_size_bytes,
                total_size_str=total_size_str,
                urls=resolved_urls
            )

            # Auto-upload to Community Cloud Cache if enabled in settings
            if ctx.settings.get("community_auto_share", True):
                try:
                    game_slug = scraper.extract_game_slug(target_url, state.last_game_title)
                    fb_url = ctx.settings.get("community_firebase_url")
                    ok, upload_msg = await asyncio.to_thread(
                        community.upload_game_record,
                        slug=game_slug,
                        title=state.last_game_title,
                        source_url=target_url,
                        image_url=cover_image_url or state.last_cover_image,
                        urls=resolved_urls,
                        total_parts=total_count,
                        total_size_str=total_size_str,
                        total_size_bytes=total_size_bytes,
                        firebase_url=fb_url
                    )
                    if ok:
                        ctx.log(f"Community Hub: {upload_msg}")
                except Exception as ex_up:
                    ctx.log(f"Community upload error (silent): {ex_up}")

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
    try:
        ctx.page.window.to_front()
    except Exception:
        pass
    ctx.refresh_extractor_ui()

    ctx.page.run_task(run_pipeline_async, ctx, state, target)


def cancel_pipeline(ctx: UIContext, state: AppState, e=None):
    if state.cancel_event:
        state.cancel_event.set()
    ctx.log("🛑 Cancellation requested by user.")
    ctx.set_status("Cancelling...", icon=ft.Icons.CANCEL, color=ft.Colors.AMBER_400)
    if ctx.cancel_btn:
        ctx.cancel_btn.disabled = True
    ctx.refresh_extractor_ui()


def finish_pipeline(ctx: UIContext, state: AppState):
    state.is_running = False
    if ctx.start_btn:
        ctx.start_btn.disabled = False
    if ctx.cancel_btn:
        ctx.cancel_btn.disabled = True
    if ctx.progress_bar and ctx.progress_bar.value is None:
        ctx.progress_bar.value = 1.0
    ctx.refresh_extractor_ui()
