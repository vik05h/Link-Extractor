import sys
import os

# Add repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import flet as ft
from ui.state import AppState, UIContext
from ui.constants import THEME_PRESETS
from ui.screens.extractor import build_extractor_screen
from ui.screens.community import build_community_screen
from ui.screens.history import build_history_screen
from ui.screens.settings import build_settings_screen
from ui.screens.pipeline import load_community_record_into_extractor
from history import HistoryManager
import utils


def test_ui_instantiation():
    print("--> Testing full UI instantiation & builder functions...")
    # Mock Page
    class MockWindow:
        width = 1000
        height = 800
        min_width = 800
        min_height = 600
        icon = None
        def to_front(self): pass
        def close(self): pass

    class MockPage:
        title = "Test"
        theme_mode = ft.ThemeMode.DARK
        theme = None
        padding = 0
        window = MockWindow()
        overlay = []
        def update(self): pass
        def show_dialog(self, dlg): pass
        def pop_dialog(self): pass
        def run_task(self, task, *args): pass

    mock_page = MockPage()
    settings = utils.load_settings()
    history_mgr = HistoryManager(os.path.join(os.path.dirname(__file__), "test_ui_hist.db"))

    state = AppState()
    ctx = UIContext(mock_page, settings, history_mgr)
    ctx.state = state

    seed_color = "#6750A4"

    def create_screen_switcher(cfg, cur_screen):
        return ft.AnimatedSwitcher(content=cur_screen, transition=cfg["transition"], duration=cfg["duration"], reverse_duration=cfg["reverse_duration"])

    extractor_screen = build_extractor_screen(ctx, state, seed_color)
    assert extractor_screen is not None
    print("    [PASS] Extractor Screen built successfully.")

    community_screen, refresh_comm = build_community_screen(
        ctx=ctx,
        state=state,
        seed_color=seed_color,
        on_load_record_into_extractor=lambda rec: load_community_record_into_extractor(ctx, state, rec)
    )
    assert community_screen is not None
    print("    [PASS] Community Screen built successfully.")

    history_screen, refresh_hist = build_history_screen(ctx, state, seed_color)
    assert history_screen is not None
    print("    [PASS] History Screen built successfully.")

    screens = [extractor_screen, community_screen, history_screen]
    screen_holder = ft.Container(content=extractor_screen)

    settings_screen = build_settings_screen(
        ctx=ctx,
        state=state,
        seed_color=seed_color,
        get_screens=lambda: screens,
        get_screen_holder=lambda: screen_holder,
        create_screen_switcher=create_screen_switcher
    )
    assert settings_screen is not None
    print("    [PASS] Settings Screen built successfully.")

    print("\nALL 4 SCREENS BUILT AND MOUNTED WITHOUT ERRORS! (100% OK)")


if __name__ == "__main__":
    test_ui_instantiation()
