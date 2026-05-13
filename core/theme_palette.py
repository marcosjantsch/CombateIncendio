from copy import deepcopy

import streamlit as st


_THEME_PALETTES = {
    "light": {
        "mode": "light",
        "chart_surface": "#ffffff",
        "chart_grid": "#d8e2ef",
        "chart_domain": "#bfcfe2",
        "chart_text": "#213248",
        "chart_legend_bg": "rgba(255, 255, 255, 0.9)",
        "chart_temp_max": "#10c9bb",
        "chart_temp_min": "#1778e6",
        "chart_precip": "#f04d63",
        "plotly_bar": "#10c9bb",
        "plotly_bar_line": "#1778e6",
        "plotly_sequence": ["#10c9bb", "#f04d63", "#1778e6", "#16273c", "#7f98b4"],
        "panel_border": "#d2deec",
        "map_background": "#e7edf6",
        "map_surface": "rgba(255, 255, 255, 0.96)",
        "map_control": "#ffffff",
        "map_text": "#203247",
        "map_text_soft": "#5d7289",
        "map_accent": "#10c9bb",
        "map_accent_strong": "#1778e6",
        "map_highlight": "#14d2c1",
        "map_tooltip": "#ffffff",
    },
}


def get_theme_key() -> str:
    return "light"


def get_theme_palette() -> dict:
    return deepcopy(_THEME_PALETTES[get_theme_key()])
