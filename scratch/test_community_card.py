import flet as ft
from ui.state import UIContext, AppState

# Test script to verify 3D card layout and animation attributes
def test_card_structure():
    rec = {
        "title": "Assassin's Creed: Black Flag Resynced – Deluxe Edition, v1.0.6 + 10 DLCs/Bonuses",
        "image_url": "https://fitgirl-repacks.site/wp-content/uploads/2024/08/cover.jpg",
        "total_parts": 27,
        "total_size_str": "39.10 GB",
        "local_time": "21 Aug 2026, 08:23 PM India Standard Time",
        "age_str": "Just now",
        "freshness": "fresh",
        "slug": "assassins-creed-black-flag-resynced",
        "uploader": "Anonymous",
        "resolved_count": 27
    }
    
    # Test creating animated container and its hover logic
    card_container = ft.Container(
        border_radius=14,
        padding=14,
        animate=ft.Animation(220, ft.AnimationCurve.EASE_OUT_CUBIC),
        animate_scale=ft.Animation(220, ft.AnimationCurve.EASE_OUT_CUBIC),
        animate_offset=ft.Animation(220, ft.AnimationCurve.EASE_OUT_CUBIC),
        scale=1.0,
        offset=ft.Offset(0, 0)
    )
    
    print("Test container created successfully:", card_container)

if __name__ == "__main__":
    test_card_structure()
