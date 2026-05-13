# tabs/tab_mapa.py
import datetime as dt
from typing import Dict, List

import numpy as np
import pandas as pd
import folium
import requests
import streamlit as st
from branca.element import Element

from folium.plugins import Fullscreen, MiniMap, MeasureControl, MousePosition
from streamlit_folium import st_folium

from core.settings import MAX_FEATURES_FULL_MAP
from core.theme_palette import get_theme_palette
from services.log_service import log_error_once, log_info, log_success_once, log_warning_once


DEFAULT_DARK_TILES = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
DEFAULT_DARK_ATTR = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
    'contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
)
NASA_LOOKBACK_DAYS = 10
NASA_REQUEST_TIMEOUT = 8
NASA_MAX_NATIVE_ZOOM = 9
SATELLITE_OVERLAY_OPTIONS = [
    {
        "slug": "terra_truecolor",
        "label": "NASA True Color",
        "layer_name": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "tile_matrix_set": "GoogleMapsCompatible_Level9",
        "preferred_ext": "jpg",
    },
    {
        "slug": "terra_false",
        "label": "NASA Terrafalse",
        "layer_name": "MODIS_Terra_CorrectedReflectance_Bands721",
        "tile_matrix_set": "GoogleMapsCompatible_Level9",
        "preferred_ext": "jpg",
    },
    {
        "slug": "world_dream",
        "label": "Satélite World Dream",
        "layer_name": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "tile_matrix_set": "GoogleMapsCompatible_Level9",
        "preferred_ext": "jpg",
    },
]
ZOOM_CONFIG_BY_TYPE = {
    "Todos os Dados": {"default_zoom": 4, "max_zoom": 6, "padding_ratio": 0.24},
    "Dados por Estado": {"default_zoom": 5, "max_zoom": 7, "padding_ratio": 0.20},
    "Dados por Empresa": {"default_zoom": 6, "max_zoom": 9, "padding_ratio": 0.16},
    "Dados Empresa/Fazenda": {"default_zoom": 9, "max_zoom": 12, "padding_ratio": 0.08},
    "Dados por Município": {"default_zoom": 8, "max_zoom": 10, "padding_ratio": 0.12},
}


def _get_zoom_config(tipo_exib: str) -> dict:
    return ZOOM_CONFIG_BY_TYPE.get(
        str(tipo_exib or "Todos os Dados"),
        ZOOM_CONFIG_BY_TYPE["Todos os Dados"],
    )


def _expand_bounds(minx, miny, maxx, maxy, padding_ratio: float):
    width = float(maxx - minx)
    height = float(maxy - miny)
    base_span = max(width, height, 0.02)
    pad_x = max(width * padding_ratio, base_span * padding_ratio)
    pad_y = max(height * padding_ratio, base_span * padding_ratio)
    return (
        float(minx - pad_x),
        float(miny - pad_y),
        float(maxx + pad_x),
        float(maxy + pad_y),
    )


def _apply_filter_zoom(m: folium.Map, bounds, tipo_exib: str) -> None:
    minx, miny, maxx, maxy = bounds
    zoom_cfg = _get_zoom_config(tipo_exib)
    exp_minx, exp_miny, exp_maxx, exp_maxy = _expand_bounds(
        minx,
        miny,
        maxx,
        maxy,
        padding_ratio=float(zoom_cfg["padding_ratio"]),
    )
    m.fit_bounds(
        [[exp_miny, exp_minx], [exp_maxy, exp_maxx]],
        max_zoom=int(zoom_cfg["max_zoom"]),
    )


