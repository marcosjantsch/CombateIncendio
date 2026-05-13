# -*- coding: utf-8 -*-
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

from core.settings import AUTH_CONFIG_PATH


def load_config():
    try:
        with open(AUTH_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.load(f, Loader=SafeLoader)
    except FileNotFoundError:
        st.error(f"Arquivo de autenticacao nao encontrado: {AUTH_CONFIG_PATH}")
        st.stop()


def build_authenticator():
    config = load_config()

    return stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )


def get_auth_state():
    return (
        st.session_state.get("name"),
        st.session_state.get("authentication_status"),
        st.session_state.get("username"),
    )


def setup_authentication(
    location="sidebar",
    fields=None,
    key="Login",
    allow_cookie_reauth=True,
):
    authenticator = build_authenticator()

    # Newer versions may return None and only populate session_state.
    try:
        if not allow_cookie_reauth and not st.session_state.get("authentication_status"):
            authenticator.cookie_controller.delete_cookie()

        login_result = authenticator.login(
            location=location,
            fields=fields,
            key=key,
        )
    except Exception as e:
        raise RuntimeError(f"Falha ao inicializar autenticacao: {e}") from e

    if isinstance(login_result, tuple) and len(login_result) == 3:
        name, authentication_status, username = login_result
    else:
        name, authentication_status, username = get_auth_state()

    return authenticator, name, authentication_status, username


def get_user_role():
    config = load_config()
    username = st.session_state.get("username")
    if username and username in config["credentials"]["usernames"]:
        return config["credentials"]["usernames"][username].get("role", "user")
    return "user"
