from pathlib import Path
import streamlit as st
from PIL import Image


def add_logo_sidebar(logo_path: str) -> None:
    logo_file = Path(logo_path)

    if not logo_file.exists():
        return

    try:
        img = Image.open(logo_file)

        st.sidebar.markdown(
            '<div style="margin-bottom:-10px;">',
            unsafe_allow_html=True
        )

        st.sidebar.image(img, width=140)

        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    except:
        pass