def build_map_viewport(gdf_map, tipo_exib: str) -> dict:
    minx, miny, maxx, maxy = [float(v) for v in gdf_map.total_bounds]
    if any(pd.isna(v) for v in [minx, miny, maxx, maxy]):
        raise ValueError("nan_bounds")

    zoom_cfg = _get_zoom_config(tipo_exib)
    center_lat = float((miny + maxy) / 2)
    center_lon = float((minx + maxx) / 2)
    exp_minx, exp_miny, exp_maxx, exp_maxy = _expand_bounds(
        minx,
        miny,
        maxx,
        maxy,
        padding_ratio=float(zoom_cfg["padding_ratio"]),
    )

    return {
        "tipo_dado": str(tipo_exib or "Todos os Dados"),
        "zoom_default": int(zoom_cfg["default_zoom"]),
        "max_zoom": int(zoom_cfg["max_zoom"]),
        "padding_ratio": float(zoom_cfg["padding_ratio"]),
        "bounds": {
            "minx": round(minx, 6),
            "miny": round(miny, 6),
            "maxx": round(maxx, 6),
            "maxy": round(maxy, 6),
        },
        "fit_bounds": [
            [round(exp_miny, 6), round(exp_minx, 6)],
            [round(exp_maxy, 6), round(exp_maxx, 6)],
        ],
        "center_lat": round(center_lat, 6),
        "center_lon": round(center_lon, 6),
    }


def apply_viewport_to_map(m: folium.Map, viewport: dict) -> None:
    fit_bounds = viewport.get("fit_bounds") or []
    if len(fit_bounds) != 2:
        raise ValueError("invalid_fit_bounds")

    m.fit_bounds(
        fit_bounds,
        max_zoom=int(viewport.get("max_zoom", 10)),
    )


def build_viewport_log_details(viewport: dict, filters_version: int = 0) -> dict:
    return {
        "zoom_default": int(viewport.get("zoom_default", 0)),
        "max_zoom": int(viewport.get("max_zoom", 0)),
        "bounds": dict(viewport.get("bounds") or {}),
        "center_lat": round(float(viewport.get("center_lat", 0.0)), 6),
        "center_lon": round(float(viewport.get("center_lon", 0.0)), 6),
        "filters_version": int(filters_version or 0),
    }


def _trigger_manual_zoom_refresh(source_tab: str, filters_version: int = 0) -> None:
    next_version = int(st.session_state.get("manual_zoom_refresh_version", 0)) + 1
    st.session_state["manual_zoom_refresh_version"] = next_version
    st.session_state["manual_zoom_last_source"] = source_tab
    log_info(
        "maps",
        "Atualizacao manual de zoom solicitada",
        {
            "source_tab": source_tab,
            "manual_zoom_refresh_version": next_version,
            "filters_version": int(filters_version or 0),
        },
    )


def render_manual_zoom_button(source_tab: str, filters_version: int = 0) -> None:
    st.button(
        "Atualizar zoom",
        key=f"{source_tab}_manual_zoom_refresh_button",
        type="secondary",
        help="Ferramenta temporaria para reaplicar manualmente o enquadramento do mapa.",
        on_click=_trigger_manual_zoom_refresh,
        args=(source_tab, int(filters_version or 0)),
    )


def _ensure_satellite_overlay_cache() -> None:
    st.session_state.setdefault("map_satellite_overlay_cache", {})


def _candidate_nasa_dates(max_days: int = NASA_LOOKBACK_DAYS) -> List[str]:
    today = dt.datetime.utcnow().date()
    return [
        (today - dt.timedelta(days=offset)).strftime("%Y-%m-%d")
        for offset in range(max_days + 1)
    ]


def _build_nasa_tile_url(layer_name: str, date_ref: str, tile_matrix_set: str, ext: str) -> str:
    return (
        "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
        f"{layer_name}/default/{date_ref}/"
        f"{tile_matrix_set}/{{z}}/{{y}}/{{x}}.{ext}"
    )


def _nasa_tile_exists(url_template: str, timeout: int = NASA_REQUEST_TIMEOUT) -> bool:
    try:
        test_url = url_template.format(z=1, x=0, y=0)
        response = requests.head(test_url, timeout=timeout, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "").lower()
            return ("image" in content_type) or (content_type == "")

        if response.status_code in (403, 405):
            response = requests.get(test_url, timeout=timeout, stream=True, allow_redirects=True)
            content_type = response.headers.get("Content-Type", "").lower()
            return response.status_code == 200 and (("image" in content_type) or (content_type == ""))

        return False
    except Exception:
        return False


