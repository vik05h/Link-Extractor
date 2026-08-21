import asyncio
import threading
import time
from typing import Callable, Tuple, List, Dict, Any, Optional
import pyperclip
import flet as ft

import utils
import community
import integrations
import validator
from ui.state import UIContext, AppState
from ui.constants import FPS_PRESETS


# Pixel Dino 8-bit Frame Art for the Running Animation
DINO_FRAME_1 = """
        ████████
       ███▒▒████
       █████████
       █████
       █████████
 █    ███████
 ██  █████████
 ████████████
  ██████████
   █████████
    ██    ██
    ██    ██
"""

DINO_FRAME_2 = """
        ████████
       ███▒▒████
       █████████
       █████
       █████████
 █    ███████
 ██  █████████
 ████████████
  ██████████
   █████████
    ██   ███
    ██     █
"""


def create_pixel_dino_loader(seed_color: str) -> ft.Container:
    """Create an animated Pixel Dino loading banner."""
    dino_text = ft.Text(
        DINO_FRAME_1,
        font_family="Courier New",
        size=8,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.GREEN_ACCENT_400,
        text_align=ft.TextAlign.LEFT
    )

    ground_line = ft.Text(
        "═" * 44 + " 🌵 " + "═" * 12 + " 🌵🌵 " + "═" * 30,
        font_family="Courier New",
        size=11,
        color=ft.Colors.GREEN_800
    )

    loading_status = ft.Text(
        "PIXEL DINO IS HUNTING FRESH COMMUNITY REPACKS...",
        size=12,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.GREEN_ACCENT_400
    )

    sub_status = ft.Text(
        "Querying Firebase Realtime Database • Calculating Local Timezones",
        size=10,
        color=ft.Colors.ON_SURFACE_VARIANT
    )

    progress_indicator = ft.ProgressBar(width=320, color=ft.Colors.GREEN_ACCENT_400, border_radius=4)

    is_animating = True

    def _run_animation():
        frame = 0
        while is_animating:
            try:
                frame = (frame + 1) % 2
                dino_text.value = DINO_FRAME_2 if frame == 1 else DINO_FRAME_1
                dino_text.update()
            except Exception:
                break
            time.sleep(0.25)

    threading.Thread(target=_run_animation, daemon=True).start()

    return ft.Container(
        content=ft.Column([
            ft.Container(height=10),
            ft.Row([dino_text], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([ground_line], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=6),
            loading_status,
            sub_status,
            ft.Container(height=8),
            progress_indicator
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
        alignment=ft.Alignment.CENTER,
        padding=30,
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.SURFACE_CONTAINER_HIGHEST),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.35, ft.Colors.GREEN_ACCENT_400)),
        border_radius=16
    )


