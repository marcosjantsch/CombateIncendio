# -*- coding: utf-8 -*-

import datetime as dt
from typing import Optional, Dict, List

import geopandas as gpd
import requests
import streamlit as st
import folium

from shapely.geometry import mapping
from streamlit_folium import st_folium
from services.log_service import log_error_once, log_success_once, log_warning_once
from tabs.tab_mapa import (
    _add_basemaps,
    _inject_map_theme,
    apply_viewport_to_map,
    build_map_viewport,
    build_viewport_log_details,
    render_manual_zoom_button,
)


MAP_HEIGHT = 680
FIXED_ZOOM = 9
NASA_LOOKBACK_DAYS = 10
NASA_REQUEST_TIMEOUT = 8

def render_tab_imagens_tempo_real(
    gdf_filtrado,
    selected_empresa=None,
    selected_fazenda=None,
    selected_uf=None,
    selected_municipio=None,
    tipo_dado: str = "Todos os Dados",
    refresh_token: str = "",
    filters_version: int = 0,
    shared_viewport: Optional[Dict[str, object]] = None,
):
    title_col, action_col = st.columns([0.72, 0.28], vertical_alignment="center")
    with title_col:
        st.markdown('<div class="section-title">Imagens em tempo real</div>', unsafe_allow_html=True)
    with action_col:
        render_manual_zoom_button("imagens_atuais", filters_version=filters_version)

    manual_zoom_refresh_version = int(st.session_state.get("manual_zoom_refresh_version", 0))

    if gdf_filtrado is None:
        log_warning_once(
            "tab_imagens",
            "missing_input_gdf",
            "Aba Imagens em tempo real sem dado espacial de entrada",
            {},
            signature={"missing_input": True, "filters_version": int(filters_version or 0)},
        )
        st.warning("⚠️ Nenhum dado espacial foi recebido para a aba.")
        return

    gdf = _prepare_gdf(gdf_filtrado)
    if gdf is None or gdf.empty:
        log_warning_once(
            "tab_imagens",
            "empty_prepared_gdf",
            "Aba Imagens em tempo real sem geometria valida apos preparo",
            {},
            signature={"empty_prepared": True, "filters_version": int(filters_version or 0)},
        )
        st.warning("⚠️ O shapefile filtrado está vazio ou inválido.")
        return

    filtro_desc = _descricao_filtro(
        selected_empresa=selected_empresa,
        selected_fazenda=selected_fazenda,
        selected_uf=selected_uf,
        selected_municipio=selected_municipio,
    )
    st.caption(f"Área selecionada: {filtro_desc}")

    _init_state()

    filtro_key = _build_filter_key(
        gdf=gdf,
        selected_empresa=selected_empresa,
        selected_fazenda=selected_fazenda,
        selected_uf=selected_uf,
        selected_municipio=selected_municipio,
        tipo_dado=tipo_dado,
        refresh_token=refresh_token,
    )

    aplicar_agora = bool(st.session_state.get("aplicar", False))

    if aplicar_agora and st.session_state["imagens_rt_last_filter_key"] != filtro_key:
        st.session_state["imagens_rt_last_filter_key"] = filtro_key
        st.session_state["imagens_rt_resultado_cache"] = {}
        st.session_state["imagens_rt_camada_ativa"] = "NASA Terra TrueColor"

    catalogo = _catalogo_camadas()
    nomes_camadas = [item["nome_base"] for item in catalogo]

    if st.session_state["imagens_rt_camada_ativa"] not in nomes_camadas:
        st.session_state["imagens_rt_camada_ativa"] = nomes_camadas[0]

    camada_escolhida = st.radio(
        "Tipos de imagem disponíveis",
        options=nomes_camadas,
        index=nomes_camadas.index(st.session_state["imagens_rt_camada_ativa"]),
        key="imagens_rt_camada_radio",
    )

    if camada_escolhida != st.session_state["imagens_rt_camada_ativa"]:
        st.session_state["imagens_rt_camada_ativa"] = camada_escolhida
        st.rerun()

    camada_def = _get_catalog_item_by_name(catalogo, camada_escolhida)
    if camada_def is None:
        log_error_once(
            "tab_imagens",
            "missing_layer_definition",
            "Nao foi possivel localizar a definicao da camada selecionada",
            {"camada": camada_escolhida},
            signature={
                "camada": camada_escolhida,
                "missing_definition": True,
                "filters_version": int(filters_version or 0),
            },
        )
        st.warning("⚠️ Não foi possível localizar a definição da camada selecionada.")
        return

    st.caption(
        "A busca é feita somente para a camada selecionada. "
        "Ao trocar a camada ou aplicar novos filtros, o mapa é recriado com o zoom do tipo de dado selecionado."
    )

    resultado = _obter_resultado_camada(camada_def)
    status = resultado["status"]

    if status == "ok":
        log_success_once(
            "tab_imagens",
            "layer_ready",
            "Camada de imagem em tempo real localizada com sucesso",
            {
                "camada": camada_def["nome_base"],
                "data": resultado.get("data", ""),
                "ext": resultado.get("ext", ""),
            },
            signature={
                "camada": camada_def["nome_base"],
                "data": resultado.get("data", ""),
                "ext": resultado.get("ext", ""),
                "status": "ok",
                "filters_version": int(filters_version or 0),
            },
        )
        st.success(
            f'✅ Camada encontrada: {resultado["nome_exibicao"]} | Data: {resultado["data"]} | '
            f'Formato: {resultado["ext"].upper()}'
        )
    elif status == "sem_imagem":
        log_warning_once(
            "tab_imagens",
            "layer_not_found",
            "Nenhuma imagem disponivel encontrada para a camada selecionada",
            {"camada": camada_def["nome_base"]},
            signature={
                "camada": camada_def["nome_base"],
                "status": "sem_imagem",
                "filters_version": int(filters_version or 0),
            },
        )
        st.warning(
            f'⚠️ Não foi encontrada imagem disponível para "{camada_def["nome_base"]}" '
            f'nos últimos {NASA_LOOKBACK_DAYS} dias.'
        )
    else:
        log_error_once(
            "tab_imagens",
            "layer_error",
            "Falha ao consultar camada de imagem em tempo real",
            {"camada": camada_def["nome_base"], "status": status},
            signature={
                "camada": camada_def["nome_base"],
                "status": status,
                "filters_version": int(filters_version or 0),
            },
        )
        st.error(f'❌ Falha ao consultar "{camada_def["nome_base"]}".')

    viewport = shared_viewport
    if viewport is None:
        try:
            viewport = build_map_viewport(gdf, tipo_dado)
        except Exception:
            viewport = None

    if viewport is None:
        log_error_once(
            "tab_imagens",
            "invalid_bounds",
            "Falha ao calcular viewport da aba Imagens em tempo real",
            {
                "records": int(len(gdf)),
                "tipo_dado": tipo_dado,
                "filters_version": int(filters_version or 0),
            },
            signature={
                "records": int(len(gdf)),
                "tipo_dado": tipo_dado,
                "status": "invalid_bounds",
                "filters_version": int(filters_version or 0),
            },
        )
        st.error("Não foi possível calcular os limites espaciais para o mapa de imagens.")
        return

    m = _criar_mapa_base(gdf, tipo_dado=tipo_dado, viewport=viewport)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satélite Base",
        overlay=False,
        control=True,
        show=True,
        max_zoom=22,
    ).add_to(m)

    if status == "ok":
        folium.TileLayer(
            tiles=resultado["url_template"],
            attr="NASA GIBS",
            name=resultado["nome_exibicao"],
            overlay=True,
            control=False,
            show=True,
            opacity=0.72,
            max_zoom=22,
            max_native_zoom=FIXED_ZOOM,
        ).add_to(m)

    _add_shape_layer(m, gdf, nome_camada="Perímetro da Fazenda")

    st_folium(
        m,
        use_container_width=True,
        height=MAP_HEIGHT,
        key=(
            f'mapa_imagens_tempo_real_'
            f'{camada_def["slug"]}_{status}_{resultado.get("data", "na")}_{FIXED_ZOOM}_{filtro_key}'
        ),
        returned_objects=[],
    )

    log_success_once(
        "tab_imagens",
        "map_rendered",
        "Mapa de imagens em tempo real renderizado",
        {
            "camada": camada_def["nome_base"],
            "status": status,
            "records": int(len(gdf)),
            "tipo_dado": tipo_dado,
            "manual_zoom_refresh_version": manual_zoom_refresh_version,
            **build_viewport_log_details(viewport, filters_version=filters_version),
        },
        signature={
            "camada": camada_def["nome_base"],
            "status": status,
            "records": int(len(gdf)),
            "data": resultado.get("data", ""),
            "tipo_dado": tipo_dado,
            "manual_zoom_refresh_version": manual_zoom_refresh_version,
            **build_viewport_log_details(viewport, filters_version=filters_version),
            "refresh_token": str(refresh_token or ""),
        },
    )