def _resolve_satellite_overlay(layer_def: Dict[str, str]) -> Dict[str, str]:
    preferred_ext = layer_def["preferred_ext"]
    fallback_ext = "png" if preferred_ext == "jpg" else "jpg"

    for date_ref in _candidate_nasa_dates():
        for ext in [preferred_ext, fallback_ext]:
            url_template = _build_nasa_tile_url(
                layer_name=layer_def["layer_name"],
                date_ref=date_ref,
                tile_matrix_set=layer_def["tile_matrix_set"],
                ext=ext,
            )
            if _nasa_tile_exists(url_template):
                return {
                    "status": "ok",
                    "slug": layer_def["slug"],
                    "label": layer_def["label"],
                    "data": date_ref,
                    "ext": ext,
                    "url_template": url_template,
                }

    return {
        "status": "sem_imagem",
        "slug": layer_def["slug"],
        "label": layer_def["label"],
    }


def _get_satellite_overlay_result(layer_def: Dict[str, str]) -> Dict[str, str]:
    _ensure_satellite_overlay_cache()
    cache = st.session_state["map_satellite_overlay_cache"]
    cache_key = str(layer_def["slug"])
    if cache_key in cache:
        return cache[cache_key]

    result = _resolve_satellite_overlay(layer_def)
    cache[cache_key] = result
    return result


def _build_satellite_status_line(selected_layers: List[Dict[str, str]]) -> str:
    if not selected_layers:
        return "Imagens atuais: nenhuma sobreposição ativa."

    items = []
    for layer in selected_layers:
        status = str(layer.get("status", ""))
        if status == "ok":
            items.append(f'{layer["label"]}: {layer.get("data", "sem data")}')
        elif status == "sem_imagem":
            items.append(f'{layer["label"]}: indisponível')
        else:
            items.append(f'{layer["label"]}: erro')

    return "Imagens atuais: " + " | ".join(items)


def _build_satellite_signature(selected_layers: List[Dict[str, str]]) -> str:
    if not selected_layers:
        return "no_satellite_overlay"

    parts = []
    for layer in selected_layers:
        parts.append(
            ":".join(
                [
                    str(layer.get("slug", "")),
                    str(layer.get("status", "")),
                    str(layer.get("data", "")),
                ]
            )
        )
    return "|".join(parts)


def _add_selected_satellite_layers(m: folium.Map, selected_layers: List[Dict[str, str]]) -> None:
    for layer in selected_layers:
        if layer.get("status") != "ok":
            continue

        folium.TileLayer(
            tiles=layer["url_template"],
            attr="NASA GIBS",
            name=f'{layer["label"]} {layer.get("data", "")}'.strip(),
            overlay=True,
            control=True,
            show=True,
            opacity=0.66,
            max_zoom=22,
            max_native_zoom=NASA_MAX_NATIVE_ZOOM,
        ).add_to(m)


