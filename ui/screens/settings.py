from typing import Callable, List
import flet as ft

import utils
import integrations
import updater
from ui.constants import THEME_PRESETS, LOGO_PRESETS, ANIMATION_PRESETS
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
        ctx.page.update()
        ctx.show_snack(f"Theme switched to {theme_name}!")

    theme_dropdown = ft.Dropdown(
        value=ctx.settings.get("theme_seed", "Deep Violet"),
        options=[ft.dropdown.Option(text=name, key=name) for name in THEME_PRESETS.keys()],
        width=200,
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
        width=220,
        dense=True,
        on_select=lambda e: on_logo_changed(e.control.value)
    )

    def on_animation_changed(anim_name: str):
        ctx.settings["animation_style"] = anim_name
        utils.save_settings(ctx.settings)
        cfg = ANIMATION_PRESETS.get(anim_name, ANIMATION_PRESETS["Fast Subtle Fade"])
        screens = get_screens()
        cur_screen = screens[state.active_screen]
        screen_holder = get_screen_holder()
        screen_holder.content = create_screen_switcher(cfg, cur_screen)
        screen_holder.update()
        ctx.show_snack(f"Tab transition set to {anim_name} (Live Applied)!")

    anim_dropdown = ft.Dropdown(
        value=ctx.settings.get("animation_style", "Fast Subtle Fade"),
        options=[ft.dropdown.Option(text=name, key=name) for name in ANIMATION_PRESETS.keys()],
        width=220,
        dense=True,
        on_select=lambda e: on_animation_changed(e.control.value)
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

    settings_screen = ft.Container(
        key="screen_settings",
        content=ft.Column([
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Engine & Customization Preferences", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("Configure Material 3 color themes, worker tab concurrency, validation, and JDownloader 2 integration.", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
                    ]),
                    padding=16
                )
            ),
            ft.Card(
                content=ft.Container(
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
                                ft.Text("Choose dynamic seed color (Deep Violet, Emerald, Sapphire, Amber, Rose).", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            theme_dropdown
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 3. App Logo & Branding
                        ft.Row([
                            ft.Column([
                                ft.Text("Application Logo & Branding Theme:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Switch between Minimalist Cyber Link and Retro Arcade Cartridge.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            logo_dropdown
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 4. Tab Transition Animation
                        ft.Row([
                            ft.Column([
                                ft.Text("Tab Switch Animation Effect:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Choose between Instant (Snappy 0ms) and Fast Subtle Fade (180ms).", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            anim_dropdown
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
                        # 7. JD2 Port
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
                        # 8. Check for Updates
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
                        # 9. Startup Update Check
                        ft.Row([
                            ft.Column([
                                ft.Text("Auto-Check for Updates on Startup:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Silently query GitHub Releases when opening the app and prompt if an update is found.", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            startup_update_switch
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        # 10. About & Author Credits
                        ft.Row([
                            ft.Column([
                                ft.Text("Original Author & Open Source License:", size=13, weight=ft.FontWeight.BOLD),
                                ft.Text("Developed by Vikash (@vik05h) • Licensed under PolyForm Noncommercial 1.0.0 (Free for personal use; no commercial use).", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                            ]),
                            ft.TextButton("GitHub Repo", icon=ft.Icons.OPEN_IN_NEW, on_click=lambda _: updater.open_release_page("https://github.com/vik05h/Link-Extractor"))
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ], spacing=12),
                    padding=20
                )
            )
        ], spacing=10, expand=True, scroll=ft.ScrollMode.ADAPTIVE),
        padding=16,
        expand=True
    )

    return settings_screen
