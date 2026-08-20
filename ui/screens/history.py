from typing import Callable, Tuple
import pyperclip
import flet as ft

import integrations
from ui.state import UIContext, AppState


def build_history_screen(ctx: UIContext, state: AppState, seed_color: str) -> Tuple[ft.Container, Callable[[str], None]]:
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
        records = ctx.history_mgr.get_records(query)
        if not records:
            history_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.HISTORY, size=48, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text("No extraction records found.", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text("Resolved game links will automatically appear here.", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.Alignment.CENTER,
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
                                    ft.FilledTonalButton("📋 Copy", on_click=lambda _, u=urls: (pyperclip.copy("\n".join(u)), ctx.show_snack(f"Copied {len(u)} URLs!"))),
                                    ft.FilledButton("🚀 Push JD2", on_click=lambda _, u=urls, t=rec["title"]: (
                                        ctx.show_snack(integrations.push_to_jdownloader(u, t, port=ctx.settings.get("jd_port", 9666))[1])
                                    )),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=ft.Colors.RED_400,
                                        tooltip="Delete Record",
                                        on_click=lambda _, r_id=rec["id"]: (ctx.history_mgr.delete_record(r_id), refresh_history(search_input.value))
                                    )
                                ])
                            ]),
                            padding=12
                        )
                    )
                )
        ctx.page.update()

    search_input.on_change = lambda e: refresh_history(search_input.value)

    history_screen = ft.Container(
        key="screen_history",
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
                                on_click=lambda _: (ctx.history_mgr.clear_history(), refresh_history())
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

    return history_screen, refresh_history
