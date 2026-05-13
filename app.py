# -*- coding: utf-8 -*-
"""
app.py — Avant | Visualizador de Shapefile + Dados Climáticos
Versão V2.1
- Header SaaS
- Logo estável
- Autenticação opcional
- Mapa modularizado
- Geometria original preservada para exibição sem simplificação
- Tabs modularizadas
- Carregamento climático centralizado em services/climate_service.py
"""

import os
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Optional

import geopandas as gpd
import streamlit as st

from core.theme import apply_locked_light_theme
from core.styles import apply_styles
from core.stylesHEADER import apply_stylesHEADER
from core.settings import (
    APP_ICON,
    GEO_PATH,
    LOGO_PATH,
    AUTH_ENABLED,
)
from components.header import render_header
from components.login_page import render_login_page
from components.sidebar import render_sidebar

from tabs.tab_mapa import build_map_viewport, build_viewport_log_details, render_tab_mapa
from tabs.tab_shape import render_tab_shape
from tabs.tab_clima import render_tab_clima
from tabs.tab_analise import render_tab_analise
from tabs.tab_previsao import render_tab_previsao
from tabs.tab_tendencia_climatica import render_tab_tendencia_climatica
from services.auth_log_service import registrar_login
from services.climate_service import load_climate_data
from services.log_service import (
    initialize_logs,
    log_error,
    log_info,
    log_info_once,
    log_success,
    log_success_once,
    log_warning,
    log_warning_once,
)

# =====================================================================
# LOGGING
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# =====================================================================
# CONFIG
# =====================================================================
SIMPLIFICATION_TOLERANCE = 0.001
APP_VERSION = "V2.3"


# =====================================================================
# PAGE CONFIG
# =====================================================================
st.set_page_config(
    page_title="Avant",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_locked_light_theme()
initialize_logs("Avant - Clima", APP_VERSION)


# =====================================================================
# HELPERS
# =====================================================================
def _read_shapefile_full(file_path: str) -> Optional[gpd.GeoDataFrame]:
    logger.info("Carregando shapefile: %s", file_path)
    log_info("shapefile", "Iniciando carregamento do shapefile", {"path": file_path})

    if not os.path.exists(file_path):
        log_error("shapefile", "Shapefile não encontrado", {"path": file_path})
        logger.warning("Shapefile não encontrado: %s", file_path)
        return None

    try:
        gdf = gpd.read_file(file_path)

        if gdf.empty:
            log_warning("shapefile", "Shapefile carregado, porém vazio", {"path": file_path})
            logger.warning("Shapefile carregado, porém vazio.")
            return gdf

        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")

        if str(gdf.crs).upper() != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        gdf["__geometry_original__"] = gdf.geometry.copy()

        try:
            gdf["geometry"] = gdf.geometry.simplify(
                SIMPLIFICATION_TOLERANCE,
                preserve_topology=True,
            )
        except Exception as e:
            logger.warning("Falha na simplificação do shapefile: %s", e)

        log_success(
            "shapefile",
            "Shapefile carregado com sucesso",
            {
                "path": file_path,
                "records": int(len(gdf)),
                "crs": str(gdf.crs),
            },
        )
        return gdf

    except Exception as e:
        logger.error("Erro ao carregar shapefile: %s", e)
        log_error(
            "shapefile",
            "Erro ao carregar shapefile",
            {"path": file_path, "error": str(e)},
        )
        return None


@st.cache_data(show_spinner=False)
def load_shapefile_full(file_path: str) -> Optional[gpd.GeoDataFrame]:
    return _read_shapefile_full(file_path)


def load_shapefile_or_stop(file_path: str) -> gpd.GeoDataFrame:
    try:
        with st.spinner("Carregando base geoespacial..."):
            gdf = load_shapefile_full(file_path)
    except Exception as e:
        logger.error("Erro inesperado ao carregar shapefile: %s", e)
        log_error(
            "shapefile",
            "Erro inesperado na carga da base geoespacial",
            {"path": file_path, "error": str(e)},
        )
        st.error(f"Erro ao carregar a base geoespacial: {e}")
        st.stop()

    if gdf is None:
        message = f"NÃ£o foi possÃ­vel carregar o shapefile em: {file_path}"
        logger.error(message)
        log_error("shapefile", "Base geoespacial indisponivel", {"path": file_path})
        st.error(message)
        st.stop()

    log_success_once(
        "shapefile",
        "base_ready",
        "Base geoespacial pronta para uso",
        {"path": file_path, "records": int(len(gdf))},
        signature={"path": file_path, "records": int(len(gdf))},
    )
    return gdf


@st.cache_resource
def get_shapefile_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=1)


