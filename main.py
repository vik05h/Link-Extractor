import os
import sys
import flet as ft

# Ensure Playwright browser cache location
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "ms-playwright"
)

import utils
import updater
from history import HistoryManager
from ui.constants import THEME_PRESETS, LOGO_PRESETS, ANIMATION_PRESETS
from ui.state import AppState, UIContext
from ui.screens.extractor import build_extractor_screen
from ui.screens.history import build_history_screen
from ui.screens.settings import build_settings_screen


def main(page: ft.Page):
    utils.apply_windows_native_icon("app_icon.ico")

    page.title = f"FitGirl Direct Link Extractor {updater.CURRENT_VERSION} — Flutter High Speed Edition"
    page.window.width = 1180
    page.window.height = 840
    page.window.min_width = 960
    page.window.min_height = 680
    page.padding = 0

    settings = utils.load_settings()
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
    abs_logo_path = utils.get_resource_path(active_logo_rel)
    page.window.icon = abs_logo_path

    rail_logo = ft.Image(src=abs_logo_path, width=38, height=38, border_radius=8, fit=ft.BoxFit.CONTAIN)
    banner_logo = ft.Image(src=abs_logo_path, width=30, height=30, border_radius=6, fit=ft.BoxFit.CONTAIN)

    # Runtime state and context
    state = AppState()
    ctx = UIContext(page, settings, history_mgr)
    ctx.rail_logo = rail_logo
    ctx.banner_logo = banner_logo

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

    # Build modular screens
    extractor_screen = build_extractor_screen(ctx, state, seed_color)
    history_screen, refresh_history = build_history_screen(ctx, state, seed_color)
    settings_screen = build_settings_screen(
        ctx=ctx,
        state=state,
        seed_color=seed_color,
        get_screens=lambda: screens,
        get_screen_holder=lambda: screen_holder,
        create_screen_switcher=create_screen_switcher
    )

    screens = [extractor_screen, history_screen, settings_screen]

    # Main layout with NavigationRail and Screen Switcher
    active_anim_name = settings.get("animation_style", "Fast Subtle Fade")
    anim_cfg = ANIMATION_PRESETS.get(active_anim_name, ANIMATION_PRESETS["Fast Subtle Fade"])

    screen_holder = ft.Container(
        content=create_screen_switcher(anim_cfg, extractor_screen),
        expand=True
    )

    def on_nav_change(e):
        idx = e.control.selected_index
        state.active_screen = idx
        if idx == 0:
            ctx.update_stats_display(state.is_running)
        elif idx == 1:
            refresh_history()

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
                on_click=ctx.show_update_dialog
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