def _init_state():
    if "imagens_rt_last_filter_key" not in st.session_state:
        st.session_state["imagens_rt_last_filter_key"] = None

    if "imagens_rt_resultado_cache" not in st.session_state:
        st.session_state["imagens_rt_resultado_cache"] = {}

    if "imagens_rt_camada_ativa" not in st.session_state:
        st.session_state["imagens_rt_camada_ativa"] = "NASA Terra TrueColor"


def _catalogo_camadas() -> List[Dict[str, str]]:
    return [
        {
            "slug": "terra_truecolor",
            "nome_base": "NASA Terra TrueColor",
            "layer_name": "MODIS_Terra_CorrectedReflectance_TrueColor",
            "tile_matrix_set": "GoogleMapsCompatible_Level9",
            "ext_preferida": "jpg",
        },
        {
            "slug": "terra_false_721",
            "nome_base": "NASA Terra False 7-2-1",
            "layer_name": "MODIS_Terra_CorrectedReflectance_Bands721",
            "tile_matrix_set": "GoogleMapsCompatible_Level9",
            "ext_preferida": "jpg",
        },
        {
            "slug": "worldview_gibs",
            "nome_base": "Satélite Worldview/GIBS",
            "layer_name": "MODIS_Terra_CorrectedReflectance_TrueColor",
            "tile_matrix_set": "GoogleMapsCompatible_Level9",
            "ext_preferida": "jpg",
        },
    ]


