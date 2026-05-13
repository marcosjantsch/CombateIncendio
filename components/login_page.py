# -*- coding: utf-8 -*-
import base64
from io import BytesIO

import streamlit as st
from PIL import Image

from auth import build_authenticator, get_auth_state, setup_authentication
from core.settings import LOGO_PATH


@st.cache_data(show_spinner=False)
def _get_login_logo_data_uri(path: str) -> str:
    with Image.open(path) as img:
        rgba_image = img.convert("RGBA")
        buffer = BytesIO()
        rgba_image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_login_page():
    name, authentication_status, username = get_auth_state()
    if authentication_status is True:
        return build_authenticator(), name, authentication_status, username

    logo_src = _get_login_logo_data_uri(LOGO_PATH)

    st.markdown(
        """
        <style>
        header[data-testid="stHeader"],
        section[data-testid="stSidebar"] {
            display: none !important;
        }

        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMainBlockContainer"] {
            background:
                radial-gradient(circle at 12% 18%, rgba(16, 201, 187, 0.16), transparent 24%),
                radial-gradient(circle at 88% 14%, rgba(23, 120, 230, 0.14), transparent 22%),
                linear-gradient(180deg, #f4f8fd 0%, #edf3fa 54%, #f7fafe 100%) !important;
            color: #1f3146 !important;
        }

        [data-testid="stAppViewContainer"] > .main {
            transform: none !important;
            zoom: 1 !important;
            width: 100% !important;
        }

        .block-container {
            max-width: 1320px !important;
            padding-top: clamp(1.5rem, 5vh, 3.5rem) !important;
            padding-bottom: clamp(1.5rem, 5vh, 3.5rem) !important;
            padding-left: clamp(1rem, 3vw, 2rem) !important;
            padding-right: clamp(1rem, 3vw, 2rem) !important;
        }

        [data-testid="stHorizontalBlock"] {
            align-items: stretch !important;
            gap: clamp(1rem, 2vw, 1.6rem) !important;
        }

        .avant-left-shell {
            min-height: min(82vh, 860px);
            border-radius: 30px;
        }

        .avant-left-shell {
            padding: clamp(1.6rem, 3vw, 2.5rem);
            background:
                radial-gradient(circle at top right, rgba(23, 210, 191, 0.22), transparent 26%),
                linear-gradient(155deg, #17314f 0%, #10253b 100%);
            box-shadow: 0 30px 70px rgba(16, 31, 52, 0.22);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .avant-chip {
            display: inline-flex;
            align-items: center;
            padding: 0.42rem 0.82rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.10);
            border: 1px solid rgba(255, 255, 255, 0.14);
            color: #dce9f8 !important;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.18em;
            text-transform: uppercase;
        }

        .avant-brand-row {
            display: flex;
            align-items: center;
            gap: 0.9rem;
            margin-bottom: 1.1rem;
        }

        .avant-logo-wrap {
            width: 66px;
            height: 66px;
            border-radius: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.16);
            box-shadow: 0 12px 24px rgba(7, 19, 34, 0.22);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            overflow: hidden;
        }

        .avant-logo {
            width: 52px;
            height: 52px;
            object-fit: contain;
            display: block;
        }

        .avant-title {
            margin: 1.25rem 0 0.8rem 0;
            color: #ffffff !important;
            font-size: clamp(2.05rem, 3vw, 3.2rem);
            line-height: 1.04;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }

        .avant-subtitle {
            max-width: 32rem;
            margin: 0 0 1.8rem 0;
            color: rgba(233, 242, 250, 0.82) !important;
            font-size: 1rem;
            line-height: 1.6;
        }

        .avant-info-grid {
            display: grid;
            gap: 0.95rem;
        }

        .avant-info-card {
            padding: 1rem 1.05rem;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.10);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }

        .avant-info-card-title {
            margin-bottom: 0.28rem;
            color: #ffffff !important;
            font-size: 0.9rem;
            font-weight: 700;
            letter-spacing: 0.04em;
        }

        .avant-info-card-text {
            color: rgba(225, 236, 247, 0.78) !important;
            font-size: 0.9rem;
            line-height: 1.5;
        }

        .avant-access-message {
            max-width: 420px;
            margin-bottom: 1.15rem;
            margin-left: auto;
            margin-right: auto;
            padding: 0.95rem 1rem;
            border-radius: 18px;
            border: 1px solid #d2deec;
            background: linear-gradient(180deg, rgba(250, 253, 255, 0.98), rgba(241, 247, 255, 0.96));
            color: #556a82 !important;
            line-height: 1.55;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.95);
        }

        .avant-access-message.error {
            border-color: rgba(240, 77, 99, 0.20);
            background: linear-gradient(180deg, rgba(255, 248, 249, 0.98), rgba(255, 240, 243, 0.96));
            color: #9c3850 !important;
        }

        div[data-testid="stForm"] {
            max-width: 420px !important;
            margin: 0 auto !important;
            border: 1px solid rgba(210, 222, 236, 0.95) !important;
            border-radius: 24px !important;
            padding: clamp(1.15rem, 2.1vw, 1.6rem) !important;
            background: #ffffff !important;
            box-shadow: 0 18px 38px rgba(31, 49, 70, 0.10) !important;
        }

        div[data-testid="stForm"] * {
            color: #1f3146 !important;
        }

        div[data-testid="stForm"] h3 {
            display: none !important;
        }

        div[data-testid="stForm"] label,
        div[data-testid="stForm"] [data-testid="stWidgetLabel"] p {
            color: #1f3146 !important;
            font-weight: 600 !important;
            letter-spacing: 0.03em;
        }

        div[data-testid="stForm"] [data-baseweb="input"] {
            border-radius: 16px !important;
            border: 1px solid #d2deec !important;
            background: #ffffff !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.92) !important;
        }

        div[data-testid="stForm"] [data-baseweb="input"]:focus-within {
            border-color: rgba(23, 120, 230, 0.48) !important;
            box-shadow: 0 0 0 4px rgba(23, 120, 230, 0.10) !important;
        }

        div[data-testid="stForm"] input {
            min-height: 3rem !important;
            color: #1f3146 !important;
            background: transparent !important;
            caret-color: #1778e6 !important;
            -webkit-text-fill-color: #1f3146 !important;
        }

        div[data-testid="stForm"] input::placeholder {
            color: #8aa0b8 !important;
            opacity: 1 !important;
        }

        div[data-testid="stForm"] button p,
        div[data-testid="stFormSubmitButton"] button p,
        div[data-testid="stFormSubmitButton"] button span {
            color: inherit !important;
        }

        div[data-testid="stFormSubmitButton"] > button {
            width: 100% !important;
            min-height: 3.2rem !important;
            margin-top: 0.55rem !important;
            border: none !important;
            border-radius: 16px !important;
            color: #ffffff !important;
            font-size: 0.98rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.05em !important;
            text-transform: uppercase !important;
            background: linear-gradient(135deg, #10c9bb 0%, #17d2bf 55%, #1778e6 100%) !important;
            box-shadow: 0 18px 30px rgba(16, 201, 187, 0.24) !important;
        }

        div[data-testid="stFormSubmitButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:focus-visible {
            transform: translateY(-1px);
            box-shadow: 0 22px 36px rgba(16, 201, 187, 0.28) !important;
        }

        div[data-testid="stFormSubmitButton"] > button:disabled {
            background: linear-gradient(135deg, #a7d8d4 0%, #9bd8d0 100%) !important;
            color: rgba(255, 255, 255, 0.88) !important;
            box-shadow: none !important;
        }

        .avant-access-footnote {
            max-width: 420px;
            margin-top: 0.9rem;
            margin-left: auto;
            margin-right: auto;
            color: #6d8199 !important;
            font-size: 0.86rem;
            line-height: 1.5;
        }

        @media (max-width: 980px) {
            [data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
            }

            .avant-left-shell {
                min-height: auto;
            }

            .avant-left-shell {
                padding: 1.35rem;
            }

            .avant-title {
                font-size: 1.8rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="avant-login-shell"></div>', unsafe_allow_html=True)
    left_col, right_col = st.columns([1.15, 0.95], gap="large", vertical_alignment="center")

    with left_col:
        st.markdown(
            """
            <div class="avant-left-shell">
                <div class="avant-brand-row">
                    <div class="avant-logo-wrap">
                        <img class="avant-logo" src="%s" alt="Avant" />
                    </div>
                    <div class="avant-chip">Avant Platform</div>
                </div>
                <div class="avant-title">Inteligência Climática Integrada</div>
                <div class="avant-subtitle">
                    Plataforma institucional para leitura operacional, análise territorial e apoio técnico à
                    tomada de decisão em ambiente corporativo.
                </div>
                <div class="avant-info-grid">
                    <div class="avant-info-card">
                        <div class="avant-info-card-title">Monitoramento Centralizado</div>
                        <div class="avant-info-card-text">Consolide camadas geoespaciais, séries climáticas e indicadores operacionais em um único ambiente.</div>
                    </div>
                    <div class="avant-info-card">
                        <div class="avant-info-card-title">Leitura Técnica Rápida</div>
                        <div class="avant-info-card-text">Acesse painéis objetivos para inspeção de mapa, clima, tendência e visão analítica com padrão executivo.</div>
                    </div>
                    <div class="avant-info-card">
                        <div class="avant-info-card-title">Acesso Seguro Corporativo</div>
                        <div class="avant-info-card-text">Ambiente autenticado com credenciais institucionais para preservar contexto, rastreabilidade e governança.</div>
                    </div>
                </div>
            </div>
            """ % logo_src,
            unsafe_allow_html=True,
        )

    with right_col:
        message_slot = st.empty()
        authenticator, name, authentication_status, username = setup_authentication(
            location="main",
            fields={
                "Form name": "",
                "Username": "Usuário",
                "Password": "Senha",
                "Login": "Entrar",
            },
            key="AvantLoginForm",
            allow_cookie_reauth=False,
        )

        if authentication_status is False:
            message_slot.markdown(
                """
                <div class="avant-access-message error">
                    Credenciais inválidas. Verifique usuário e senha para continuar.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            message_slot.markdown(
                """
                <div class="avant-access-message">
                    Entre com suas credenciais corporativas para acessar módulos analíticos, mapas e leituras operacionais da plataforma.
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div class="avant-access-footnote">
                Ambiente institucional Avant com autenticação segura e experiência otimizada para desktop e mobile.
            </div>
            """,
            unsafe_allow_html=True,
        )

    return authenticator, name, authentication_status, username