def show_game_details_modal(
    rec: Dict[str, Any],
    ctx: UIContext,
    state: AppState,
    seed_color: str,
    on_load_record: Callable[[Dict[str, Any]], None]
):
    """
    Display an interactive Game Details modal popup
    with full part list breakdown, 1-click batch actions, and direct URL copy.
    """
    title = rec.get("title", "FitGirl Repack")
    image_url = rec.get("image_url", "")
    total_parts = rec.get("total_parts", 0)
    total_size_str = rec.get("total_size_str", "0 B")
    local_time = rec.get("local_time", "Recently")
    slug = rec.get("slug", "")
    uploader = rec.get("uploader", "Community")
    age_str = rec.get("age_str", "Recently")
    freshness = rec.get("freshness", "fresh")

    fb_url = ctx.settings.get("community_firebase_url")
    urls = community.get_game_urls(slug, fb_url)

    def handle_modal_use_instant(e):
        ctx.page.pop_dialog()
        on_load_record(rec)

    def handle_modal_push_jd2(e):
        if not urls:
            ctx.show_snack("No direct URLs available to push.", success=False)
            return
        port = ctx.settings.get("jd_port", 9666)
        success, msg = integrations.push_to_jdownloader(urls, package_name=title, port=port)
        ctx.show_snack(msg, success=success)

    def handle_modal_copy_all(e):
        if not urls:
            ctx.show_snack("No direct URLs available to copy.", success=False)
            return
        pyperclip.copy("\n".join(urls))
        ctx.show_snack(f"Copied {len(urls)} direct download URLs to clipboard!")

    # Cover image
    cover_control = (
        ft.Image(src=image_url, width=90, height=120, fit=ft.BoxFit.COVER, border_radius=8)
        if image_url else
        ft.Container(
            content=ft.Icon(ft.Icons.FOLDER_ZIP_ROUNDED, size=40, color=seed_color),
            width=90, height=120, alignment=ft.Alignment.CENTER,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH, border_radius=8
        )
    )

    # Build Parts Breakdown List
    parts_list_items = []
    if urls:
        for idx, u in enumerate(urls, 1):
            clean_url = u.split("#")[0]
            filename = u.split("#")[-1] if "#" in u else f"Part {idx}"
            
            def make_copy_part_fn(target_url, p_num):
                return lambda _: (pyperclip.copy(target_url), ctx.show_snack(f"Copied Part {p_num} link!"))

            parts_list_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(f"#{idx:02d}", size=11, weight=ft.FontWeight.BOLD, color=seed_color),
                            width=36, alignment=ft.Alignment.CENTER,
                            bgcolor=ft.Colors.with_opacity(0.12, seed_color),
                            border_radius=6, padding=4
                        ),
                        ft.Column([
                            ft.Text(filename, size=11, weight=ft.FontWeight.W_500, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(clean_url, size=10, color=ft.Colors.ON_SURFACE_VARIANT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ], expand=True, spacing=1),
                        ft.IconButton(
                            icon=ft.Icons.COPY,
                            icon_size=14,
                            tooltip=f"Copy Part {idx}",
                            on_click=make_copy_part_fn(u, idx)
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
                    border_radius=8
                )
            )
    else:
        parts_list_items.append(
            ft.Text("Direct URLs will be loaded dynamically upon extraction.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
        )

    parts_scroll_view = ft.ListView(
        controls=parts_list_items,
        height=180,
        spacing=6,
        padding=4
    )

    modal_dialog = ft.AlertDialog(
        title=ft.Row([
            ft.Icon(ft.Icons.FOLDER_ZIP_ROUNDED, color=seed_color),
            ft.Text("Game Repack Inspector", size=16, weight=ft.FontWeight.BOLD)
        ], spacing=8),
        content=ft.Container(
            content=ft.Column([
                # Top Game Overview
                ft.Row([
                    cover_control,
                    ft.Column([
                        ft.Text(title, size=14, weight=ft.FontWeight.BOLD, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row([
                            ft.Icon(ft.Icons.ACCESS_TIME_FILLED, size=12, color=ft.Colors.PRIMARY),
                            ft.Text(f"Synced: {local_time}", size=11, color=ft.Colors.PRIMARY, weight=ft.FontWeight.W_500),
                        ], spacing=4),
                        ft.Row([
                            ft.Container(
                                content=ft.Text(f"{total_parts} Parts", size=11, weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE_VARIANT),
                                bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
                                border_radius=6, padding=ft.Padding.symmetric(horizontal=6, vertical=2)
                            ),
                            ft.Container(
                                content=ft.Text(f"{total_size_str}", size=11, weight=ft.FontWeight.BOLD, color=seed_color),
                                bgcolor=ft.Colors.with_opacity(0.14, seed_color),
                                border=ft.Border.all(0.8, ft.Colors.with_opacity(0.35, seed_color)),
                                border_radius=6, padding=ft.Padding.symmetric(horizontal=6, vertical=2)
                            ),
                            ft.Row([
                                ft.Icon(ft.Icons.PERSON_OUTLINE, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(f"By {uploader}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                            ], spacing=3)
                        ], spacing=6),
                        ft.Container(
                            content=ft.Text(f"STATUS: {freshness.upper()} ({age_str})", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400 if freshness == "fresh" else ft.Colors.AMBER_400),
                            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.GREEN_400 if freshness == "fresh" else ft.Colors.AMBER_400),
                            border_radius=6, padding=ft.Padding.symmetric(horizontal=6, vertical=2)
                        )
                    ], expand=True, spacing=4)
                ], spacing=12),
                ft.Divider(height=12),
                ft.Row([
                    ft.Text(f"Resolved Direct Parts ({len(urls)} URLs Available):", size=12, weight=ft.FontWeight.BOLD),
                    ft.TextButton("Copy All URLs", icon=ft.Icons.COPY_ALL, on_click=handle_modal_copy_all)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                parts_scroll_view
            ], tight=True, spacing=6),
            width=540
        ),
        actions=[
            ft.OutlinedButton("Close", on_click=lambda _: ctx.page.pop_dialog()),
            ft.FilledTonalButton("Push JD2", icon=ft.Icons.ROCKET_LAUNCH, on_click=handle_modal_push_jd2),
            ft.FilledButton("Load into Turbo Extractor", icon=ft.Icons.BOLT, on_click=handle_modal_use_instant)
        ]
    )

    ctx.page.show_dialog(modal_dialog)


def build_arcade_grid_card(
    rec: Dict[str, Any],
    ctx: UIContext,
    state: AppState,
    seed_color: str,
    on_load_record: Callable[[Dict[str, Any]], None],
    on_health_check_complete: Callable[[], None]
) -> ft.Card:
    """
    Build a clean Poster Card for Responsive Grid View.
    """
    title = rec.get("title", "FitGirl Repack")
    image_url = rec.get("image_url", "")
    total_parts = rec.get("total_parts", 0)
    total_size_str = rec.get("total_size_str", "0 B")
    local_time = rec.get("local_time", "Recently")
    age_str = rec.get("age_str", "Recently")
    freshness = rec.get("freshness", "fresh")
    slug = rec.get("slug", "")
    uploader = rec.get("uploader", "Community")

    # Freshness Badge Color & Icon
    if freshness == "fresh":
        badge_color = ft.Colors.GREEN_400
        badge_icon = ft.Icons.BOLT
        badge_label = f"Fresh ({age_str})"
    elif freshness == "aging":
        badge_color = ft.Colors.AMBER_400
        badge_icon = ft.Icons.SCHEDULE
        badge_label = f"Aging ({age_str})"
    else:
        badge_color = ft.Colors.DEEP_ORANGE_400
        badge_icon = ft.Icons.WARNING_AMBER
        badge_label = f"Expired ({age_str})"

    freshness_chip = ft.Container(
        content=ft.Row([
            ft.Icon(badge_icon, size=11, color=badge_color),
            ft.Text(badge_label, size=9, weight=ft.FontWeight.BOLD, color=badge_color)
        ], spacing=3, tight=True),
        bgcolor=ft.Colors.with_opacity(0.18, badge_color),
        border=ft.Border.all(0.8, ft.Colors.with_opacity(0.45, badge_color)),
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=6, vertical=3)
    )

    # Health Check Status Pill
    health_pill = ft.Text("", size=10, weight=ft.FontWeight.BOLD)

    # Cover Thumbnail Image with fallback
    if image_url:
        cover_img = ft.Image(
            src=image_url,
            width=320,
            height=150,
            fit=ft.BoxFit.COVER,
            border_radius=ft.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0),
            error_content=ft.Container(
                content=ft.Icon(ft.Icons.FOLDER_ZIP_ROUNDED, size=44, color=seed_color),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                width=320,
                height=150,
                alignment=ft.Alignment.CENTER,
                border_radius=ft.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0)
            )
        )
    else:
        cover_img = ft.Container(
            content=ft.Icon(ft.Icons.FOLDER_ZIP_ROUNDED, size=44, color=seed_color),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            width=320,
            height=150,
            alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0)
        )

    cover_frame = ft.Container(
        content=cover_img,
        border_radius=ft.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        animate_scale=ft.Animation(160, ft.AnimationCurve.FAST_OUT_SLOWIN),
        scale=1.0,
        on_click=lambda _: show_game_details_modal(rec, ctx, state, seed_color, on_load_record)
    )

    title_text = ft.Text(
        title,
        size=13,
        weight=ft.FontWeight.BOLD,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
        color=ft.Colors.ON_SURFACE
    )

    # Action Handlers
    def handle_use_instant(e):
        on_load_record(rec)

    def handle_push_jd2(e):
        urls = community.get_game_urls(slug, ctx.settings.get("community_firebase_url"))
        if not urls:
            ctx.show_snack(f"No URLs found for {title}", success=False)
            return
        port = ctx.settings.get("jd_port", 9666)
        success, msg = integrations.push_to_jdownloader(urls, package_name=title, port=port)
        ctx.show_snack(msg, success=success)

    def handle_copy_all(e):
        urls = community.get_game_urls(slug, ctx.settings.get("community_firebase_url"))
        if not urls:
            ctx.show_snack("No direct URLs available to copy.", success=False)
            return
        pyperclip.copy("\n".join(urls))
        ctx.show_snack(f"Copied {len(urls)} direct URLs for {title}!")

    def handle_health_check(e):
        health_pill.value = "Checking..."
        health_pill.color = ft.Colors.CYAN_400
        health_pill.tooltip = "Sending 1-byte HTTP Range verification request to Part 1..."
        health_pill.update()

        async def _check_worker():
            urls = community.get_game_urls(slug, ctx.settings.get("community_firebase_url"))
            if not urls:
                health_pill.value = "No URLs"
                health_pill.color = ft.Colors.RED_400
                health_pill.update()
                return

            is_alive, msg = await asyncio.to_thread(community.check_link_health, urls[0])
            if is_alive:
                health_pill.value = f"Part 1 Live ({msg})"
                health_pill.color = ft.Colors.GREEN_400
                health_pill.tooltip = f"Part 1 server verified alive ({msg}). Total repack: {total_size_str} ({total_parts} parts)"
            else:
                health_pill.value = f"Expired ({msg})"
                health_pill.color = ft.Colors.DEEP_ORANGE_400
                health_pill.tooltip = f"Link health check failed: {msg}"
            try:
                health_pill.update()
            except Exception:
                pass

        ctx.page.run_task(_check_worker)

    card = ft.Card(
        elevation=1,
        animate_scale=ft.Animation(160, ft.AnimationCurve.FAST_OUT_SLOWIN),
        scale=1.0
    )

    card_container = ft.Container(
        padding=0,
        border_radius=10,
        border=ft.Border.all(1.2, ft.Colors.TRANSPARENT),
        animate=ft.Animation(160, ft.AnimationCurve.FAST_OUT_SLOWIN),
        content=ft.Column([
            # Cover Poster Header
            cover_frame,
            # Card Body
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        freshness_chip,
                        health_pill
                    ], spacing=6, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(
                        content=title_text,
                        on_click=lambda _: show_game_details_modal(rec, ctx, state, seed_color, on_load_record),
                        tooltip="Click to inspect all parts in detail"
                    ),
                    ft.Row([
                        ft.Icon(ft.Icons.ACCESS_TIME_FILLED, size=11, color=ft.Colors.PRIMARY),
                        ft.Text(f"Synced: {local_time}", size=10, color=ft.Colors.PRIMARY, weight=ft.FontWeight.W_500, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=4),
                    ft.Row([
                        ft.Container(
                            content=ft.Text(f"{total_parts} Parts", size=10, weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE_VARIANT),
                            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
                            border_radius=6, padding=ft.Padding.symmetric(horizontal=6, vertical=2)
                        ),
                        ft.Container(
                            content=ft.Text(f"{total_size_str}", size=10, weight=ft.FontWeight.BOLD, color=seed_color),
                            bgcolor=ft.Colors.with_opacity(0.14, seed_color),
                            border=ft.Border.all(0.8, ft.Colors.with_opacity(0.35, seed_color)),
                            border_radius=6, padding=ft.Padding.symmetric(horizontal=6, vertical=2)
                        ),
                        ft.Row([
                            ft.Icon(ft.Icons.PERSON_OUTLINE, size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(f"{uploader}", size=10, color=ft.Colors.ON_SURFACE_VARIANT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ], spacing=2, tight=True)
                    ], spacing=4, alignment=ft.MainAxisAlignment.START),
                    ft.Divider(height=8),
                    # Action Bar
                    ft.Row([
                        ft.FilledButton(
                            "Use Instant",
                            icon=ft.Icons.BOLT,
                            height=32,
                            style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=10)),
                            on_click=handle_use_instant
                        ),
                        ft.Row([
                            ft.IconButton(icon=ft.Icons.ROCKET_LAUNCH, icon_size=16, tooltip="Push JD2", on_click=handle_push_jd2),
                            ft.IconButton(icon=ft.Icons.COPY, icon_size=16, tooltip="Copy URLs", on_click=handle_copy_all),
                            ft.IconButton(icon=ft.Icons.HEALTH_AND_SAFETY, icon_size=16, tooltip="1-Click Health Check", on_click=handle_health_check),
                        ], spacing=0)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                ], spacing=6),
                padding=12
            )
        ], spacing=0)
    )

    def handle_card_hover(e):
        is_hovered = e.data == "true" or e.data is True
        if is_hovered:
            card.elevation = 4
            card.scale = 1.015
            card_container.border = ft.Border.all(1.2, ft.Colors.with_opacity(0.65, seed_color))
            cover_frame.scale = 1.03
        else:
            card.elevation = 1
            card.scale = 1.0
            card_container.border = ft.Border.all(1.2, ft.Colors.TRANSPARENT)
            cover_frame.scale = 1.0

        try:
            card.update()
        except Exception:
            pass

    card_container.on_hover = handle_card_hover
    card.content = card_container
    return card


def build_3d_title_card(
    rec: Dict[str, Any],
    ctx: UIContext,
    state: AppState,
    seed_color: str,
    on_load_record: Callable[[Dict[str, Any]], None],
    on_health_check_complete: Callable[[], None]
) -> ft.Card:
    """
    Build a clean Feed Card with native Material 3 elevation and quick actions.
    """
    title = rec.get("title", "FitGirl Repack")
    image_url = rec.get("image_url", "")
    total_parts = rec.get("total_parts", 0)
    total_size_str = rec.get("total_size_str", "0 B")
    local_time = rec.get("local_time", "Recently")
    age_str = rec.get("age_str", "Recently")
    freshness = rec.get("freshness", "fresh")
    slug = rec.get("slug", "")
    uploader = rec.get("uploader", "Community")

    # Freshness Badge Color & Icon
    if freshness == "fresh":
        badge_color = ft.Colors.GREEN_400
        badge_icon = ft.Icons.BOLT
        badge_label = f"Fresh ({age_str})"
    elif freshness == "aging":
        badge_color = ft.Colors.AMBER_400
        badge_icon = ft.Icons.SCHEDULE
        badge_label = f"Aging ({age_str})"
    else:
        badge_color = ft.Colors.DEEP_ORANGE_400
        badge_icon = ft.Icons.WARNING_AMBER
        badge_label = f"Expired ({age_str})"

    freshness_chip = ft.Container(
        content=ft.Row([
            ft.Icon(badge_icon, size=12, color=badge_color),
            ft.Text(badge_label, size=10, weight=ft.FontWeight.BOLD, color=badge_color)
        ], spacing=4, tight=True),
        bgcolor=ft.Colors.with_opacity(0.15, badge_color),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.4, badge_color)),
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=8, vertical=4)
    )

    # Health Check Status Pill
    health_pill = ft.Text("", size=11, weight=ft.FontWeight.BOLD)

    # Cover Thumbnail Image with fallback
    if image_url:
        cover_img = ft.Image(
            src=image_url,
            width=90,
            height=115,
            fit=ft.BoxFit.COVER,
            border_radius=8,
            error_content=ft.Container(
                content=ft.Icon(ft.Icons.FOLDER_ZIP_ROUNDED, size=36, color=seed_color),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                width=90,
                height=115,
                alignment=ft.Alignment.CENTER,
                border_radius=8
            )
        )
    else:
        cover_img = ft.Container(
            content=ft.Icon(ft.Icons.FOLDER_ZIP_ROUNDED, size=36, color=seed_color),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            width=90,
            height=115,
            alignment=ft.Alignment.CENTER,
            border_radius=8
        )

    cover_frame = ft.Container(
        content=cover_img,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.PRIMARY)),
        border_radius=8,
        animate_scale=ft.Animation(160, ft.AnimationCurve.FAST_OUT_SLOWIN),
        scale=1.0,
        on_click=lambda _: show_game_details_modal(rec, ctx, state, seed_color, on_load_record)
    )

    title_accent_bar = ft.Container(
        width=3.5,
        height=20,
        border_radius=2,
        bgcolor=seed_color,
        animate=ft.Animation(160, ft.AnimationCurve.FAST_OUT_SLOWIN)
    )

    title_text = ft.Text(
        title,
        size=15,
        weight=ft.FontWeight.BOLD,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
        color=ft.Colors.ON_SURFACE
    )

    title_block = ft.Container(
        content=ft.Row([
            title_accent_bar,
            ft.Container(
                content=title_text,
                expand=True,
                padding=ft.Padding.only(left=2)
            )
        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding.only(bottom=2),
        on_click=lambda _: show_game_details_modal(rec, ctx, state, seed_color, on_load_record),
        tooltip="Click to inspect all parts in detail"
    )

    # Action Handlers
    def handle_use_instant(e):
        on_load_record(rec)

    def handle_push_jd2(e):
        urls = community.get_game_urls(slug, ctx.settings.get("community_firebase_url"))
        if not urls:
            ctx.show_snack(f"No URLs found for {title}", success=False)
            return
        port = ctx.settings.get("jd_port", 9666)
        success, msg = integrations.push_to_jdownloader(urls, package_name=title, port=port)
        ctx.show_snack(msg, success=success)

    def handle_copy_all(e):
        urls = community.get_game_urls(slug, ctx.settings.get("community_firebase_url"))
        if not urls:
            ctx.show_snack("No direct URLs available to copy.", success=False)
            return
        pyperclip.copy("\n".join(urls))
        ctx.show_snack(f"Copied {len(urls)} direct URLs for {title}!")

    def handle_health_check(e):
        health_pill.value = "Checking..."
        health_pill.color = ft.Colors.CYAN_400
        health_pill.tooltip = "Sending 1-byte HTTP Range verification request to Part 1..."
        health_pill.update()

        async def _check_worker():
            urls = community.get_game_urls(slug, ctx.settings.get("community_firebase_url"))
            if not urls:
                health_pill.value = "No URLs"
                health_pill.color = ft.Colors.RED_400
                health_pill.update()
                return

            is_alive, msg = await asyncio.to_thread(community.check_link_health, urls[0])
            if is_alive:
                health_pill.value = f"Part 1 Live ({msg})"
                health_pill.color = ft.Colors.GREEN_400
                health_pill.tooltip = f"Part 1 server verified alive ({msg}). Total repack: {total_size_str} ({total_parts} parts)"
            else:
                health_pill.value = f"Expired ({msg})"
                health_pill.color = ft.Colors.DEEP_ORANGE_400
                health_pill.tooltip = f"Link health check failed: {msg}"
            try:
                health_pill.update()
            except Exception:
                pass

        ctx.page.run_task(_check_worker)

    card = ft.Card(
        elevation=1,
        animate_scale=ft.Animation(160, ft.AnimationCurve.FAST_OUT_SLOWIN),
        scale=1.0
    )

    card_container = ft.Container(
        padding=14,
        border_radius=10,
        border=ft.Border.all(1.2, ft.Colors.TRANSPARENT),
        animate=ft.Animation(160, ft.AnimationCurve.FAST_OUT_SLOWIN),
        content=ft.Row([
            # Left: Poster Artwork Frame
            cover_frame,
            # Middle: Game Info & Title
            ft.Column([
                ft.Row([
                    freshness_chip,
                    health_pill
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                title_block,
                ft.Row([
                    ft.Icon(ft.Icons.ACCESS_TIME_FILLED, size=12, color=ft.Colors.PRIMARY),
                    ft.Text(
                        f"Synced: {local_time}",
                        size=11,
                        color=ft.Colors.PRIMARY,
                        weight=ft.FontWeight.W_500
                    ),
                ], spacing=4, tight=True),
                ft.Row([
                    ft.Container(
                        content=ft.Text(f"{total_parts} Parts", size=11, weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE_VARIANT),
                        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
                        border_radius=6,
                        padding=ft.Padding.symmetric(horizontal=6, vertical=2)
                    ),
                    ft.Container(
                        content=ft.Text(f"{total_size_str}", size=11, weight=ft.FontWeight.BOLD, color=seed_color),
                        bgcolor=ft.Colors.with_opacity(0.14, seed_color),
                        border=ft.Border.all(0.8, ft.Colors.with_opacity(0.35, seed_color)),
                        border_radius=6,
                        padding=ft.Padding.symmetric(horizontal=6, vertical=2)
                    ),
                    ft.Row([
                        ft.Icon(ft.Icons.PERSON_OUTLINE, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(f"By {uploader}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                    ], spacing=3, tight=True)
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ], expand=True, spacing=4),
            # Right: Quick Action Hub
            ft.Column([
                ft.FilledButton(
                    "Use Instant",
                    icon=ft.Icons.BOLT,
                    height=36,
                    on_click=handle_use_instant
                ),
                ft.Row([
                    ft.FilledTonalButton(
                        "Push JD2",
                        icon=ft.Icons.ROCKET_LAUNCH,
                        height=32,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8)
                        ),
                        on_click=handle_push_jd2
                    ),
                    ft.IconButton(
                        icon=ft.Icons.COPY,
                        icon_size=16,
                        tooltip="Copy Direct URLs",
                        on_click=handle_copy_all
                    ),
                    ft.IconButton(
                        icon=ft.Icons.HEALTH_AND_SAFETY,
                        icon_size=16,
                        tooltip="1-Click Health Check",
                        on_click=handle_health_check
                    ),
                ], spacing=4)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.END, spacing=6)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=14)
    )

    def handle_card_hover(e):
        is_hovered = e.data == "true" or e.data is True
        if is_hovered:
            card.elevation = 4
            card.scale = 1.01
            card_container.border = ft.Border.all(1.2, ft.Colors.with_opacity(0.65, seed_color))
            cover_frame.scale = 1.04
            title_accent_bar.width = 4.5
        else:
            card.elevation = 1
            card.scale = 1.0
            card_container.border = ft.Border.all(1.2, ft.Colors.TRANSPARENT)
            cover_frame.scale = 1.0
            title_accent_bar.width = 3.5

        try:
            card.update()
        except Exception:
            pass

    card_container.on_hover = handle_card_hover
    card.content = card_container
    return card


def build_community_screen(
    ctx: UIContext,
    state: AppState,
    seed_color: str,
    on_load_record_into_extractor: Callable[[Dict[str, Any]], None]
) -> Tuple[ft.Container, Callable[[], None]]:
    """
    Build Clean Community Hub screen with Grid/List view switcher,
    dynamic live theme color updates, search, and filter chips.
    """
    current_view_mode = [ctx.settings.get("community_view_mode", "grid")]
    active_seed = [seed_color]

    cards_list = ft.ListView(expand=True, spacing=10, padding=12)
    search_input = ft.TextField(
        hint_text="Search community repacks...",
        prefix_icon=ft.Icons.SEARCH,
        dense=True,
        width=260,
        border_radius=8
    )

    current_filter = ["all"]

    def apply_filter_and_render(games: List[Dict[str, Any]], query: str = "", filter_tag: str = "all"):
        cards_list.controls.clear()
        q = query.lower().strip()
        cur_seed = active_seed[0]

        filtered = []
        for g in games:
            t = g.get("title", "").lower()
            s = g.get("slug", "").lower()
            fresh = g.get("freshness", "fresh")

            if q and (q not in t and q not in s):
                continue

            if filter_tag == "fresh" and fresh != "fresh":
                continue
            elif filter_tag == "aging" and fresh != "aging":
                continue
            elif filter_tag == "expired" and fresh != "expired":
                continue

            filtered.append(g)

        if not filtered:
            cards_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.CLOUD_OFF, size=48, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text("No community repacks match your filter.", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text("Try changing your search terms or extract a new game to share with the community!", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                    alignment=ft.Alignment.CENTER,
                    padding=40
                )
            )
        else:
            if current_view_mode[0] == "grid":
                # Render responsive multi-column poster grid
                grid_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
                for g in filtered:
                    card_elem = build_arcade_grid_card(
                        rec=g,
                        ctx=ctx,
                        state=state,
                        seed_color=cur_seed,
                        on_load_record=on_load_record_into_extractor,
                        on_health_check_complete=lambda: ctx.page.update()
                    )
                    grid_row.controls.append(
                        ft.Container(content=card_elem, col={"sm": 12, "md": 6, "lg": 4})
                    )
                cards_list.controls.append(grid_row)
            else:
                # Render horizontal feed list
                for g in filtered:
                    cards_list.controls.append(
                        build_3d_title_card(
                            rec=g,
                            ctx=ctx,
                            state=state,
                            seed_color=cur_seed,
                            on_load_record=on_load_record_into_extractor,
                            on_health_check_complete=lambda: ctx.page.update()
                        )
                    )

        try:
            cards_list.update()
        except Exception:
            ctx.page.update()

    def refresh_community():
        """Trigger Pixel Dino loading animation and fetch fresh records from Firebase."""
        cards_list.controls.clear()
        cards_list.controls.append(create_pixel_dino_loader(active_seed[0]))
        try:
            cards_list.update()
        except Exception:
            ctx.page.update()

        async def _fetch_worker():
            fb_url = ctx.settings.get("community_firebase_url")
            games = await asyncio.to_thread(community.get_community_games, fb_url)
            state.community_games = games
            await asyncio.sleep(0.4)
            selected_filt = current_filter[0] if current_filter else "all"
            apply_filter_and_render(games, search_input.value or "", selected_filt)

        ctx.page.run_task(_fetch_worker)

    ctx.refresh_community_cb = refresh_community

    def on_filter_change(e):
        if not e.control.selected:
            return
        val = list(e.control.selected)[0]
        current_filter[0] = val
        apply_filter_and_render(state.community_games, search_input.value or "", val)

    filter_segments = ft.SegmentedButton(
        selected=["all"],
        allow_multiple_selection=False,
        on_change=on_filter_change,
        segments=[
            ft.Segment(value="all", label=ft.Text("All Repacks"), icon=ft.Icon(ft.Icons.ALL_INCLUSIVE)),
            ft.Segment(value="fresh", label=ft.Text("Fresh (<12h)"), icon=ft.Icon(ft.Icons.BOLT)),
            ft.Segment(value="aging", label=ft.Text("Aging (12-36h)"), icon=ft.Icon(ft.Icons.SCHEDULE)),
            ft.Segment(value="expired", label=ft.Text("Expired"), icon=ft.Icon(ft.Icons.WARNING_AMBER)),
        ]
    )

    def on_view_mode_changed(e):
        if not e.control.selected:
            return
        mode = list(e.control.selected)[0]
        current_view_mode[0] = mode
        ctx.settings["community_view_mode"] = mode
        utils.save_settings(ctx.settings)
        selected_filt = current_filter[0] if current_filter else "all"
        apply_filter_and_render(state.community_games, search_input.value or "", selected_filt)

    view_mode_segmented = ft.SegmentedButton(
        selected=[current_view_mode[0]],
        allow_multiple_selection=False,
        on_change=on_view_mode_changed,
        segments=[
            ft.Segment(value="grid", label=ft.Text("Grid"), icon=ft.Icon(ft.Icons.GRID_VIEW_ROUNDED)),
            ft.Segment(value="list", label=ft.Text("List"), icon=ft.Icon(ft.Icons.VIEW_LIST_ROUNDED)),
        ]
    )

    search_input.on_change = lambda e: apply_filter_and_render(state.community_games, search_input.value or "", current_filter[0])

    top_banner_container = ft.Container(
        content=ft.Row([
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.CLOUD_DOWNLOAD_ROUNDED, size=24, color=seed_color),
                    ft.Text("FitGirl Community Cloud Cache", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Text("🌐 LIVE HUB", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.GREEN_700,
                        border_radius=10,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=2)
                    )
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                ft.Text(
                    "Instant decentralized link sharing. Download games already resolved by others without waiting for browser decryption.",
                    size=11, color=ft.Colors.ON_SURFACE_VARIANT
                )
            ], expand=True, spacing=4),
            ft.Row([
                search_input,
                ft.FilledTonalButton(
                    "Refresh Feed",
                    icon=ft.Icons.REFRESH,
                    on_click=lambda _: refresh_community()
                )
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=16,
        border_radius=12
    )
    ctx.tour_targets["community_banner"] = top_banner_container

    top_banner_card = ft.Card(
        content=top_banner_container
    )

    feed_card = ft.Card(
        content=ft.Container(
            content=cards_list,
            expand=True,
            padding=6
        ),
        expand=True
    )

    community_screen = ft.Container(
        key="screen_community",
        content=ft.Column([
            top_banner_card,
            ft.Row([
                filter_segments,
                view_mode_segmented
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            feed_card
        ], spacing=10, expand=True),
        padding=16,
        expand=True
    )

    # Dynamic Live Theme Listener
    def on_theme_seed_updated(new_seed: str):
        active_seed[0] = new_seed
        selected_filt = current_filter[0] if current_filter else "all"
        apply_filter_and_render(state.community_games, search_input.value or "", selected_filt)
        try:
            community_screen.update()
        except Exception:
            pass

    ctx.register_theme_listener(on_theme_seed_updated)

    return community_screen, refresh_community
