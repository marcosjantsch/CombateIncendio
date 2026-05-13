# core/state.py
import streamlit as st

def init_session_state():
    defaults = {
        "aplicar": False,
        "mostrar_tudo_shape": False,
        "mostrar_tudo_clima": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value