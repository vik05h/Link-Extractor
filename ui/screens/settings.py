from typing import Callable, List
import flet as ft

import utils
import integrations
import updater
import community
from ui.constants import THEME_PRESETS, LOGO_PRESETS, ANIMATION_PRESETS, FPS_PRESETS
from ui.state import UIContext, AppState


def build_settings_screen(
    ctx: UIContext,
    state: AppState,
    seed_color: str,
    get_screens: Callable[[], List[ft.Control]],
    get_screen_holder: Callable[[], ft.Container],
    create_screen_switcher: Callable[[dict, ft.Control], ft.AnimatedSwitcher]
) -> ft.Container:

    def on_theme_changed(theme_name: str):
        ctx.settings["theme_seed"] = theme_name
        utils.save_settings(ctx.settings)
        new_seed = THEME_PRESETS.get(theme_name, "#6750A4")
        ctx.page.theme = ft.Theme(color_scheme_seed=new_seed)
        ctx.notify_theme_changed(new_seed)
        ctx.page.update()
        ctx.show_snack(f"Theme switched to {theme_name}!")

    theme_dropdown = ft.Dropdown(
        value=ctx.settings.get("theme_seed", "Deep Violet"),
        options=[ft.dropdown.Option(text=name, key=name) for name in THEME_PRESETS.keys()],
        width=230,
        dense=True,
        on_select=lambda e: on_theme_changed(e.control.value)
    )

    def on_logo_changed(logo_name: str):
        ctx.settings["logo_style"] = logo_name
        utils.save_settings(ctx.settings)
        rel_path = LOGO_PRESETS.get(logo_name, "assets/logo_minimal.png")
        abs_path = utils.get_resource_path(rel_path)
        if ctx.rail_logo:
            ctx.rail_logo.src = abs_path
        if ctx.banner_logo:
            ctx.banner_logo.src = abs_path
        ctx.page.window.icon = abs_path
        utils.apply_windows_native_icon("app_icon.ico")
        ctx.page.update()
        ctx.show_snack(f"Branding logo switched to {logo_name}!")

    def on_mode_changed(mode_name: str):
        ctx.settings["theme_mode"] = mode_name
        utils.save_settings(ctx.settings)
        if mode_name == "Light":
            ctx.page.theme_mode = ft.ThemeMode.LIGHT
        elif mode_name == "System":
            ctx.page.theme_mode = ft.ThemeMode.SYSTEM
        else:
            ctx.page.theme_mode = ft.ThemeMode.DARK
        ctx.page.update()
        ctx.show_snack(f"Switched to {mode_name} Mode!")

    theme_mode_btn = ft.SegmentedButton(
        selected=[ctx.settings.get("theme_mode", "Dark")],
        allow_multiple_selection=False,
        on_change=lambda e: on_mode_changed(list(e.control.selected)[0]),
        segments=[
            ft.Segment(value="Dark", label=ft.Text("Dark"), icon=ft.Icon(ft.Icons.DARK_MODE)),
            ft.Segment(value="Light", label=ft.Text("Light"), icon=ft.Icon(ft.Icons.LIGHT_MODE)),
            ft.Segment(value="System", label=ft.Text("System"), icon=ft.Icon(ft.Icons.SETTINGS_SYSTEM_DAYDREAM)),
        ]
    )

    logo_dropdown = ft.Dropdown(
        value=ctx.settings.get("logo_style", "Minimalist Cyber Link"),
        options=[ft.dropdown.Option(text=name, key=name) for name in LOGO_PRESETS.keys()],
        width=230,
        dense=True,
        on_select=lambda e: on_logo_changed(e.control.value)
    )

    cur_fps = ctx.settings.get("fps_mode", "120 FPS")
    if cur_fps not in FPS_PRESETS:
        cur_fps = "120 FPS"

    fps_desc_text = ft.Text(
        FPS_PRESETS[cur_fps].get("desc", ""),
        size=11,
        color=ft.Colors.ON_SURFACE_VARIANT
    )

    def on_fps_changed(fps_mode: str):
        ctx.settings["fps_mode"] = fps_mode
        utils.save_settings(ctx.settings)
        cfg = FPS_PRESETS.get(fps_mode, FPS_PRESETS["120 FPS"])
        screens = get_screens()
        cur_screen = screens[state.active_screen]
        screen_holder = get_screen_holder()
        screen_holder.content = create_screen_switcher(cfg, cur_screen)
        screen_holder.update()
        fps_desc_text.value = cfg.get("desc", "")
        fps_desc_text.update()
        ctx.show_snack(f"Framerate mode set to {fps_mode} ({cfg.get('label')}) - Live Applied!")

    fps_mode_btn = ft.SegmentedButton(
        selected=[cur_fps],
        allow_multiple_selection=False,
        on_change=lambda e: on_fps_changed(list(e.control.selected)[0]),
        segments=[
            ft.Segment(value="60 FPS", label=ft.Text("60 FPS"), icon=ft.Icon(ft.Icons.SPEED)),
            ft.Segment(value="120 FPS", label=ft.Text("120 FPS"), icon=ft.Icon(ft.Icons.BOLT)),
            ft.Segment(value="Instant", label=ft.Text("Instant"), icon=ft.Icon(ft.Icons.FLASH_ON)),
        ]
    )

    concur_slider = ft.Slider(
        min=1, max=6, divisions=5,
        value=ctx.settings.get("concurrency", 3),
        label="{value} tabs"
    )
    concur_label = ft.Text(f"{ctx.settings.get('concurrency', 3)} Parallel Tabs (Recommended: 3–4)", size=12, color=seed_color)

    def on_concur_changed(e):
        val = int(round(concur_slider.value))
        concur_label.value = f"{val} Parallel Tabs (Recommended: 3–4)"
        ctx.settings["concurrency"] = val
        utils.save_settings(ctx.settings)
        concur_label.update()
        ctx.update_stats_display(state.is_running)

    concur_slider.on_change = on_concur_changed

    def on_val_switch_changed(e):
        ctx.settings["auto_validate"] = e.control.value
        utils.save_settings(ctx.settings)
        ctx.update_stats_display(state.is_running)

    val_switch = ft.Switch(
        value=ctx.settings.get("auto_validate", True),
        on_change=on_val_switch_changed
    )

    jd_port_field = ft.TextField(
        value=str(ctx.settings.get("jd_port", 9666)),
        width=100,
        dense=True,
        on_change=lambda e: (ctx.settings.update({"jd_port": int(e.control.value or 9666)}), utils.save_settings(ctx.settings))
    )

    def test_jd_connection(e):
        port = int(jd_port_field.value or 9666)
        if integrations.is_jdownloader_running(port):
            ctx.show_snack(f"✅ JDownloader 2 is running and reachable on port {port}!")
        else:
            ctx.show_snack(f"⚠️ Could not connect to JDownloader 2 on port {port}.", success=False)

    def on_startup_update_changed(e):
        ctx.settings["check_updates_on_startup"] = e.control.value
        utils.save_settings(ctx.settings)

    startup_update_switch = ft.Switch(
        value=ctx.settings.get("check_updates_on_startup", True),
        on_change=on_startup_update_changed
    )

    def on_community_share_changed(e):
        ctx.settings["community_auto_share"] = e.control.value
        utils.save_settings(ctx.settings)
        ctx.show_snack("Community auto-share preference saved!")

    community_share_switch = ft.Switch(
        value=ctx.settings.get("community_auto_share", True),
        on_change=on_community_share_changed
    )

    community_url_field = ft.TextField(
        value=ctx.settings.get("community_firebase_url", community.DEFAULT_FIREBASE_URL),
        width=340,
        dense=True,
        on_change=lambda e: (ctx.settings.update({"community_firebase_url": e.control.value.strip()}), utils.save_settings(ctx.settings))
    )

    def test_firebase_cloud(e):
        url = community_url_field.value.strip()
        ok, msg = community.test_firebase_connection(url)
        ctx.show_snack(f"{'✅' if ok else '⚠️'} {msg}", success=ok)

    settings_main_container = ft.Container(
        content=ft.Column([
            # 1. Theme Brightness Mode (Dark / Light / System)
                        ft.Row([
                            ft.Column([
                                ft.Text("Appearance & Theme Mode:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Toggle between Dark Mode, Light Mode, or follow Windows System setting.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            theme_mode_btn
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 2. Theme Palette Color
                        ft.Row([
                            ft.Column([
                                ft.Text("Material 3 Theme Palette Preset:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Choose dynamic seed color (Deep Violet, Emerald, Cyber Sapphire, Amber Gold, Neon Rose, Synthwave, Matrix, Crimson).", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            theme_dropdown
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 3. App Logo & Branding
                        ft.Row([
                            ft.Column([
                                ft.Text("Application Logo & Branding Theme:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Active theme: Minimalist Cyber Link branding.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            logo_dropdown
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 4. Framerate & High Refresh Rate Mode (60 FPS / 120 FPS / Instant)
                        ft.Row([
                            ft.Column([
                                ft.Text("Framerate & Refresh Rate Mode:", size=13, weight=ft.FontWeight.BOLD),
                                fps_desc_text
                            ], expand=True),
                            fps_mode_btn
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 5. Concurrency
                        ft.Row([
                            ft.Column([
                                ft.Text("Worker Tab Concurrency (Parallel Resolution):", size=13, weight=ft.FontWeight.BOLD),
                                concur_label
                            ]),
                            ft.Container(content=concur_slider, width=220)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 6. Auto-Validation
                        ft.Row([
                            ft.Column([
                                ft.Text("Auto-Validate Links & Calculate Repack Size:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Runs rapid 1-byte Range checks to compute total download size and verify live filenames.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            val_switch
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 7. Phase 3: Community Cloud Auto-Share
                        ft.Row([
                            ft.Column([
                                ft.Text("Auto-Share Resolved Links to Community Cloud:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Automatically publish newly resolved direct URLs anonymously to Community Hub so others can download instantly.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            community_share_switch
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 8. Phase 3: Community Firebase RTDB URL
                        ft.Row([
                            ft.Column([
                                ft.Text("Community Firebase Realtime DB Endpoint:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("REST API endpoint for Community Cloud Cache synchronization.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            ft.Row([
                                community_url_field,
                                ft.FilledTonalButton("Test Cloud", on_click=test_firebase_cloud)
                            ])
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 9. JD2 Port
                        ft.Row([
                            ft.Column([
                                ft.Text("JDownloader 2 Local CNL Port:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Default port for JDownloader 2 Click'n'Load / FlashGot web API is 9666.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            ft.Row([
                                jd_port_field,
                                ft.FilledTonalButton("Test", on_click=test_jd_connection)
                            ])
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 10. Check for Updates
                        ft.Row([
                            ft.Column([
                                ft.Text(f"Application Version & Updates ({updater.CURRENT_VERSION}):", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Check GitHub Releases for the latest patches, features, and binary builds.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            ft.Row([
                                ft.OutlinedButton("What's New", icon=ft.Icons.AUTO_AWESOME, on_click=lambda _: ctx.show_whats_new_dialog()),
                                ft.FilledButton("Check for Updates", icon=ft.Icons.SYSTEM_UPDATE, on_click=ctx.show_update_dialog)
                            ], spacing=8)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 11. Startup Update Check
                        ft.Row([
                            ft.Column([
                                ft.Text("Auto-Check for Updates on Startup:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Silently query GitHub Releases when opening the app and prompt if an update is found.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            startup_update_switch
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 12. Interactive Tutorial & Tour
                        ft.Row([
                            ft.Column([
                                ft.Text("Interactive GUI Tutorial & Quickstart Tour:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Replay the 4-step visual onboarding guide covering Turbo Extractor, Community Cloud Cache, Health Check, and JD2 push.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            ft.FilledTonalButton("Open Tutorial Tour", icon=ft.Icons.HELP_OUTLINE, on_click=lambda _: ctx.show_tutorial_dialog())
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 13. About & Author Credits
                        ft.Row([
                            ft.Column([
                                ft.Text("Original Author & Open Source License:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Developed by Vikash (@vik05h) • Licensed under PolyForm Noncommercial 1.0.0 (Free for personal use; no commercial use).", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            ft.TextButton("GitHub Repo", icon=ft.Icons.OPEN_IN_NEW, on_click=lambda _: updater.open_release_page("https://github.com/vik05h/Link-Extractor"))
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ], spacing=12),
                    padding=20,
                    border_radius=12
                )
    ctx.tour_targets["settings_card"] = settings_main_container

    settings_screen = ft.Container(
        key="screen_settings",
        content=ft.Column([
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Engine & Customization Preferences", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("Configure Material 3 color themes, worker tab concurrency, validation, Community Cloud, and JDownloader 2 integration.", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
                    ]),
                    padding=16
                )
            ),
            ft.Card(
                content=settings_main_container
            )
        ], spacing=10, expand=True, scroll=ft.ScrollMode.ADAPTIVE),
        padding=16,
        expand=True
    )

    return settings_screen
