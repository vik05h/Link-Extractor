import flet as ft

THEME_PRESETS = {
    "Deep Violet": "#6750A4",
    "Emerald": "#10B981",
    "Cyber Sapphire": "#0284C7",
    "Amber Gold": "#F59E0B",
    "Neon Rose": "#F43F5E",
    "Synthwave Purple": "#A855F7",
    "Matrix Cyber": "#00FF66",
    "Crimson Flame": "#EF4444"
}

LOGO_PRESETS = {
    "Minimalist Cyber Link": "assets/logo_minimal.png"
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

FPS_PRESETS = {
    "60 FPS": {
        "label": "60 FPS (Balanced)",
        "duration": 220,
        "reverse_duration": 160,
        "card_duration": 200,
        "curve_in": ft.AnimationCurve.EASE_OUT_CUBIC,
        "curve_out": ft.AnimationCurve.EASE_IN_OUT,
        "transition": ft.AnimatedSwitcherTransition.FADE,
        "desc": "Optimized 60 FPS standard fluid transitions for 60Hz displays and power efficiency."
    },
    "120 FPS": {
        "label": "120 FPS (Ultra Fluid)",
        "duration": 110,
        "reverse_duration": 80,
        "card_duration": 100,
        "curve_in": ft.AnimationCurve.FAST_OUT_SLOWIN,
        "curve_out": ft.AnimationCurve.FAST_OUT_SLOWIN,
        "transition": ft.AnimatedSwitcherTransition.FADE,
        "desc": "High-refresh rate 120+ FPS mode for ultra-responsive, silky-smooth gaming monitors (120Hz/144Hz/240Hz)."
    },
    "Instant": {
        "label": "Instant (0ms)",
        "duration": 0,
        "reverse_duration": 0,
        "card_duration": 0,
        "curve_in": ft.AnimationCurve.LINEAR,
        "curve_out": ft.AnimationCurve.LINEAR,
        "transition": ft.AnimatedSwitcherTransition.FADE,
        "desc": "Snappy zero-delay instant switching mode with no animations."
    }
}
