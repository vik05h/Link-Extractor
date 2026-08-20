import flet as ft

THEME_PRESETS = {
    "Deep Violet": "#6750A4",
    "Emerald": "#10B981",
    "Sapphire": "#0284C7",
    "Amber": "#F59E0B",
    "Rose": "#F43F5E"
}

LOGO_PRESETS = {
    "Minimalist Cyber Link": "assets/logo_minimal.png",
    "Retro Arcade Cartridge": "assets/logo_arcade.png"
}

ANIMATION_PRESETS = {
    "Fast Subtle Fade": {
        "transition": ft.AnimatedSwitcherTransition.FADE,
        "duration": 300,
        "reverse_duration": 220,
        "curve_in": ft.AnimationCurve.EASE_IN_OUT,
        "curve_out": ft.AnimationCurve.EASE_IN_OUT
    },
    "Instant (Snappy)": {
        "transition": ft.AnimatedSwitcherTransition.FADE,
        "duration": 0,
        "reverse_duration": 0,
        "curve_in": ft.AnimationCurve.LINEAR,
        "curve_out": ft.AnimationCurve.LINEAR
    }
}
