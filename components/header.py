from pathlib import Path
from typing import Optional

import streamlit as st
from PIL import Image

from services.log_service import log_info, restart_logs


def _render_logout_button(authenticator, username=None, name=None, role=None) -> None:
    if authenticator is None:
        return

    if st.button("Logout", key="logout_button"):
        try:
            log_info(
                "auth",
                "Logout solicitado pelo usuario",
                {"username": username or "", "name": name or "", "role": role or ""},
            )
            restart_logs(reason="Sessao encerrada; log reiniciado para novo acesso")
        except Exception:
            pass

        try:
            from services.auth_log_service import registrar_logout

            registrar_logout(
                username=username,
                nome=name,
                perfil=role,
            )
        except Exception:
            pass

        st.session_state["login_registrado"] = False

        try:
            authenticator.logout(location="unrendered")
        except TypeError:
            try:
                authenticator.logout("Logout", "unrendered")
            except Exception:
                pass
        except Exception:
            pass

        st.rerun()


def _pill(text: str, icon: str = "") -> str:
    prefix = f"{icon} " if icon else ""
    return (
        "<span style='"
        "display:inline-flex;"
        "align-items:center;"
        "padding:7px 14px;"
        "border-radius:999px;"
        "font-size:15px;"
        "font-weight:600;"
        "line-height:1;"
        "border:1px solid var(--panel-border);"
        "background:var(--panel-bg);"
        "color:var(--text-secondary);"
        "white-space:nowrap;"
        "'>"
        f"{prefix}{text}"
        "</span>"
    )


def render_header(
    logo_path: str,
    app_name: str,
    version: str,
    user: Optional[str] = None,
    role: Optional[str] = None,
    username: Optional[str] = None,
    authenticator=None,
    subtitle: str = "Análise de Dados Climáticos",
) -> None:
    left, center, right = st.columns([3.1, 3.4, 3.5], vertical_alignment="center")

    with left:
        logo_col, text_col = st.columns([1, 6], vertical_alignment="center")

        with logo_col:
            logo_file = Path(logo_path)
            if logo_file.exists():
                try:
                    img = Image.open(logo_file)
                    st.image(img, width=52)
                except Exception:
                    pass

        with text_col:
            st.markdown(
                (
                    "<div style='display:flex; align-items:center; gap:12px; flex-wrap:wrap;'>"
                    f"<span style='font-size:28px; font-weight:700; line-height:1.1;'>{app_name}</span>"
                    f"<span style='font-size:12px; opacity:0.70; padding-top:3px;'>{version}</span>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

    with center:
        st.markdown(
            (
                "<div style='display:flex; justify-content:center; align-items:center; height:100%; text-align:center;'>"
                f"<span style='font-size:22px; font-weight:600; opacity:0.95; line-height:1.15;'>{subtitle}</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    with right:
        if user or role or authenticator:
            info_col, btn_col = st.columns([4.4, 1.35], vertical_alignment="center")

            with info_col:
                items = []
                if user:
                    items.append(_pill(str(user), "👤"))
                if role:
                    items.append(_pill(str(role), "🔐"))

                st.markdown(
                    (
                        "<div style='display:flex; justify-content:flex-end; align-items:center; "
                        "gap:8px; flex-wrap:wrap;'>"
                        + "".join(items) +
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

            with btn_col:
                _render_logout_button(
                    authenticator=authenticator,
                    username=username,
                    name=user,
                    role=role,
                )

    st.markdown(
        (
            "<div style='margin-top:4px; margin-bottom:8px; "
            "border-bottom:1px solid var(--panel-border);'></div>"
        ),
        unsafe_allow_html=True,
    )
