from pathlib import Path

import streamlit as st


CSS_PATH = Path(__file__).resolve().parents[1] / "assets" / "styles" / "theme_streamlit.css"


def apply_styles() -> None:
    st.markdown(
        "<style>\n" + CSS_PATH.read_text(encoding="utf-8") + "\n</style>",
        unsafe_allow_html=True,
    )