def _get_catalog_item_by_name(catalogo: List[Dict[str, str]], nome_base: Optional[str]) -> Optional[Dict[str, str]]:
    if not nome_base:
        return None
    for item in catalogo:
        if item["nome_base"] == nome_base:
            return item
    return None


def _obter_resultado_camada(camada_def: Dict[str, str]) -> Dict[str, str]:
    cache_key = camada_def["slug"]
    cache = st.session_state["imagens_rt_resultado_cache"]

    if cache_key in cache:
        return cache[cache_key]

    resultado = _buscar_camada_disponivel(camada_def)
    cache[cache_key] = resultado
    return resultado


def _buscar_camada_disponivel(camada_def: Dict[str, str]) -> Dict[str, str]:
    layer_name = camada_def["layer_name"]
    nome_base = camada_def["nome_base"]
    tile_matrix_set = camada_def["tile_matrix_set"]
    ext_preferida = camada_def["ext_preferida"]

    extensoes = [ext_preferida]
    if ext_preferida == "jpg":
        extensoes.append("png")
    else:
        extensoes.append("jpg")

    for data_ref in _datas_candidatas_nasa():
        for ext in extensoes:
            url_template = _url_gibs(layer_name, data_ref, tile_matrix_set, ext)
            if _tile_existe(url_template):
                return {
                    "status": "ok",
                    "slug": camada_def["slug"],
                    "layer_name": layer_name,
                    "nome_exibicao": f"{nome_base} {data_ref}",
                    "data": data_ref,
                    "ext": ext,
                    "url_template": url_template,
                }

    return {
        "status": "sem_imagem",
        "slug": camada_def["slug"],
        "layer_name": layer_name,
        "nome_exibicao": nome_base,
    }


def _prepare_gdf(gdf_input) -> Optional[gpd.GeoDataFrame]:
    try:
        if isinstance(gdf_input, gpd.GeoDataFrame):
            gdf = gdf_input.copy()
        else:
            gdf = gpd.GeoDataFrame(gdf_input, geometry="geometry")

        if gdf.empty:
            return gdf

        gdf = gdf[gdf.geometry.notnull()].copy()
        gdf = gdf[~gdf.geometry.is_empty].copy()

        if gdf.empty:
            return gdf

        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326, allow_override=True)
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)

        try:
            gdf["geometry"] = gdf["geometry"].buffer(0)
        except Exception:
            pass

        gdf = gdf[gdf.geometry.notnull()].copy()
        gdf = gdf[~gdf.geometry.is_empty].copy()

        return gdf

    except Exception as e:
        st.warning(f"⚠️ Falha ao preparar o shapefile: {e}")
        return None


def _descricao_filtro(
    selected_empresa=None,
    selected_fazenda=None,
    selected_uf=None,
    selected_municipio=None,
) -> str:
    partes = []

    if selected_uf:
        partes.append(f"UF: {selected_uf}")
    if selected_municipio:
        partes.append(f"Município: {selected_municipio}")
    if selected_empresa:
        partes.append(f"Empresa: {selected_empresa}")
    if selected_fazenda:
        partes.append(f"Fazenda: {selected_fazenda}")

    return " | ".join(partes) if partes else "Filtro atual"


