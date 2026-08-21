import asyncio
import threading
import time
from typing import Callable, Tuple, List, Dict, Any, Optional
import pyperclip
import flet as ft

import community
import integrations
import validator
from ui.state import UIContext, AppState


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
    """Create an animated retro 8-bit arcade Pixel Dino loading banner."""
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
        bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.SURFACE_CONTAINER_HIGHEST),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.GREEN_ACCENT_400)),
        border_radius=16
    )


def build_3d_title_card(
    rec: Dict[str, Any],
    ctx: UIContext,
    state: AppState,
    seed_color: str,
    on_load_record: Callable[[Dict[str, Any]], None],
    on_health_check_complete: Callable[[], None]
) -> ft.Card:
    """
    Build a rich 3D-styled Game Card with thumbnail, depth lighting,
    freshness indicators, local time formatting, and 4 quick actions.
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
        bgcolor=ft.Colors.with_opacity(0.18, badge_color),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.5, badge_color)),
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
                content=ft.Icon(ft.Icons.SPORTS_ESPORTS, size=36, color=ft.Colors.PRIMARY),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                width=90,
                height=115,
                alignment=ft.Alignment.CENTER,
                border_radius=8
            )
        )
    else:
        cover_img = ft.Container(
            content=ft.Icon(ft.Icons.SPORTS_ESPORTS, size=36, color=ft.Colors.PRIMARY),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            width=90,
            height=115,
            alignment=ft.Alignment.CENTER,
            border_radius=8
        )

    # 3D Title with Layered Depth Style
    title_widget = ft.Container(
        content=ft.Text(
            title,
            size=15,
            weight=ft.FontWeight.BOLD,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
            color=ft.Colors.ON_SURFACE
        ),
        padding=ft.Padding.only(bottom=2)
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
                health_pill.value = f"Active ({msg})"
                health_pill.color = ft.Colors.GREEN_400
            else:
                health_pill.value = f"Expired ({msg})"
                health_pill.color = ft.Colors.DEEP_ORANGE_400
            try:
                health_pill.update()
            except Exception:
                pass

        ctx.page.run_task(_check_worker)

    return ft.Card(
        content=ft.Container(
            content=ft.Row([
                # Left: Game Cover Thumbnail
                ft.Container(
                    content=cover_img,
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.PRIMARY)),
                    border_radius=10,
                    padding=2
                ),
                # Middle: Game Info & 3D Title
                ft.Column([
                    ft.Row([
                        freshness_chip,
                        health_pill
                    ], spacing=8),
                    title_widget,
                    ft.Text(
                        f"Local Time: {local_time}",
                        size=11,
                        color=ft.Colors.PRIMARY,
                        weight=ft.FontWeight.W_500
                    ),
                    ft.Row([
                        ft.Text(f"{total_parts} Parts", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text("•", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(f"{total_size_str}", size=11, weight=ft.FontWeight.BOLD, color=seed_color),
                        ft.Text("•", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(f"By {uploader}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                    ], spacing=6)
                ], expand=True, spacing=4),
                # Right: 4 Quick Actions
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
                            on_click=handle_push_jd2
                        ),
                        ft.IconButton(
                            icon=ft.Icons.COPY,
                            icon_size=16,
                            tooltip="Copy URLs",
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
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=14
        ),
        elevation=2
    )


def build_community_screen(
    ctx: UIContext,
    state: AppState,
    seed_color: str,
    on_load_record_into_extractor: Callable[[Dict[str, Any]], None]
) -> Tuple[ft.Container, Callable[[], None]]:
    """
    Build Phase 3 Community Hub screen with Pixel Dino loading animation,
    3D game cards, live search, and filter chips.
    """
    cards_list = ft.ListView(expand=True, spacing=10, padding=12)
    search_input = ft.TextField(
        hint_text="Search community repacks...",
        prefix_icon=ft.Icons.SEARCH,
        dense=True,
        width=280,
        border_radius=8
    )

    current_filter = ["all"]

    def apply_filter_and_render(games: List[Dict[str, Any]], query: str = "", filter_tag: str = "all"):
        cards_list.controls.clear()
        q = query.lower().strip()

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
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.Alignment.CENTER,
                    padding=40
                )
            )
        else:
            for g in filtered:
                cards_list.controls.append(
                    build_3d_title_card(
                        rec=g,
                        ctx=ctx,
                        state=state,
                        seed_color=seed_color,
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
        cards_list.controls.append(create_pixel_dino_loader(seed_color))
        try:
            cards_list.update()
        except Exception:
            ctx.page.update()

        async def _fetch_worker():
            fb_url = ctx.settings.get("community_firebase_url")
            games = await asyncio.to_thread(community.get_community_games, fb_url)
            state.community_games = games
            await asyncio.sleep(0.4)  # Ensure Dino animation displays smoothly
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

    search_input.on_change = lambda e: apply_filter_and_render(state.community_games, search_input.value or "", current_filter[0])

    community_screen = ft.Container(
        key="screen_community",
        content=ft.Column([
            # Top Banner Card
            ft.Card(
                content=ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.GROUPS, size=24, color=seed_color),
                                ft.Text("FitGirl Community Cloud Cache", size=18, weight=ft.FontWeight.BOLD),
                                ft.Container(
                                    content=ft.Text("🌐 LIVE HUB", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                    bgcolor=ft.Colors.GREEN_700,
                                    border_radius=10,
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=2)
                                )
                            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
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
                        ], spacing=8)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=16
                )
            ),
            # Filter Tabs
            ft.Row([filter_segments], alignment=ft.MainAxisAlignment.START),
            # Community Feed Card
            ft.Card(
                content=ft.Container(
                    content=cards_list,
                    expand=True,
                    padding=6
                ),
                expand=True
            )
        ], spacing=10, expand=True),
        padding=16,
        expand=True
    )

    return community_screen, refresh_community
