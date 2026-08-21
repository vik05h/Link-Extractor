import sys
sys.path.insert(0, ".")
import flet as ft
from ui.state import UIContext, AppState
import utils
from history import HistoryManager
from ui.screens.community import build_community_screen, build_3d_title_card

def test_community_screen():
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
    
    screen, refresh_cb = build_community_screen(
        ctx=ctx,
        state=state,
        seed_color="#6750A4",
        on_load_record_into_extractor=lambda r: None
    )
    print("Community screen built successfully:", type(screen))
    
    # Test card with hover simulation
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
    card = build_3d_title_card(rec, ctx, state, "#6750A4", lambda r: None, lambda: None)
    
    # Simulate hover event
    class HoverEvent:
        def __init__(self, data):
            self.data = data
            
    card.content.on_hover(HoverEvent("true"))
    print("Hover enter simulated successfully! Card elevation:", card.elevation, "Card scale:", card.scale)
    card.content.on_hover(HoverEvent("false"))
    print("Hover exit simulated successfully! Card elevation:", card.elevation, "Card scale:", card.scale)

if __name__ == "__main__":
    test_community_screen()