def _build_filter_key(
    gdf: gpd.GeoDataFrame,
    selected_empresa=None,
    selected_fazenda=None,
    selected_uf=None,
    selected_municipio=None,
    tipo_dado: str = "",
    refresh_token: str = "",
) -> str:
    try:
        bounds = tuple(round(v, 6) for v in gdf.total_bounds.tolist())
    except Exception:
        bounds = ("sem_bounds",)

    partes = [
        str(selected_empresa or ""),
        str(selected_fazenda or ""),
        str(selected_uf or ""),
        str(selected_municipio or ""),
        str(tipo_dado or ""),
        str(len(gdf)),
        str(bounds),
        str(refresh_token or ""),
    ]
    return "|".join(partes)


def _criar_mapa_base(
    gdf: gpd.GeoDataFrame,
    tipo_dado: str = "Todos os Dados",
    viewport: Optional[Dict[str, object]] = None,
) -> folium.Map:
    map_viewport = viewport or build_map_viewport(gdf, tipo_dado)

    m = folium.Map(
        location=[map_viewport["center_lat"], map_viewport["center_lon"]],
        zoom_start=int(map_viewport["zoom_default"]),
        control_scale=True,
        tiles=None,
        prefer_canvas=True,
        scrollWheelZoom=False,
    )

    try:
        apply_viewport_to_map(m, map_viewport)
    except Exception:
        pass

    _add_basemaps(m)
    _inject_map_theme(m)

    return m


def _datas_candidatas_nasa(max_dias: int = NASA_LOOKBACK_DAYS) -> List[str]:
    hoje = dt.datetime.utcnow().date()
    return [
        (hoje - dt.timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(max_dias + 1)
    ]


def _url_gibs(layer_name: str, data_ref: str, tile_matrix_set: str, ext: str) -> str:
    return (
        "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
        f"{layer_name}/default/{data_ref}/"
        f"{tile_matrix_set}/{{z}}/{{y}}/{{x}}.{ext}"
    )


def _tile_existe(url_template: str, timeout: int = NASA_REQUEST_TIMEOUT) -> bool:
    try:
        test_url = url_template.format(z=1, x=0, y=0)

        r = requests.head(test_url, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            content_type = r.headers.get("Content-Type", "").lower()
            return ("image" in content_type) or (content_type == "")

        if r.status_code in (403, 405):
            r = requests.get(test_url, timeout=timeout, stream=True, allow_redirects=True)
            content_type = r.headers.get("Content-Type", "").lower()
            return r.status_code == 200 and (("image" in content_type) or (content_type == ""))

        return False

    except Exception:
        return False


def _add_shape_layer(
    m: folium.Map,
    gdf: gpd.GeoDataFrame,
    nome_camada: str = "Perímetro",
):
    try:
        geojson_data = {
            "type": "FeatureCollection",
            "features": [],
        }

        campos_popup = []
        for campo in ["EMPRESA", "FAZENDA", "UF", "MUNICIPIO", "AREA_T", "AREA_PRODU"]:
            if campo in gdf.columns:
                campos_popup.append(campo)

        for _, row in gdf.iterrows():
            props = {}
            for campo in campos_popup:
                val = row.get(campo, "")
                props[campo] = "" if val is None else str(val)

            geojson_data["features"].append(
                {
                    "type": "Feature",
                    "geometry": mapping(row.geometry),
                    "properties": props,
                }
            )

        popup_obj = None
        if campos_popup:
            popup_obj = folium.GeoJsonPopup(
                fields=campos_popup,
                aliases=[f"{c}: " for c in campos_popup],
                localize=True,
                labels=True,
                sticky=False,
            )

        tooltip_fields = [c for c in ["EMPRESA", "FAZENDA"] if c in gdf.columns]
        tooltip_obj = None
        if tooltip_fields:
            tooltip_obj = folium.GeoJsonTooltip(
                fields=tooltip_fields,
                aliases=[f"{c}: " for c in tooltip_fields],
                sticky=True,
            )

        folium.GeoJson(
            geojson_data,
            name=nome_camada,
            style_function=lambda _x: {
                "color": "#ffff00",
                "weight": 3,
                "fillColor": "#ffff00",
                "fillOpacity": 0.02,
            },
            highlight_function=lambda _x: {
                "color": "#ff0000",
                "weight": 4,
                "fillOpacity": 0.08,
            },
            popup=popup_obj,
            tooltip=tooltip_obj,
        ).add_to(m)

    except Exception as e:
        st.warning(f"⚠️ Não foi possível desenhar o perímetro da fazenda: {e}")

