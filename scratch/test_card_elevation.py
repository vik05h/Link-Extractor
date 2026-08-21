import sys
sys.path.insert(0, ".")
import flet as ft
from ui.state import UIContext, AppState
import utils
from history import HistoryManager

def test_clean_card():
    settings = utils.load_settings()
    history_mgr = HistoryManager()
    state = AppState()
    
    class MockPage:
        def __init__(self):
            self.dialog = None
            self.snack_bar = None
        def run_task(self, task):
            pass
        def update(self):
            pass
            
    mock_page = MockPage()
    ctx = UIContext(mock_page, settings, history_mgr)
    
    rec = {
        "title": "Assassin's Creed: Black Flag Resynced – Deluxe Edition, v1.0.6 + 10 DLCs/Bonuses",
        "image_url": "https://fitgirl-repacks.site/wp-content/uploads/2024/08/cover.jpg",
        "total_parts": 27,
        "total_size_str": "39.10 GB",
        "local_time": "21 Aug 2026, 08:23 PM India Standard Time",
        "age_str": "10 mins ago",
        "freshness": "fresh",
        "slug": "assassins-creed-black-flag-resynced",
        "uploader": "Anonymous",
        "resolved_count": 27
    }
    
    cover_img = ft.Image(
        src=rec["image_url"],
        width=90,
        height=115,
        fit=ft.BoxFit.COVER,
        border_radius=8
    )
    
    cover_frame = ft.Container(
        content=cover_img,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.PRIMARY)),
        border_radius=8,
        animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT_CUBIC),
        scale=1.0
    )
    
    title_bar = ft.Container(
        width=3.5,
        height=20,
        border_radius=2,
        bgcolor=ft.Colors.with_opacity(0.6, ft.Colors.PRIMARY),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT_CUBIC)
    )
    
    title_text = ft.Text(
        rec["title"],
        size=15,
        weight=ft.FontWeight.BOLD,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
        color=ft.Colors.ON_SURFACE
    )
    
    title_block = ft.Container(
        content=ft.Row([
            title_bar,
            ft.Container(content=title_text, expand=True, padding=ft.Padding.only(left=2))
        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        animate_offset=ft.Animation(200, ft.AnimationCurve.EASE_OUT_CUBIC),
        offset=ft.Offset(0, 0)
    )
    
    card = ft.Card(
        elevation=1,
        animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT_CUBIC),
        scale=1.0,
        content=ft.Container(
            content=ft.Row([
                cover_frame,
                title_block
            ]),
            padding=14
        )
    )
    
    def on_hover(e):
        is_hovered = e.data in ("true", True, "True")
        card.elevation = 4 if is_hovered else 1
        card.scale = 1.008 if is_hovered else 1.0
        cover_frame.scale = 1.04 if is_hovered else 1.0
        title_block.offset = ft.Offset(0.006, 0) if is_hovered else ft.Offset(0, 0)
        title_bar.bgcolor = ft.Colors.PRIMARY if is_hovered else ft.Colors.with_opacity(0.6, ft.Colors.PRIMARY)
        
    card.content.on_hover = on_hover
    print("Card constructed cleanly without blur smudges:", card)

if __name__ == "__main__":
    test_clean_card()
