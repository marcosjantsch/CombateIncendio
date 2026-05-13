import base64
from io import BytesIO
from pathlib import Path
from datetime import date

import streamlit as st
from PIL import Image

from core.settings import LOGO_PATH, TIPOS_DADO, ANOS_DISPONIVEIS, MESES_DISPONIVEIS
from services.log_service import export_logs_csv_bytes, get_log_download_filename


def safe_unique(gdf, col):
    if col not in gdf.columns:
        return []
    return sorted([str(x) for x in gdf[col].dropna().unique()])


def _section_header(title: str, subtitle: str = "") -> None:
    subtitle_html = (
        f'<div class="sidebar-section-subtitle">{subtitle}</div>' if subtitle else ""
    )
    st.markdown(
        (
            '<div class="sidebar-section-header">'
            f'<div class="sidebar-section-title">{title}</div>'
            f"{subtitle_html}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _summary_chip(label: str, value: str) -> str:
    return (
        '<div class="sidebar-summary-chip">'
        f'<div class="sidebar-summary-label">{label}</div>'
        f'<div class="sidebar-summary-value">{value}</div>'
        "</div>"
    )


@st.cache_data(show_spinner=False)
def _image_to_data_uri(path: str) -> str:
    logo_path = Path(path)
    if not logo_path.exists():
        return ""

    with Image.open(logo_path) as img:
        image = img.convert("RGBA")
        buffer = BytesIO()
        image.save(buffer, format="PNG")

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _bytes_to_data_uri(data: bytes, mime: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _render_log_download_shortcut() -> None:
    logo_src = _image_to_data_uri(LOGO_PATH)
    download_href = _bytes_to_data_uri(
        export_logs_csv_bytes(),
        "text/csv;charset=utf-8",
    )
    file_name = get_log_download_filename()

    logo_markup = (
        f'<img src="{logo_src}" alt="Avant log" class="sidebar-log-download-logo" />'
        if logo_src
        else '<div class="sidebar-log-download-fallback">AV</div>'
    )

    st.markdown(
        f"""
        <div class="sidebar-log-download-card">
            <a
                class="sidebar-log-download-link"
                href="{download_href}"
                download="{file_name}"
                title="Baixar log da sessão atual"
            >
                {logo_markup}
            </a>
            <div class="sidebar-log-download-caption">Baixar log da sessão</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(gdf_full):
    with st.sidebar:
        st.image(LOGO_PATH, width=60)
        st.markdown(
            (
                '<div class="sidebar-brand-card">'
                '<div class="sidebar-brand-kicker">Painel de controle</div>'
                '<div class="sidebar-brand-title">Selecione a opção</div>'
                '<div class="sidebar-brand-subtitle">Filtros espaciais e período de análise</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    filtros_container = st.sidebar.container(border=True)
    with filtros_container:
        _section_header("Filtro principal", "Defina a abrangência dos dados")
        tipo_dado = st.selectbox("Tipo de Dados", TIPOS_DADO)

    selected_uf = None
    selected_empresa = None
    selected_fazenda = None
    selected_municipio = None

    with filtros_container:
        if tipo_dado == "Dados por Estado":
            ufs = safe_unique(gdf_full, "UF")
            selected_uf = st.selectbox("Selecione UF", ufs) if ufs else None

        elif tipo_dado == "Dados por Empresa":
            empresas = safe_unique(gdf_full, "EMPRESA")
            selected_empresa = (
                st.selectbox("Selecione Empresa", empresas) if empresas else None
            )

        elif tipo_dado == "Dados Empresa/Fazenda":
            empresas = safe_unique(gdf_full, "EMPRESA")
            selected_empresa = (
                st.selectbox("Selecione Empresa", empresas) if empresas else None
            )

            if (
                selected_empresa
                and "EMPRESA" in gdf_full.columns
                and "FAZENDA" in gdf_full.columns
            ):
                gdf_emp = gdf_full[gdf_full["EMPRESA"].astype(str) == str(selected_empresa)]
                fazendas = safe_unique(gdf_emp, "FAZENDA")
                selected_fazenda = (
                    st.selectbox("Selecione Fazenda", fazendas)
                    if fazendas
                    else None
                )

        elif tipo_dado == "Dados por Município":
            ufs = safe_unique(gdf_full, "UF")
            selected_uf = st.selectbox("Selecione UF", ufs) if ufs else None

            if (
                selected_uf
                and "UF" in gdf_full.columns
                and "MUNICIPIO" in gdf_full.columns
            ):
                gdf_uf = gdf_full[gdf_full["UF"].astype(str) == str(selected_uf)]
                municipios = safe_unique(gdf_uf, "MUNICIPIO")
                selected_municipio = (
                    st.selectbox("Selecione Município", municipios)
                    if municipios
                    else None
                )

    periodo_container = st.sidebar.container(border=True)
    with periodo_container:
        _section_header("Período mensal", "Delimite a janela temporal")

        col1, col2 = st.columns(2)
        with col1:
            start_mes_nome = st.selectbox(
                "Mês inicial", list(MESES_DISPONIVEIS.keys()), index=0
            )
        with col2:
            start_ano = st.selectbox(
                "Ano inicial",
                ANOS_DISPONIVEIS,
                index=ANOS_DISPONIVEIS.index(2026),
            )

        col3, col4 = st.columns(2)
        with col3:
            end_mes_nome = st.selectbox(
                "Mês final", list(MESES_DISPONIVEIS.keys()), index=11
            )
        with col4:
            end_ano = st.selectbox(
                "Ano final",
                ANOS_DISPONIVEIS,
                index=ANOS_DISPONIVEIS.index(2026),
            )

    start_date = date(start_ano, MESES_DISPONIVEIS[start_mes_nome], 1)
    end_date = date(end_ano, MESES_DISPONIVEIS[end_mes_nome], 1)

    action_container = st.sidebar.container(border=True)
    with action_container:
        apply = st.button("Aplicar Filtros")
        st.markdown(
            (
                '<div class="sidebar-summary-grid">'
                f'{_summary_chip("Modo", tipo_dado.replace("Dados ", "").replace("/", " / "))}'
                f'{_summary_chip("Janela", f"{start_mes_nome[:3]}/{str(start_ano)[-2:]} - {end_mes_nome[:3]}/{str(end_ano)[-2:]}")}'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        log_container = st.container() if apply else st.empty()

    with st.sidebar:
        _render_log_download_shortcut()

    return {
        "tipo_dado": tipo_dado,
        "selected_uf": selected_uf,
        "selected_empresa": selected_empresa,
        "selected_fazenda": selected_fazenda,
        "selected_municipio": selected_municipio,
        "start_date": start_date,
        "end_date": end_date,
        "apply": apply,
        "log_container": log_container,
    }