def init_shapefile_loader_state() -> None:
    st.session_state.setdefault("_shapefile_future", None)
    st.session_state.setdefault("_shapefile_future_path", None)
    st.session_state.setdefault("_shapefile_future_started_at", None)
    st.session_state.setdefault("_shapefile_gdf", None)
    st.session_state.setdefault("_shapefile_gdf_path", None)
    st.session_state.setdefault("_shapefile_error", None)
    st.session_state.setdefault("_shapefile_ready_rerun_done", False)


def start_shapefile_loading(file_path: str) -> Future:
    init_shapefile_loader_state()

    current_future = st.session_state.get("_shapefile_future")
    current_path = st.session_state.get("_shapefile_future_path")

    if current_path != file_path:
        reset_shapefile_loading()
        current_future = None

    if current_future is None:
        executor = get_shapefile_executor()
        current_future = executor.submit(_read_shapefile_full, file_path)
        st.session_state["_shapefile_future"] = current_future
        st.session_state["_shapefile_future_path"] = file_path
        st.session_state["_shapefile_future_started_at"] = time.time()
        st.session_state["_shapefile_gdf"] = None
        st.session_state["_shapefile_gdf_path"] = None
        st.session_state["_shapefile_error"] = None
        st.session_state["_shapefile_ready_rerun_done"] = False

    return current_future


def reset_shapefile_loading() -> None:
    init_shapefile_loader_state()
    st.session_state["_shapefile_future"] = None
    st.session_state["_shapefile_future_path"] = None
    st.session_state["_shapefile_future_started_at"] = None
    st.session_state["_shapefile_gdf"] = None
    st.session_state["_shapefile_gdf_path"] = None
    st.session_state["_shapefile_error"] = None
    st.session_state["_shapefile_ready_rerun_done"] = False


def get_shapefile_loading_state(file_path: str):
    init_shapefile_loader_state()

    cached_gdf = st.session_state.get("_shapefile_gdf")
    cached_path = st.session_state.get("_shapefile_gdf_path")
    if cached_gdf is not None and cached_path == file_path:
        return "ready", cached_gdf, None

    cached_error = st.session_state.get("_shapefile_error")
    if cached_error and st.session_state.get("_shapefile_future_path") == file_path:
        return "error", None, cached_error

    future = start_shapefile_loading(file_path)

    if not future.done():
        return "loading", None, None

    try:
        gdf = future.result()
        if gdf is None:
            st.session_state["_shapefile_error"] = "Não foi possível carregar o shapefile."
            return "error", None, "Não foi possível carregar o shapefile."
        st.session_state["_shapefile_gdf"] = gdf
        st.session_state["_shapefile_gdf_path"] = file_path
        st.session_state["_shapefile_future"] = None
        st.session_state["_shapefile_error"] = None
        return "ready", gdf, None
    except Exception as e:
        logger.error("Erro no futuro de carregamento do shapefile: %s", e)
        st.session_state["_shapefile_error"] = str(e)
        return "error", None, str(e)


