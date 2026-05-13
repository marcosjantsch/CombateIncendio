# components/topbar.py
import streamlit as st

def render_logout_in_main(authenticator):
    try:
        authenticator.logout(location="main")
    except TypeError:
        authenticator.logout("Logout", "main")

def render_topbar(auth_enabled, authentication_status, name, role, authenticator):
    topL, topR = st.columns([7, 3], vertical_alignment="center")
    with topR:
        if auth_enabled and authentication_status:
            c_user, c_role, c_btn = st.columns([2.2, 1.6, 1.2], vertical_alignment="center")

            with c_user:
                st.markdown(
                    f'<div class="userbar"><span class="pill">👤 {name}</span></div>',
                    unsafe_allow_html=True,
                )

            with c_role:
                st.markdown(
                    f'<div class="userbar"><span class="pill">🔐 {role}</span></div>',
                    unsafe_allow_html=True,
                )

            with c_btn:
                render_logout_in_main(authenticator)