def render_compact_summary_cards(summary_items: List[Dict[str, str]]) -> None:
    st.markdown(
        """
        <style>
        .avant-map-summary-card {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(244, 248, 253, 0.98));
            border: 1px solid rgba(210, 222, 236, 0.9);
            border-radius: 16px;
            padding: 0.7rem 0.85rem 0.78rem;
            box-shadow: 0 12px 28px rgba(22, 47, 76, 0.08);
            min-height: 84px;
        }
        .avant-map-summary-label {
            display: block;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #6f849b;
            margin-bottom: 0.35rem;
        }
        .avant-map-summary-value {
            display: block;
            font-size: 1.6rem;
            line-height: 1.1;
            font-weight: 700;
            color: #1f3146;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(len(summary_items))
    for column, item in zip(columns, summary_items):
        column.markdown(
            (
                '<div class="avant-map-summary-card">'
                f'<span class="avant-map-summary-label">{item["label"]}</span>'
                f'<span class="avant-map-summary-value">{item["value"]}</span>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def _inject_map_theme(m: folium.Map) -> None:
    palette = get_theme_palette()
    css = """
    <style>
    .leaflet-container {{
        background: {map_background} !important;
        font-family: "Segoe UI", Arial, sans-serif;
    }}

    .leaflet-control-zoom a,
    .leaflet-control-layers-toggle,
    .leaflet-bar a {{
        background: {map_control} !important;
        color: {map_text} !important;
        border-color: {panel_border} !important;
    }}

    .leaflet-bar,
    .leaflet-control-layers,
    .leaflet-control-attribution,
    .leaflet-control-scale,
    .leaflet-control-minimap {{
        background: {map_surface} !important;
        border: 1px solid {panel_border} !important;
        border-radius: 12px !important;
        box-shadow: 0 14px 28px rgba(0, 0, 0, 0.35) !important;
    }}

    .leaflet-control-layers-expanded {{
        padding: 12px 14px !important;
        color: {map_text} !important;
        min-width: 18rem;
        max-width: min(24rem, 32vw);
        font-size: clamp(0.88rem, 0.76vw, 1rem);
        line-height: 1.45;
    }}

    .leaflet-control-layers-list span,
    .leaflet-control-layers label {{
        color: {map_text} !important;
        font-size: inherit !important;
        line-height: inherit !important;
    }}

    .leaflet-control-layers-base label,
    .leaflet-control-layers-overlays label {{
        display: flex !important;
        align-items: center;
        gap: 0.38rem;
        margin-bottom: 0.38rem !important;
    }}

    .leaflet-control-layers-base input,
    .leaflet-control-layers-overlays input {{
        transform: scale(1.05);
        accent-color: {map_accent};
    }}

    .leaflet-control-layers-base label:hover,
    .leaflet-control-layers-overlays label:hover {{
        color: {map_accent_strong} !important;
    }}

    .leaflet-control-layers-separator {{
        border-top-color: {panel_border} !important;
    }}

    .leaflet-tooltip {{
        background: {map_tooltip} !important;
        color: {map_text} !important;
        border: 1px solid {panel_border} !important;
        border-radius: 10px !important;
        box-shadow: 0 16px 32px rgba(0, 0, 0, 0.32) !important;
    }}

    .leaflet-tooltip:before {{
        border-top-color: {map_tooltip} !important;
    }}

    .leaflet-popup-content-wrapper,
    .leaflet-popup-tip {{
        background: {map_tooltip} !important;
        color: {map_text} !important;
    }}

    .leaflet-popup-content-wrapper {{
        border: 1px solid {panel_border} !important;
        border-radius: 14px !important;
        box-shadow: 0 20px 36px rgba(0, 0, 0, 0.38) !important;
    }}

    .leaflet-popup-content {{
        margin: 12px 14px !important;
        line-height: 1.45 !important;
    }}

    .leaflet-popup-content h4 {{
        margin: 0 0 8px 0 !important;
        color: {map_accent_strong} !important;
        font-size: 14px !important;
    }}

    .leaflet-popup-close-button {{
        color: {map_text_soft} !important;
    }}

    .leaflet-control-attribution,
    .leaflet-control-attribution a,
    .leaflet-control-scale-line,
    .leaflet-control-mouseposition {{
        color: {map_text_soft} !important;
    }}

    .leaflet-control-scale-line {{
        background: {map_surface} !important;
        border-color: {panel_border} !important;
    }}
    </style>
    """.format(
        map_background=palette["map_background"],
        map_control=palette["map_control"],
        map_text=palette["map_text"],
        panel_border=palette["panel_border"],
        map_surface=palette["map_surface"],
        map_accent=palette["map_accent"],
        map_accent_strong=palette["map_accent_strong"],
        map_tooltip=palette["map_tooltip"],
        map_text_soft=palette["map_text_soft"],
    )
    m.get_root().header.add_child(Element(css))


def _add_basemaps(m: folium.Map) -> None:
    """
    Adiciona multiplas camadas de mapa base.
    """

    folium.TileLayer(
        tiles=DEFAULT_DARK_TILES,
        attr=DEFAULT_DARK_ATTR,
        name="CartoDB Dark Matter",
        show=False,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="OpenStreetMap",
        name="OpenStreetMap",
        show=False,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Esri World Imagery",
        show=True,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Esri World Topo",
        show=False,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr="OpenTopoMap",
        name="OpenTopoMap",
        show=False,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://tiles.stadiamaps.com/tiles/outdoors/{z}/{x}/{y}{r}.png",
        attr="Stadia Maps",
        name="Stadia Outdoors",
        show=False,
        control=True,
    ).add_to(m)

def _get_cor_exibicao(tipo_exib: str) -> str:
    color_map = {
        "Todos os Dados": "#98FF6B",
        "Dados por Estado": "#46E08F",
        "Dados por Empresa": "#5AF7C0",
        "Dados Empresa/Fazenda": "#7CFFB2",
        "Dados por Município": "#2F8F5B",
    }
    return color_map.get(tipo_exib, "#6EFFB3")


def _preparar_gdf_exibicao(gdf_map):
    """
    Padroniza campos numericos e textos auxiliares para tooltip.
    """
    gdf_map = gdf_map.copy()

    for col in ["AREA_T", "AREA_PRODU"]:
        if col in gdf_map.columns:
            gdf_map[col] = pd.to_numeric(gdf_map[col], errors="coerce").round(1)

    if "AREA_T" in gdf_map.columns:
        gdf_map["AREA_T_TXT"] = gdf_map["AREA_T"].apply(
            lambda x: f"{x:.1f} ha" if pd.notna(x) else "N/A"
        )

    if "AREA_PRODU" in gdf_map.columns:
        gdf_map["AREA_PRODU_TXT"] = gdf_map["AREA_PRODU"].apply(
            lambda x: f"{x:.1f} ha" if pd.notna(x) else "N/A"
        )

    return gdf_map


def _criar_tooltip(gdf_map):
    tooltip_fields = [
        c
        for c in [
            "UF",
            "MUNICIPIO",
            "EMPRESA",
            "FAZENDA",
            "AREA_T_TXT",
            "AREA_PRODU_TXT",
        ]
        if c in gdf_map.columns
    ]

    tooltip_aliases_map = {
        "UF": "UF",
        "MUNICIPIO": "Município",
        "EMPRESA": "Empresa",
        "FAZENDA": "Fazenda",
        "AREA_T_TXT": "Área Total",
        "AREA_PRODU_TXT": "Área Produtiva",
    }
    tooltip_aliases = [tooltip_aliases_map.get(c, c) for c in tooltip_fields]

    return tooltip_fields, tooltip_aliases


def _build_map_key(
    filtro: dict,
    gdf_map,
    usar_geometria_original: bool,
    mostrar_preenchimento: bool,
    imagery_signature: str = "",
    refresh_token: str = "",
) -> str:
    partes = [
        "mapa_principal",
        str(filtro.get("tipo_dado", "todos")),
        str(filtro.get("selected_uf", "")),
        str(filtro.get("selected_empresa", "")),
        str(filtro.get("selected_fazenda", "")),
        str(filtro.get("selected_municipio", "")),
        f"orig_{int(bool(usar_geometria_original))}",
        f"fill_{int(bool(mostrar_preenchimento))}",
        str(imagery_signature or ""),
        f"n_{len(gdf_map)}",
        str(refresh_token or ""),
    ]

    if not gdf_map.empty:
        try:
            minx, miny, maxx, maxy = gdf_map.total_bounds
            partes.extend(
                [
                    f"{minx:.5f}",
                    f"{miny:.5f}",
                    f"{maxx:.5f}",
                    f"{maxy:.5f}",
                ]
            )
        except Exception:
            pass

    return "_".join(partes)


def render_tab_mapa(
    gdf_full,
    gdf_filtered,
    filtro,
    refresh_token: str = "",
    filters_version: int = 0,
    shared_viewport=None,
):
    title_col, action_col = st.columns([0.82, 0.18], vertical_alignment="center")
    with title_col:
        st.markdown('<div class="section-title">Mapa Principal</div>', unsafe_allow_html=True)
    with action_col:
        render_manual_zoom_button("mapa_principal", filters_version=filters_version)

    palette = get_theme_palette()
    manual_zoom_refresh_version = int(st.session_state.get("manual_zoom_refresh_version", 0))

    aplicar = st.session_state.get("aplicar", False)
    gdf_map = gdf_filtered if aplicar else gdf_full
    tipo_exib = filtro["tipo_dado"] if aplicar else "Todos os Dados"

    if gdf_map is None or gdf_map.empty:
        log_warning_once(
            "tab_mapa",
            "empty_geometry",
            "Mapa Principal sem geometrias para renderizacao",
            {
                "aplicar": bool(aplicar),
                "tipo_dado": tipo_exib,
                "filters_version": int(filters_version or 0),
            },
            signature={
                "aplicar": bool(aplicar),
                "tipo_dado": tipo_exib,
                "empty": True,
                "filters_version": int(filters_version or 0),
            },
        )
        st.info("Nenhuma geometria disponível para exibição no mapa.")
        return

    gdf_map = gdf_map.copy()

    overlay_col1, overlay_col2, overlay_col3, overlay_col4 = st.columns([1.2, 1.2, 1.25, 1.1])
    with overlay_col1:
        overlay_truecolor = st.checkbox(
            "NASA True Color",
            value=False,
            key="mapa_overlay_truecolor",
        )
    with overlay_col2:
        overlay_terrafalse = st.checkbox(
            "NASA Terrafalse",
            value=False,
            key="mapa_overlay_terrafalse",
        )
    with overlay_col3:
        overlay_worlddream = st.checkbox(
            "Satélite World Dream",
            value=False,
            key="mapa_overlay_worlddream",
        )
    with overlay_col4:
        usar_geometria_original = st.checkbox(
            "Exibir polígonos sem simplificação",
            value=False,
            key="mapa_sem_simplificacao",
            help="Mostra as geometrias originais do shapefile. Pode deixar o mapa mais pesado.",
        )

    option_col1, option_col2 = st.columns([1, 1])
    with option_col1:
        mostrar_preenchimento = st.checkbox(
            "Preencher polígonos",
            value=True,
            key="mapa_preenchimento",
            help="Quando desmarcado, exibe apenas o contorno das feições.",
        )
    with option_col2:
        st.caption("As imagens atuais são opcionais e entram como sobreposição no mapa principal.")

    if usar_geometria_original and "__geometry_original__" in gdf_map.columns:
        gdf_map["geometry"] = gdf_map["__geometry_original__"]

    area_total_mapa = (
        float(pd.to_numeric(gdf_map["AREA_T"], errors="coerce").sum())
        if "AREA_T" in gdf_map.columns
        else np.nan
    )
    area_produ_mapa = (
        float(pd.to_numeric(gdf_map["AREA_PRODU"], errors="coerce").sum())
        if "AREA_PRODU" in gdf_map.columns
        else np.nan
    )
    n_municipios = (
        int(gdf_map["MUNICIPIO"].dropna().astype(str).nunique())
        if "MUNICIPIO" in gdf_map.columns
        else 0
    )
    n_fazendas = (
        int(gdf_map["FAZENDA"].dropna().astype(str).nunique())
        if "FAZENDA" in gdf_map.columns
        else 0
    )
    n_feicoes = len(gdf_map)

    if len(gdf_map) > MAX_FEATURES_FULL_MAP:
        log_warning_once(
            "tab_mapa",
            "feature_limit_applied",
            "Mapa Principal truncado por limite de feicoes",
            {
                "total_features": int(len(gdf_map)),
                "max_features": int(MAX_FEATURES_FULL_MAP),
            },
            signature={
                "total_features": int(len(gdf_map)),
                "max_features": int(MAX_FEATURES_FULL_MAP),
                "filters_version": int(filters_version or 0),
            },
        )
        st.warning(
            f"⚠️ Muitas feições ({len(gdf_map)}). "
            f"Renderizando apenas {MAX_FEATURES_FULL_MAP}."
        )
        gdf_map = gdf_map.head(MAX_FEATURES_FULL_MAP)

    gdf_map = _preparar_gdf_exibicao(gdf_map)

    selected_satellite_defs = []
    if overlay_truecolor:
        selected_satellite_defs.append(SATELLITE_OVERLAY_OPTIONS[0])
    if overlay_terrafalse:
        selected_satellite_defs.append(SATELLITE_OVERLAY_OPTIONS[1])
    if overlay_worlddream:
        selected_satellite_defs.append(SATELLITE_OVERLAY_OPTIONS[2])

    selected_satellite_layers = [
        {
            **layer_def,
            **_get_satellite_overlay_result(layer_def),
        }
        for layer_def in selected_satellite_defs
    ]
    satellite_status_line = _build_satellite_status_line(selected_satellite_layers)
    imagery_signature = _build_satellite_signature(selected_satellite_layers)

    if selected_satellite_layers:
        log_success_once(
            "tab_mapa",
            "satellite_overlays_resolved",
            "Sobreposicoes de imagem atual avaliadas para o mapa principal",
            {
                "selected_satellite_overlays": ", ".join(layer["label"] for layer in selected_satellite_layers),
                "satellite_status_line": satellite_status_line,
                "manual_zoom_refresh_version": manual_zoom_refresh_version,
                "filters_version": int(filters_version or 0),
            },
            signature={
                "selected_satellite_overlays": [
                    {
                        "slug": layer.get("slug"),
                        "status": layer.get("status"),
                        "data": layer.get("data", ""),
                    }
                    for layer in selected_satellite_layers
                ],
                "manual_zoom_refresh_version": manual_zoom_refresh_version,
                "filters_version": int(filters_version or 0),
            },
        )

    try:
        viewport = shared_viewport or build_map_viewport(gdf_map, tipo_exib)
    except Exception:
        log_error_once(
            "tab_mapa",
            "invalid_bounds",
            "Falha ao calcular limites espaciais do mapa",
            {
                "records": int(len(gdf_map)),
                "filters_version": int(filters_version or 0),
            },
            signature={
                "records": int(len(gdf_map)),
                "status": "bounds_error",
                "filters_version": int(filters_version or 0),
            },
        )
        st.error("Não foi possível calcular os limites espaciais das geometrias.")
        return

    bounds = dict(viewport.get("bounds") or {})
    minx = bounds.get("minx")
    miny = bounds.get("miny")
    maxx = bounds.get("maxx")
    maxy = bounds.get("maxy")

    if any(pd.isna(v) for v in [minx, miny, maxx, maxy]):
        log_error_once(
            "tab_mapa",
            "nan_bounds",
            "Limites espaciais invalidos na aba Mapa Principal",
            {
                "records": int(len(gdf_map)),
                "filters_version": int(filters_version or 0),
            },
            signature={
                "records": int(len(gdf_map)),
                "status": "nan_bounds",
                "filters_version": int(filters_version or 0),
            },
        )
        st.error("Os limites espaciais das geometrias são inválidos.")
        return

    m = folium.Map(
        location=[viewport["center_lat"], viewport["center_lon"]],
        zoom_start=int(viewport["zoom_default"]),
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
        scrollWheelZoom=False,
    )

    try:
        apply_viewport_to_map(m, viewport)
    except Exception:
        pass

    _add_basemaps(m)
    _inject_map_theme(m)
    _add_selected_satellite_layers(m, selected_satellite_layers)

    Fullscreen(
        position="topright",
        title="Tela cheia",
        title_cancel="Sair da tela cheia",
        force_separate_button=True,
    ).add_to(m)

    MiniMap(
        tile_layer=folium.TileLayer(
            tiles=DEFAULT_DARK_TILES,
            attr=DEFAULT_DARK_ATTR,
            name="MiniMap Dark",
        ),
        toggle_display=True,
        position="bottomright",
        width=170,
        height=110,
        collapsed_width=26,
        collapsed_height=26,
        zoom_level_offset=-4,
    ).add_to(m)

    MeasureControl(
        position="topleft",
        primary_length_unit="meters",
        secondary_length_unit="kilometers",
        primary_area_unit="sqmeters",
        secondary_area_unit="hectares",
    ).add_to(m)

    MousePosition(
        position="bottomleft",
        separator=" | ",
        prefix="Coordenadas",
        lat_formatter="function(num) {return L.Util.formatNum(num, 6);}",
        lng_formatter="function(num) {return L.Util.formatNum(num, 6);}",
    ).add_to(m)

    color = _get_cor_exibicao(tipo_exib)
    tooltip_fields, tooltip_aliases = _criar_tooltip(gdf_map)
    gdf_render = gdf_map.drop(columns=["__geometry_original__"], errors="ignore").copy()

    folium.GeoJson(
        data=gdf_render.to_json(),
        name="Fazendas",
        style_function=lambda x: {
            "fillColor": color,
            "color": color,
            "weight": 1.8,
            "opacity": 0.9,
            "fillOpacity": 0.28 if mostrar_preenchimento else 0.00,
        },
        highlight_function=lambda x: {
            "fillColor": palette["map_highlight"],
            "color": palette["map_highlight"],
            "weight": 3.2,
            "opacity": 1,
            "fillOpacity": 0.42 if mostrar_preenchimento else 0.08,
        },
        tooltip=folium.features.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            sticky=True,
            labels=True,
            localize=True,
            style=(
                f"background-color: {palette['map_tooltip']};"
                f"color: {palette['map_text']};"
                f"border: 1px solid {palette['panel_border']};"
                "border-radius: 12px;"
                "padding: 8px 10px;"
                "box-shadow: 0 16px 32px rgba(0,0,0,0.28);"
            ),
        ),
        popup=folium.GeoJsonPopup(
            fields=[field for field in tooltip_fields if field in gdf_render.columns],
            aliases=tooltip_aliases,
            localize=True,
            labels=True,
            style=(
                f"background-color: {palette['map_tooltip']};"
                f"color: {palette['map_text']};"
                f"border: 1px solid {palette['panel_border']};"
                "border-radius: 12px;"
                "padding: 8px 10px;"
            ),
        ),
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    map_key = _build_map_key(
        filtro=filtro,
        gdf_map=gdf_map,
        usar_geometria_original=usar_geometria_original,
        mostrar_preenchimento=mostrar_preenchimento,
        imagery_signature=imagery_signature,
        refresh_token=refresh_token,
    )

    st_folium(
        m,
        use_container_width=True,
        height=620,
        key=map_key,
        returned_objects=[],
    )

    st.caption(satellite_status_line)

    render_compact_summary_cards(
        [
            {"label": "Fazendas", "value": str(n_fazendas)},
            {
                "label": "Área total (ha)",
                "value": f"{area_total_mapa:.1f}" if pd.notna(area_total_mapa) else "N/A",
            },
            {
                "label": "Área produtiva (ha)",
                "value": f"{area_produ_mapa:.1f}" if pd.notna(area_produ_mapa) else "N/A",
            },
            {"label": "Municípios", "value": str(n_municipios)},
            {"label": "Feições", "value": f"{n_feicoes:,}".replace(",", ".")},
        ]
    )

    log_success_once(
        "tab_mapa",
        "map_rendered",
        "Mapa Principal renderizado com sucesso",
        {
            "records": int(len(gdf_render)),
            "tipo_dado": tipo_exib,
            "usar_geometria_original": bool(usar_geometria_original),
            "mostrar_preenchimento": bool(mostrar_preenchimento),
            "selected_satellite_overlays": ", ".join(layer["label"] for layer in selected_satellite_layers),
            "satellite_status_line": satellite_status_line,
            "manual_zoom_refresh_version": manual_zoom_refresh_version,
            **build_viewport_log_details(viewport, filters_version=filters_version),
        },
        signature={
            "records": int(len(gdf_render)),
            "tipo_dado": tipo_exib,
            "usar_geometria_original": bool(usar_geometria_original),
            "mostrar_preenchimento": bool(mostrar_preenchimento),
            "selected_satellite_overlays": [
                {
                    "slug": layer.get("slug"),
                    "status": layer.get("status"),
                    "data": layer.get("data", ""),
                }
                for layer in selected_satellite_layers
            ],
            "manual_zoom_refresh_version": manual_zoom_refresh_version,
            **build_viewport_log_details(viewport, filters_version=filters_version),
            "refresh_token": str(refresh_token or ""),
        },
    )

    st.caption(
        "Bases disponíveis: CartoDB Dark Matter, OpenStreetMap, Esri World Imagery, "
        "Esri World Topo, OpenTopoMap e Stadia Outdoors."
    )