@st.fragment(run_every=1)
def render_shapefile_loading_fragment(file_path: str) -> None:
    state, gdf_ready, error_message = get_shapefile_loading_state(file_path)
    elapsed = 0.0
    started_at = st.session_state.get("_shapefile_future_started_at")
    if started_at:
        elapsed = max(0.0, time.time() - started_at)

    if state == "loading":
        progress_value = min(92, 8 + int(elapsed * 18))
        st.progress(
            progress_value,
            text="Carregando base geoespacial da pasta Data...",
            width="stretch",
        )
        status_box = st.status(
            "Carregando shapefile principal",
            expanded=True,
            state="running",
            width="stretch",
        )
        status_box.write("Interface iniciada com sucesso.")
        status_box.write(f"Arquivo aguardado: `{file_path}`")
        status_box.write("Leitura e preparação das geometrias em andamento.")
        status_box.caption("A aplicação será liberada automaticamente assim que a base estiver pronta.")
        return

    if state == "error":
        st.progress(100, text="Falha ao carregar a base geoespacial.", width="stretch")
        status_box = st.status(
            "Erro no carregamento do shapefile",
            expanded=True,
            state="error",
            width="stretch",
        )
        status_box.write(error_message or f"Não foi possível carregar `{file_path}`.")
        if st.button("Tentar novamente", key="retry_shapefile_load"):
            reset_shapefile_loading()
            st.rerun(scope="app")
        return

    st.progress(100, text="Base geoespacial carregada com sucesso.", width="stretch")
    status_box = st.status(
        "Shapefile carregado",
        expanded=False,
        state="complete",
        width="stretch",
    )
    status_box.write(f"Base pronta com {len(gdf_ready):,} registros.")
    if not st.session_state.get("_shapefile_ready_rerun_done", False):
        st.session_state["_shapefile_ready_rerun_done"] = True
        st.rerun(scope="app")


def render_loading_shell() -> None:
    sidebar_placeholder = st.sidebar.empty()
    with sidebar_placeholder.container():
        st.image(LOGO_PATH, width=60)
        st.markdown(
            '<div style="font-size:16px; font-weight:600; margin-bottom:-6px;">Selecione a opção</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.info("Carregando base geoespacial...")

    st.markdown('<div class="section-title">Inicializando Aplicação</div>', unsafe_allow_html=True)
    render_shapefile_loading_fragment(GEO_PATH)

    loading_tabs = st.tabs(
        [
            "🗺️ Mapa Principal",
            "📋 Dados Shape",
            "📈 Dados de Clima",
            "📉 Análise Avançada",
            "Previsão do Tempo (Teste)",
            "Tendência Climática (Teste)",
        ]
    )

    for tab in loading_tabs:
        with tab:
            st.info("A interface já foi iniciada. Aguarde a conclusão do carregamento da base para liberar os conteúdos.")


def filter_gdf(gdf: gpd.GeoDataFrame, filtro: dict) -> gpd.GeoDataFrame:
    gdf_filtered = gdf.copy()
    tipo = filtro["tipo_dado"]

    if (
        tipo == "Dados por Estado"
        and filtro["selected_uf"]
        and "UF" in gdf_filtered.columns
    ):
        gdf_filtered = gdf_filtered[
            gdf_filtered["UF"].astype(str) == str(filtro["selected_uf"])
        ]

    elif (
        tipo == "Dados por Empresa"
        and filtro["selected_empresa"]
        and "EMPRESA" in gdf_filtered.columns
    ):
        gdf_filtered = gdf_filtered[
            gdf_filtered["EMPRESA"].astype(str) == str(filtro["selected_empresa"])
        ]

    elif (
        tipo == "Dados Empresa/Fazenda"
        and filtro["selected_empresa"]
        and filtro["selected_fazenda"]
        and all(c in gdf_filtered.columns for c in ["EMPRESA", "FAZENDA"])
    ):
        gdf_filtered = gdf_filtered[
            (gdf_filtered["EMPRESA"].astype(str) == str(filtro["selected_empresa"]))
            & (gdf_filtered["FAZENDA"].astype(str) == str(filtro["selected_fazenda"]))
        ]

    elif (
        tipo == "Dados por Município"
        and filtro["selected_uf"]
        and filtro["selected_municipio"]
        and all(c in gdf_filtered.columns for c in ["UF", "MUNICIPIO"])
    ):
        gdf_filtered = gdf_filtered[
            (gdf_filtered["UF"].astype(str) == str(filtro["selected_uf"]))
            & (
                gdf_filtered["MUNICIPIO"].astype(str)
                == str(filtro["selected_municipio"])
            )
        ]

    return gdf_filtered


def get_map_refresh_token(filtro: dict) -> str:
    signature_parts = [
        str(filtro.get("tipo_dado", "")),
        str(filtro.get("selected_uf", "")),
        str(filtro.get("selected_empresa", "")),
        str(filtro.get("selected_fazenda", "")),
        str(filtro.get("selected_municipio", "")),
        str(filtro.get("start_date", "")),
        str(filtro.get("end_date", "")),
        str(int(bool(filtro.get("aplicar", False)))),
        str(filtro.get("filters_version", "")),
        str(filtro.get("manual_zoom_refresh_version", "")),
    ]
    signature = "|".join(signature_parts)

    previous_signature = st.session_state.get("_map_refresh_signature")
    refresh_counter = int(st.session_state.get("_map_refresh_counter", 0))

    if previous_signature != signature:
        refresh_counter += 1
        st.session_state["_map_refresh_signature"] = signature
        st.session_state["_map_refresh_counter"] = refresh_counter

    return f"map_refresh_{st.session_state.get('_map_refresh_counter', refresh_counter)}"


def init_applied_filters_state() -> None:
    st.session_state.setdefault(
        "applied_filters",
        {
            "tipo_dado": None,
            "selected_uf": None,
            "selected_empresa": None,
            "selected_fazenda": None,
            "selected_municipio": None,
            "start_date": None,
            "end_date": None,
            "aplicar": False,
        },
    )
    st.session_state.setdefault("applied_filters_version", 0)
    st.session_state.setdefault("manual_zoom_refresh_version", 0)
    st.session_state.setdefault("manual_zoom_last_source", "")


def render_tab_theme_marker(theme_name: str) -> None:
    st.markdown(
        f"<div class='tab-theme-marker tab-theme-{theme_name}'></div>",
        unsafe_allow_html=True,
    )


def render_premium_login_page():
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

        [data-testid="column"]:has(.avant-login-panel-left),
        [data-testid="column"]:has(.avant-login-panel-right) {
            border-radius: 30px;
            min-height: min(82vh, 860px);
        }

        [data-testid="column"]:has(.avant-login-panel-left) {
            padding: clamp(1.6rem, 3vw, 2.5rem) !important;
            background:
                radial-gradient(circle at top right, rgba(23, 210, 191, 0.22), transparent 26%),
                linear-gradient(155deg, #17314f 0%, #10253b 100%) !important;
            box-shadow: 0 30px 70px rgba(16, 31, 52, 0.22);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        [data-testid="column"]:has(.avant-login-panel-right) {
            padding: clamp(1.6rem, 3vw, 2.4rem) !important;
            background:
                linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(245, 250, 255, 0.96)) !important;
            box-shadow: 0 24px 60px rgba(31, 49, 70, 0.10);
            border: 1px solid rgba(210, 222, 236, 0.9);
        }

        .avant-chip {
            display: inline-flex;
            align-items: center;
            padding: 0.42rem 0.82rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.10);
            border: 1px solid rgba(255, 255, 255, 0.14);
            color: #dce9f8;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.18em;
            text-transform: uppercase;
        }

        .avant-title {
            margin: 1.25rem 0 0.8rem 0;
            color: #ffffff;
            font-size: clamp(2.05rem, 3vw, 3.2rem);
            line-height: 1.04;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }

        .avant-subtitle {
            max-width: 32rem;
            margin: 0 0 1.8rem 0;
            color: rgba(233, 242, 250, 0.82);
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
            color: #ffffff;
            font-size: 0.9rem;
            font-weight: 700;
            letter-spacing: 0.04em;
        }

        .avant-info-card-text {
            color: rgba(225, 236, 247, 0.76);
            font-size: 0.9rem;
            line-height: 1.5;
        }

        .avant-access-kicker {
            color: #1f3146;
            font-size: clamp(1.85rem, 2.3vw, 2.45rem);
            font-weight: 800;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            margin: 0 0 0.9rem 0;
        }

        .avant-access-message {
            margin-bottom: 1.15rem;
            padding: 0.95rem 1rem;
            border-radius: 18px;
            border: 1px solid #d2deec;
            background: linear-gradient(180deg, rgba(250, 253, 255, 0.98), rgba(241, 247, 255, 0.96));
            color: #556a82;
            line-height: 1.55;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.95);
        }

        .avant-access-message.error {
            border-color: rgba(240, 77, 99, 0.20);
            background: linear-gradient(180deg, rgba(255, 248, 249, 0.98), rgba(255, 240, 243, 0.96));
            color: #9c3850;
        }

        div[data-testid="stForm"] {
            border: 1px solid rgba(210, 222, 236, 0.95) !important;
            border-radius: 24px !important;
            padding: clamp(1.15rem, 2.1vw, 1.6rem) !important;
            background: rgba(255, 255, 255, 0.96) !important;
            box-shadow: 0 18px 38px rgba(31, 49, 70, 0.10) !important;
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
        }

        div[data-testid="stForm"] input::placeholder {
            color: #8aa0b8 !important;
            opacity: 1 !important;
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
            margin-top: 0.9rem;
            color: #6d8199;
            font-size: 0.86rem;
            line-height: 1.5;
        }

        @media (max-width: 980px) {
            [data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
            }

            [data-testid="column"]:has(.avant-login-panel-left),
            [data-testid="column"]:has(.avant-login-panel-right) {
                min-height: auto;
            }

            [data-testid="column"]:has(.avant-login-panel-left) {
                padding: 1.35rem !important;
            }

            [data-testid="column"]:has(.avant-login-panel-right) {
                padding: 1.25rem !important;
            }

            .avant-title {
                font-size: 1.8rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([1.15, 0.95], gap="large", vertical_alignment="center")

    with left_col:
        st.markdown(
            """
            <div class="avant-login-panel-left"></div>
            <div class="avant-chip">Avant Platform</div>
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
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        st.markdown(
            """
            <div class="avant-login-panel-right"></div>
            <div class="avant-access-kicker">Acesso</div>
            """,
            unsafe_allow_html=True,
        )
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


# =====================================================================
# AUTH
# =====================================================================
# AUTH
# =====================================================================
name = None
username = None
role = None
authentication_status = None
authenticator = None

auth_enabled = AUTH_ENABLED

if auth_enabled:
    try:
        from auth import setup_authentication, get_user_role

        authenticator, name, authentication_status, username = render_login_page()

        if authentication_status is not True:
            if authentication_status is False:
                log_warning_once(
                    "auth",
                    "invalid_credentials",
                    "Falha de autenticacao no login",
                    {"username": username or ""},
                    signature={"status": "invalid", "username": username or ""},
                )
            else:
                log_info_once(
                    "auth",
                    "login_screen",
                    "Tela de login exibida aguardando autenticacao",
                    {"auth_enabled": True},
                    signature={"status": "pending"},
                )
            st.stop()

        try:
            role = get_user_role()
        except Exception:
            role = "Usuario"

        log_success_once(
            "auth",
            "login_success",
            "Autenticacao realizada com sucesso",
            {"username": username or "", "name": name or "", "role": role or ""},
            signature={"username": username or "", "role": role or ""},
        )

    except Exception as e:
        log_error("auth", "Falha ao carregar autenticacao", {"error": str(e)})
        logger.warning("Falha ao carregar autenticacao: %s", e)
        st.error("Falha ao carregar a autenticacao. Verifique a configuracao do login.")
        st.stop()
else:
    name = "Usuario"
    role = "Acesso local"
    log_info_once(
        "auth",
        "auth_disabled",
        "Aplicacao iniciada sem autenticacao obrigatoria",
        {"auth_enabled": False},
        signature={"auth_enabled": False},
    )

apply_styles()
apply_stylesHEADER()

# REGISTRO DE LOGIN
# =====================================================================
if authentication_status:
    if "login_registrado" not in st.session_state:
        st.session_state["login_registrado"] = False

    if not st.session_state["login_registrado"]:
        registrar_login(
            username=username,
            nome=name,
            perfil=role,
        )
        st.session_state["login_registrado"] = True
        log_info(
            "auth",
            "Login registrado no arquivo de auditoria",
            {"username": username or "", "role": role or ""},
        )


# =====================================================================
# HEADER
# =====================================================================
render_header(
    logo_path=LOGO_PATH,
    app_name="Avant - Clima",
    version=APP_VERSION,
    user=name,
    role=role,
    username=username,
    authenticator=authenticator,
)

# =====================================================================
# DADOS BASE
# =====================================================================
gdf_full = load_shapefile_or_stop(GEO_PATH)


# Compatibilidade: a validaÃ§Ã£o agora acontece em load_shapefile_or_stop.
if False and gdf_full is None:
    st.error(f"Não foi possível carregar o shapefile em: {GEO_PATH}")
    st.stop()


# =====================================================================
# SIDEBAR
# =====================================================================
sidebar_data = render_sidebar(gdf_full)

tipo_dado = sidebar_data["tipo_dado"]
selected_uf = sidebar_data["selected_uf"]
selected_empresa = sidebar_data["selected_empresa"]
selected_fazenda = sidebar_data["selected_fazenda"]
selected_municipio = sidebar_data["selected_municipio"]
start_date = sidebar_data["start_date"]
end_date = sidebar_data["end_date"]
apply = sidebar_data["apply"]
log_container = sidebar_data.get("log_container")

init_applied_filters_state()

if apply:
    st.session_state["applied_filters_version"] = (
        int(st.session_state.get("applied_filters_version", 0)) + 1
    )
    st.session_state["applied_filters"] = {
        "tipo_dado": tipo_dado,
        "selected_uf": selected_uf,
        "selected_empresa": selected_empresa,
        "selected_fazenda": selected_fazenda,
        "selected_municipio": selected_municipio,
        "start_date": start_date,
        "end_date": end_date,
        "aplicar": True,
    }
    st.session_state["mostrar_tudo_shape"] = False
    st.session_state["mostrar_tudo_clima"] = False
    st.session_state["mostrar_tudo_resumo_mes"] = False
    log_info(
        "filters",
        "Filtros aplicados pelo usuario",
        {
            "tipo_dado": tipo_dado,
            "selected_uf": selected_uf or "",
            "selected_empresa": selected_empresa or "",
            "selected_fazenda": selected_fazenda or "",
            "selected_municipio": selected_municipio or "",
            "start_date": str(start_date),
            "end_date": str(end_date),
            "filters_version": int(st.session_state.get("applied_filters_version", 0)),
        },
    )

applied_filters = st.session_state["applied_filters"]
applied_filters_version = int(st.session_state.get("applied_filters_version", 0))
manual_zoom_refresh_version = int(st.session_state.get("manual_zoom_refresh_version", 0))
filters_applied = bool(applied_filters.get("aplicar", False))
st.session_state.aplicar = filters_applied


# =====================================================================
# FILTRO SHAPE
# =====================================================================
filtro_shape = {
    "tipo_dado": applied_filters.get("tipo_dado"),
    "selected_uf": applied_filters.get("selected_uf"),
    "selected_empresa": applied_filters.get("selected_empresa"),
    "selected_fazenda": applied_filters.get("selected_fazenda"),
    "selected_municipio": applied_filters.get("selected_municipio"),
}

start_date_applied = applied_filters.get("start_date")
end_date_applied = applied_filters.get("end_date")

map_refresh_token = get_map_refresh_token(
    {
        **filtro_shape,
        "start_date": start_date_applied,
        "end_date": end_date_applied,
        "aplicar": filters_applied,
        "filters_version": applied_filters_version,
        "manual_zoom_refresh_version": manual_zoom_refresh_version,
    }
)

gdf_filtered = gdf_full.copy()
if filters_applied:
    gdf_filtered = filter_gdf(gdf_full, filtro_shape)
    log_success_once(
        "filters",
        "shape_filter_result",
        "Filtro espacial aplicado sobre a base geoespacial",
        {
            "tipo_dado": filtro_shape.get("tipo_dado"),
            "records": int(len(gdf_filtered)),
        },
        signature={
            "tipo_dado": filtro_shape.get("tipo_dado"),
            "selected_uf": filtro_shape.get("selected_uf"),
            "selected_empresa": filtro_shape.get("selected_empresa"),
            "selected_fazenda": filtro_shape.get("selected_fazenda"),
            "selected_municipio": filtro_shape.get("selected_municipio"),
            "records": int(len(gdf_filtered)),
            "filters_version": applied_filters_version,
        },
    )
else:
    log_info_once(
        "filters",
        "waiting_apply",
        "Aplicacao aguardando acao de filtros na sidebar",
        {"records": int(len(gdf_full))},
        signature={"waiting": True, "records": int(len(gdf_full))},
    )

shared_map_viewport = None
viewport_gdf = gdf_filtered if filters_applied else gdf_full
viewport_tipo_dado = filtro_shape["tipo_dado"] if filters_applied else "Todos os Dados"

if viewport_gdf is not None and not viewport_gdf.empty:
    try:
        shared_map_viewport = build_map_viewport(viewport_gdf, viewport_tipo_dado)
        log_success_once(
            "filters",
            "shared_viewport_ready",
            "Viewport compartilhado calculado para sincronizar os mapas",
            {
                "tipo_dado": viewport_tipo_dado,
                "records": int(len(viewport_gdf)),
                "manual_zoom_refresh_version": manual_zoom_refresh_version,
                "manual_zoom_last_source": str(st.session_state.get("manual_zoom_last_source", "")),
                **build_viewport_log_details(
                    shared_map_viewport,
                    filters_version=applied_filters_version,
                ),
            },
            signature={
                "tipo_dado": viewport_tipo_dado,
                "records": int(len(viewport_gdf)),
                "manual_zoom_refresh_version": manual_zoom_refresh_version,
                "manual_zoom_last_source": str(st.session_state.get("manual_zoom_last_source", "")),
                **build_viewport_log_details(
                    shared_map_viewport,
                    filters_version=applied_filters_version,
                ),
            },
        )
    except Exception as exc:
        log_warning_once(
            "filters",
            "shared_viewport_unavailable",
            "Nao foi possivel preparar o viewport compartilhado dos mapas",
            {
                "tipo_dado": viewport_tipo_dado,
                "records": int(len(viewport_gdf)),
                "error": str(exc),
                "filters_version": applied_filters_version,
            },
            signature={
                "tipo_dado": viewport_tipo_dado,
                "records": int(len(viewport_gdf)),
                "error": str(exc),
                "filters_version": applied_filters_version,
            },
        )
else:
    log_warning_once(
        "filters",
        "shared_viewport_empty",
        "Viewport compartilhado nao foi gerado por ausencia de geometrias",
        {
            "tipo_dado": viewport_tipo_dado,
            "filters_version": applied_filters_version,
        },
        signature={
            "tipo_dado": viewport_tipo_dado,
            "filters_version": applied_filters_version,
            "empty": True,
        },
    )


# =====================================================================
# LOAD CSV VIA SERVICE
# =====================================================================
df_csv = None

if filters_applied:
    try:
        filtro_clima = {
            "tipo_dado": filtro_shape["tipo_dado"],
            "selected_uf": filtro_shape["selected_uf"],
            "selected_empresa": filtro_shape["selected_empresa"],
            "selected_fazenda": filtro_shape["selected_fazenda"],
            "selected_municipio": filtro_shape["selected_municipio"],
            "start_date": start_date_applied,
            "end_date": end_date_applied,
            "filters_version": applied_filters_version,
            "log_container": log_container,
        }

        log_info(
            "climate",
            "Iniciando carregamento dos dados climaticos",
            {
                "start_date": str(start_date_applied),
                "end_date": str(end_date_applied),
                "tipo_dado": filtro_shape["tipo_dado"],
            },
        )
        with st.spinner("Carregando dados climáticos..."):
            df_csv = load_climate_data(filtro_clima)

        if df_csv is None or df_csv.empty:
            log_warning_once(
                "climate",
                "empty_dataset_after_load",
                "Carga climatica concluida sem registros validos",
                {
                    "tipo_dado": filtro_shape["tipo_dado"],
                    "start_date": str(start_date_applied),
                    "end_date": str(end_date_applied),
                },
                signature={
                    "tipo_dado": filtro_shape["tipo_dado"],
                    "start_date": str(start_date_applied),
                    "end_date": str(end_date_applied),
                    "records": 0,
                    "filters_version": applied_filters_version,
                },
            )
        else:
            log_success_once(
                "climate",
                "dataset_loaded",
                "Dados climaticos carregados com sucesso",
                {
                    "records": int(len(df_csv)),
                    "columns": int(len(df_csv.columns)),
                },
                signature={
                    "records": int(len(df_csv)),
                    "columns": int(len(df_csv.columns)),
                    "filters_version": applied_filters_version,
                },
            )

    except Exception as e:
        logger.error("Erro no carregamento dos CSVs via climate_service: %s", e)
        log_error(
            "climate",
            "Erro no carregamento dos dados climaticos",
            {
                "error": str(e),
                "tipo_dado": filtro_shape["tipo_dado"],
                "start_date": str(start_date_applied),
                "end_date": str(end_date_applied),
            },
        )
        if log_container:
            log_container.error(f"❌ Erro geral no carregamento: {e}")
        else:
            st.error(f"❌ Erro geral no carregamento: {e}")
        df_csv = None


# =====================================================================
# TABS
# =====================================================================
TAB_LABELS = [
    "Mapa Principal",
    "Dados Shape",
    "Dados de Clima",
    "Analise Avancada",
    "Previsao do Tempo (Teste)",
    "Tendencia Climatica (Teste)",
]

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    TAB_LABELS,
)

with tab1:
    render_tab_theme_marker("mapa")
    render_tab_mapa(
        gdf_full,
        gdf_filtered,
        filtro_shape,
        refresh_token=map_refresh_token,
        filters_version=applied_filters_version,
        shared_viewport=shared_map_viewport,
    )

with tab2:
    render_tab_theme_marker("shape")
    render_tab_shape(gdf_filtered, filters_version=applied_filters_version)

with tab3:
    render_tab_theme_marker("clima")
    render_tab_clima(df_csv, filters_version=applied_filters_version)

with tab4:
    render_tab_theme_marker("analise")
    render_tab_analise(
        df_csv,
        tipo_dado=filtro_shape["tipo_dado"],
        selected_uf=filtro_shape["selected_uf"],
        selected_municipio=filtro_shape["selected_municipio"],
        selected_empresa=filtro_shape["selected_empresa"],
        selected_fazenda=filtro_shape["selected_fazenda"],
        start_date=start_date_applied,
        end_date=end_date_applied,
        filters_version=applied_filters_version,
    )

with tab5:
    render_tab_theme_marker("previsao")
    render_tab_previsao(
        gdf_filtered=gdf_filtered,
        selected_empresa=filtro_shape["selected_empresa"],
        selected_fazenda=filtro_shape["selected_fazenda"],
        selected_municipio=filtro_shape["selected_municipio"],
        selected_uf=filtro_shape["selected_uf"],
        logo_path=LOGO_PATH,
        filters_version=applied_filters_version,
    )

with tab6:
    render_tab_theme_marker("tendencia")
    render_tab_tendencia_climatica(
        gdf_filtered=gdf_filtered,
        selected_empresa=filtro_shape["selected_empresa"],
        selected_fazenda=filtro_shape["selected_fazenda"],
        selected_municipio=filtro_shape["selected_municipio"],
        selected_uf=filtro_shape["selected_uf"],
        logo_path=LOGO_PATH,
        filters_version=applied_filters_version,
    )

